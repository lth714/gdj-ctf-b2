<?php
namespace App\Controllers;

use App\Core\Logger;
use App\Core\Config;
use App\Models\ErrorLog;
use App\Core\Database;
use App\Core\Redis;

class ProxyController
{
    private $logger;
    private $config;
    private $pidFile;
    private $errorLog;
    private $db;
    private $redis;
    
    public function __construct()
    {
        $this->logger = new Logger();
        $this->config = Config::getInstance();
        $this->pidFile = dirname(dirname(__DIR__)) . '/storage/proxy.pid';
        $this->errorLog = new ErrorLog();
        $this->db = Database::getInstance()->getConnection();
        $this->redis = new Redis();
    }
    
    private function isRunning($pid = null)
    {
        if ($pid === null) {
            $pid = @file_get_contents($this->pidFile);
        }
        if (!$pid) {
            return false;
        }
        
        // Windows系统下的进程检查
        if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
            // 使用tasklist命令检查进程
            $cmd = "tasklist /FI \"PID eq $pid\" /NH";
            exec($cmd, $output);
            
            // 检查输出中是否包含PID
            foreach ($output as $line) {
                if (strpos($line, (string)$pid) !== false) {
                    // 检查端口占用
                    $port = $this->config->get('proxy_port', '9260');
                    $cmd = "netstat -ano | findstr :$port";
                    exec($cmd, $netstatOutput);
                    
                    // 如果端口未被占用，进程可能正在停止中
                    if (empty($netstatOutput)) {
                        return false;
                    }
                    return true;
                }
            }
            return false;
        } else {
            // Linux系统的原有检查逻辑
            exec("ps -p $pid", $psOutput, $psReturnVar);
            if ($psReturnVar !== 0) {
                return false;
            }
            
            $port = $this->config->get('proxy_port', '9260');
            exec("netstat -tnlp 2>/dev/null | grep :$port", $netstatOutput);
            
            if (empty($netstatOutput)) {
                return false;
            }
            
            return true;
        }
    }
    
    private function sendJsonResponse($data)
    {
        // 清除之前的所有输出
        while (ob_get_level()) {
            ob_end_clean();
        }
        
        // 设置响应头
        header('Content-Type: application/json');
        header('Cache-Control: no-cache, must-revalidate');
        header('Expires: Thu, 01 Jan 1970 00:00:00 GMT');
        
        // 输出 JSON 数据
        echo json_encode($data);
        exit;
    }
    
    public function start()
    {
        $pid = @file_get_contents($this->pidFile);
        
        // 如果进程已经在运行，返回错误
        if ($pid && $this->isRunning($pid)) {
            $this->sendJsonResponse([
                'success' => false,
                'message' => '代理服务器已经在运行中'
            ]);
        }
        
        // 构建完整的命令路径
        $scriptPath = realpath(__DIR__ . '/../Commands/proxy.php');
        if (!$scriptPath) {
            $this->logError('找不到代理服务器脚本文件', 'error', __FILE__, __LINE__);
            $this->sendJsonResponse([
                'success' => false,
                'message' => '找不到代理服务器脚本文件'
            ]);
        }
        
        // 检查文件权限
        if (!is_readable($scriptPath)) {
            $this->logError('代理服务器脚本文件无法读取', 'error', __FILE__, __LINE__);
            $this->sendJsonResponse([
                'success' => false,
                'message' => '代理服务器脚本文件无法读取'
            ]);
        }
        
        // 确保日志目录存在且可写
        $logDir = __DIR__ . '/../../storage/logs';
        if (!is_dir($logDir)) {
            mkdir($logDir, 0755, true);
        }
        
        // 确保 PID 文件目录存在且可写
        $pidDir = dirname($this->pidFile);
        if (!is_dir($pidDir)) {
            mkdir($pidDir, 0755, true);
        }
        
        // 查找可用的PHP CLI可执行文件
        $phpBinary = $this->findPhpBinary();
        if (!$phpBinary) {
            $this->logError('找不到可用的PHP CLI可执行文件', 'error', __FILE__, __LINE__);
            $this->sendJsonResponse([
                'success' => false,
                'message' => '找不到可用的PHP CLI可执行文件'
            ]);
        }
        
        // 执行启动命令
        $command = sprintf('%s %s start 2>&1', $phpBinary, escapeshellarg($scriptPath));
        exec($command, $output, $returnVar);
        
        // 如果命令执行失败，直接返回错误
        if ($returnVar !== 0) {
            $this->logError('代理服务器启动失败', 'error', __FILE__, __LINE__);
            $this->sendJsonResponse([
                'success' => false,
                'message' => '代理服务器启动失败: ' . implode("\n", $output)
            ]);
        }
        
        // 等待进程启动（最多等待5秒）
        $timeout = 5;
        $started = false;
        while ($timeout > 0) {
            clearstatcache(true, $this->pidFile);
            $pid = @file_get_contents($this->pidFile);
            
            if ($pid && $this->isRunning($pid)) {
                $started = true;
                break;
            }
            
            sleep(1);
            $timeout--;
        }
        
        if ($started) {
            $this->logError('代理服务器已启动', 'info', __FILE__, __LINE__);
            $this->sendJsonResponse([
                'success' => true,
                'message' => '代理服务器已启动'
            ]);
        } else {
            $this->logError('代理服务器启动失败', 'error', __FILE__, __LINE__);
            if (file_exists($this->pidFile)) {
                @unlink($this->pidFile);
            }
            $this->sendJsonResponse([
                'success' => false,
                'message' => '代理服务器启动失败，请查看日志获取详细信息'
            ]);
        }
    }
    
    private function findPhpBinary()
    {
        // 检查是否是宝塔环境
        $btPanelPath = '/www/server/panel/class/panelSite.py';
        
        if (file_exists($btPanelPath)) {
            // 从当前 PHP 进程路径中提取版本号
            if (preg_match('/\/www\/server\/php\/(\d+)\//', PHP_BINARY, $matches)) {
                $version = $matches[1];
                
                // 构建宝塔 PHP CLI 路径
                $btPath = "/www/server/php/{$version}/bin/php";
                
                if (file_exists($btPath) && is_executable($btPath)) {
                    // 验证是否是 CLI 版本
                    $command = sprintf('"%s" -v 2>&1', $btPath);
                    exec($command, $output, $returnVar);
                    
                    if ($returnVar === 0) {
                        return $btPath;
                    }
                }
            } else {
                // 尝试直接使用当前PHP版本
                $version = PHP_MAJOR_VERSION . PHP_MINOR_VERSION;
                $btPath = "/www/server/php/{$version}/bin/php";
                
                if (file_exists($btPath) && is_executable($btPath)) {
                    return $btPath;
                }
            }
        }
        
        // 如果宝塔环境检测失败，尝试直接使用 php 命令
        exec('command -v php 2>/dev/null', $output, $returnVar);
        
        if ($returnVar === 0 && !empty($output)) {
            $phpPath = trim($output[0]);
            
            // 验证是否可用
            $command = sprintf('"%s" -v 2>&1', $phpPath);
            exec($command, $output, $returnVar);
            
            if ($returnVar === 0) {
                return $phpPath;
            }
        }
        
        // 如果是 Windows 系统
        if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
            $possiblePaths = [
                'C:\\php\\php.exe',
                'C:\\xampp\\php\\php.exe',
                'C:\\wamp64\\bin\\php\\php8.2.0\\php.exe',
                'C:\\wamp64\\bin\\php\\php8.1.0\\php.exe',
                'C:\\wamp64\\bin\\php\\php8.0.0\\php.exe',
                'C:\\wamp64\\bin\\php\\php7.4.0\\php.exe',
                'php.exe'
            ];
            
            foreach ($possiblePaths as $path) {
                if ($path === 'php.exe') {
                    $command = 'where php.exe';
                    exec($command, $output, $returnVar);
                    
                    if ($returnVar === 0 && !empty($output)) {
                        $path = trim($output[0]);
                    }
                }
                
                if (file_exists($path) && is_executable($path)) {
                    return $path;
                }
            }
        } else {
            $possiblePaths = [
                '/usr/bin/php',
                '/usr/local/bin/php',
                '/usr/local/php/bin/php',
                'php'
            ];
            
            foreach ($possiblePaths as $path) {
                if ($path === 'php') {
                    $command = 'which php 2>/dev/null';
                    exec($command, $output, $returnVar);
                    
                    if ($returnVar === 0 && !empty($output)) {
                        $path = trim($output[0]);
                    }
                }
                
                if (file_exists($path) && is_executable($path)) {
                    $command = sprintf('"%s" -v 2>&1', $path);
                    exec($command, $output, $returnVar);
                    
                    if ($returnVar === 0) {
                        return $path;
                    }
                }
            }
        }
        
        $this->logError('找不到可用的 PHP CLI', 'error', __FILE__, __LINE__);
        return null;
    }
    
    public function stop()
    {
        $pid = @file_get_contents($this->pidFile);
        
        // 如果进程不在运行，返回成功
        if (!$pid || !$this->isRunning($pid)) {
            @unlink($this->pidFile);
            $this->sendJsonResponse([
                'success' => true,
                'message' => '代理服务器已停止'
            ]);
        }
        
        // 获取PHP可执行文件路径
        $phpBinary = $this->findPhpBinary();
        if (!$phpBinary) {
            $this->logError('找不到可用的PHP CLI可执行文件', 'error', __FILE__, __LINE__);
            $this->sendJsonResponse([
                'success' => false,
                'message' => '找不到可用的PHP CLI可执行文件'
            ]);
        }
        
        // 构建完整的命令路径
        $scriptPath = realpath(__DIR__ . '/../Commands/proxy.php');
        if (!$scriptPath) {
            $this->logError('找不到代理服务器脚本文件', 'error', __FILE__, __LINE__);
            $this->sendJsonResponse([
                'success' => false,
                'message' => '找不到代理服务器脚本文件'
            ]);
        }
        
        // 执行停止命令
        $command = sprintf('%s %s stop 2>&1', $phpBinary, escapeshellarg($scriptPath));
        exec($command, $output, $returnVar);
        
        // 发送SIGTERM信号
        if ($pid) {
            posix_kill((int)$pid, SIGTERM);
        }
        
        // 等待进程停止（最多等待10秒）
        $timeout = 10;
        $stopped = false;
        while ($timeout > 0) {
            if (!$this->isRunning($pid)) {
                $stopped = true;
                break;
            }
            
            sleep(1);
            $timeout--;
        }
        
        // 如果进程仍在运行，尝试强制终止
        if (!$stopped && $pid) {
            posix_kill((int)$pid, SIGKILL);
            sleep(1);
        }
        
        // 清理PID文件
        @unlink($this->pidFile);
        // 检查是否需要清空日志
        if ($this->config->get('clear_logs_on_stop', '0') == '1'){
            // 清空错误日志表
            $this->db->query("TRUNCATE TABLE error_logs");
            // 清空应用日志文件
            $logFile = dirname(dirname(__DIR__)) . '/storage/logs/app.log';
            if (file_exists($logFile)) {
                file_put_contents($logFile, '');
            }
        }

        // 检查是否需要清空连接记录
        if ($this->config->get('clear_connections', '0') == '1') {
            // 清空连接日志表
            $this->db->query("TRUNCATE TABLE channel_connections");
        }
        
        // 获取缓存统计数据的 Redis key
        $monitorCacheKey = $this->config->get('monitor_cache_stats', 'monitor:cache_stats');
        
        // 删除缓存统计数据
        try {
            $redis = new Redis();
            if ($redis->exists($monitorCacheKey)) {
                $redis->del($monitorCacheKey);
                $this->logger->info("已清除缓存统计数据: {$monitorCacheKey}");
            }
        } catch (\Exception $e) {
            $this->logger->error("清除缓存统计数据失败: " . $e->getMessage());
        }

        if ($stopped || !$this->isRunning($pid)) {
            $this->logError('代理服务器已停止', 'info', __FILE__, __LINE__);
            $this->sendJsonResponse([
                'success' => true,
                'message' => '代理服务器已停止'
            ]);
            
        } else {
            $this->logError('代理服务器停止失败', 'error', __FILE__, __LINE__);
            $this->sendJsonResponse([
                'success' => false,
                'message' => '代理服务器停止失败'
            ]);
        }
    }

    public function status()
    {
        $pid = @file_get_contents($this->pidFile);
        $running = $pid && $this->isRunning($pid);
        
        // 如果进程不存在但PID文件存在，清理PID文件
        if (!$running && $pid) {
            @unlink($this->pidFile);
            $pid = null;
        }
        
        // 获取进程运行时间
        $uptime = null;
        if ($running && $pid) {
            $stat = @file_get_contents("/proc/$pid/stat");
            if ($stat) {
                $stats = explode(' ', $stat);
                if (isset($stats[21])) {  // starttime
                    $btime = file_get_contents('/proc/stat');
                    if (preg_match('/btime\s+(\d+)/', $btime, $matches)) {
                        $bootTime = (int)$matches[1];
                        $startTime = $bootTime + ((int)$stats[21] / 100);
                        $uptime = time() - $startTime;
                    }
                }
            }
        }
        
        // 获取端口和连接信息
        $port = $this->config->get('proxy_port', '9260');
        $connections = 0;
        if ($running) {
            $netstat = [];
            exec("netstat -ant | grep :$port | grep ESTABLISHED", $netstat);
            $connections = count($netstat);
        }
        
        // 获取内存使用情况
        $memory = null;
        if ($running && $pid) {
            $status = @file_get_contents("/proc/$pid/status");
            if ($status && preg_match('/VmRSS:\s+(\d+)\s+kB/', $status, $matches)) {
                $memory = (int)$matches[1] * 1024;  // 转换为字节
            }
        }
        
        $this->sendJsonResponse([
            'success' => true,
            'data' => [
                'running' => $running,
                'pid' => $running ? $pid : null,
                'uptime' => $uptime,
                'memory' => $memory,
                'connections' => $connections,
                'port' => $port,
                'settings' => [
                    'host' => $this->config->get('proxy_host', '0.0.0.0'),
                    'port' => $port,
                    'timeout' => $this->config->get('proxy_timeout', '10'),
                    'buffer_size' => $this->config->get('proxy_buffer_size', '8192')
                ]
            ]
        ]);
    }
    
    public function getStatus()
    {
        $pid = @file_get_contents($this->pidFile);
        $isRunning = $this->isRunning($pid);
        
        // 获取配置
        $port = $this->config->get('proxy_port', '9260');
        $host = $this->config->get('proxy_host', '0.0.0.0');
        $timeout = $this->config->get('proxy_timeout', '10');
        $bufferSize = $this->config->get('proxy_buffer_size', '8192');
        
        // 获取进程信息
        $uptime = null;
        $memory = null;
        $connections = 0;
        
        if ($isRunning && $pid) {
            // 获取进程启动时间
            $stat = @file_get_contents("/proc/$pid/stat");
            if ($stat) {
                $stats = explode(' ', $stat);
                if (isset($stats[21])) {
                    $startTime = (int)$stats[21];
                    $uptime = time() - $startTime;
                }
            }
            
            // 获取内存使用
            $status = @file_get_contents("/proc/$pid/status");
            if ($status) {
                if (preg_match('/VmRSS:\s+(\d+)\s+kB/', $status, $matches)) {
                    $memory = (int)$matches[1] * 1024; // 转换为字节
                }
            }
            
            // 获取连接数
            exec("netstat -tnp 2>/dev/null | grep :$port | grep $pid | wc -l", $output);
            if (isset($output[0])) {
                $connections = (int)$output[0];
            }
        }
        
        $this->sendJsonResponse([
            'success' => true,
            'data' => [
                'running' => $isRunning,
                'pid' => $isRunning ? $pid : null,
                'uptime' => $uptime,
                'memory' => $memory,
                'connections' => $connections,
                'port' => $port,
                'settings' => [
                    'host' => $host,
                    'port' => $port,
                    'timeout' => $timeout,
                    'buffer_size' => $bufferSize
                ]
            ]
        ]);
    }
    
    public function getConnectionStats()
    {
        try {
            $db = \App\Core\Database::getInstance()->getConnection();
            
            // 清理不活跃连接（超过1分钟未活动）
            $stmt = $db->prepare("UPDATE channel_connections 
                SET status = 'disconnected' 
                WHERE status = 'active' 
                AND last_active_time < DATE_SUB(NOW(), INTERVAL 1 MINUTE)");
            $stmt->execute();
            
            // 获取总连接数
            $totalQuery = "SELECT COUNT(*) as count FROM channel_connections WHERE status = 'active'";
            $stmt = $db->query($totalQuery);
            $totalConnections = $stmt->fetch(\PDO::FETCH_ASSOC)['count'];
            
            // 获取每个频道的连接数
            $channelQuery = "SELECT c.id, c.name, COUNT(cc.id) as connections 
                           FROM channels c 
                           LEFT JOIN channel_connections cc ON c.id = cc.channel_id 
                           AND cc.status = 'active' 
                           GROUP BY c.id, c.name 
                           HAVING connections > 0 
                           ORDER BY connections DESC";
            $stmt = $db->query($channelQuery);
            $channelConnections = $stmt->fetchAll(\PDO::FETCH_ASSOC);
            
            // 记录日志
            //$this->logError("当前活跃连接数: $totalConnections", 'info', __FILE__, __LINE__);
            if ($totalConnections > 0) {
                //$this->logError("频道连接详情: " . json_encode($channelConnections), 'info', __FILE__, __LINE__);
            }
        
            $this->sendJsonResponse([
                'success' => true,
                'data' => [
                    'running' => true,
                    'connections' => (int)$totalConnections,
                    'channel_connections' => $channelConnections
                ]
            ]);
        } catch (\Exception $e) {
            $this->logError("获取连接统计信息时发生错误: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            $this->logError("错误堆栈: " . $e->getTraceAsString(), 'error', __FILE__, __LINE__);
            $this->sendJsonResponse([
                'success' => false,
                'message' => '获取连接统计信息失败'
            ]);
        }
    }
    
    
    private function formatBandwidthStats($stats, $channel)
    {
        $bytesReceived = intval($stats['bytes_received'] ?? 0);
        $bytesSent = intval($stats['bytes_sent'] ?? 0);
        $timestamp = time();
        
        // 计算带宽速率（基于最近两次更新的差值）
        $key = "proxy:stats:prev:{$channel['id']}";
        $prevStats = $this->redis->hGetAll($key);
        
        // 初始化速率为0
        $downloadSpeed = 0;
        $uploadSpeed = 0;
        
        if (!empty($prevStats)) {
            $prevBytesReceived = intval($prevStats['bytes_received'] ?? 0);
            $prevBytesSent = intval($prevStats['bytes_sent'] ?? 0);
            $prevTimestamp = intval($prevStats['timestamp'] ?? 0);
            
            // 确保时间戳是正确的
            if ($prevTimestamp < $timestamp) {
                $timeDiff = $timestamp - $prevTimestamp;
                $bytesDiffReceived = $bytesReceived - $prevBytesReceived;
                $bytesDiffSent = $bytesSent - $prevBytesSent;
                
                // 只要有数据变化就计算速率，但限制时间窗口
                if ($timeDiff > 0 && $bytesDiffReceived > 0) {
                    // 如果时间差太大，使用一个合理的时间窗口
                    if ($timeDiff > 30) {
                        $timeDiff = 30;  // 使用30秒作为最大时间窗口
                    }
                    
                    $downloadSpeed = $bytesDiffReceived / $timeDiff;
                    $uploadSpeed = $bytesDiffSent / $timeDiff;
                }
            }
        }
        
        // 保存当前数据作为下次计算的基础
        $this->redis->hMSet($key, [
            'bytes_received' => $bytesReceived,
            'bytes_sent' => $bytesSent,
            'timestamp' => $timestamp
        ]);
        
        return [
            'channel' => $channel,
            'stats' => [
                'traffic' => [
                    'received' => $this->formatBytes($bytesReceived),
                    'sent' => $this->formatBytes($bytesSent)
                ],
                'bandwidth' => [
                    'download' => $this->formatBytes(max(0, $downloadSpeed)) . '/s',
                    'upload' => $this->formatBytes(max(0, $uploadSpeed)) . '/s'
                ],
                'last_update' => date('Y-m-d H:i:s', $timestamp),
                'debug' => [
                    'time_diff' => $timeDiff ?? 0,
                    'bytes_diff' => [
                        'received' => $bytesDiffReceived ?? 0,
                        'sent' => $bytesDiffSent ?? 0
                    ],
                    'timestamps' => [
                        'current' => $timestamp,
                        'prev' => $prevTimestamp ?? 0
                    ],
                    'adjusted_time' => ($timeDiff ?? 0) > 30  // 标记是否进行了时间调整
                ]
            ]
        ];
    }
    
    private function getTotalBandwidthStats()
    {
        $timestamp = time();
        $totalDownloadSpeed = 0;
        $totalUploadSpeed = 0;
        $activeChannelsWithTraffic = 0;
        $totalReceived = 0;
        $totalSent = 0;
        
        // 获取所有活跃频道
        $stmt = $this->db->query("SELECT id, name FROM channels WHERE status = 1");
        $channels = $stmt->fetchAll(\PDO::FETCH_ASSOC);
        
        $channelStats = [];
        
        foreach ($channels as $channel) {
            $currentKey = "proxy:stats:{$channel['id']}";
            $prevKey = "proxy:stats:prev:{$channel['id']}";
            
            $stats = $this->redis->hGetAll($currentKey);
            $prevStats = $this->redis->hGetAll($prevKey);
            
            if (!empty($stats)) {
                $bytesReceived = intval($stats['bytes_received'] ?? 0);
                $bytesSent = intval($stats['bytes_sent'] ?? 0);
                
                // 累加总流量
                $totalReceived += $bytesReceived;
                $totalSent += $bytesSent;
                
                if (!empty($prevStats)) {
                    $prevBytesReceived = intval($prevStats['bytes_received'] ?? 0);
                    $prevBytesSent = intval($prevStats['bytes_sent'] ?? 0);
                    $prevTimestamp = intval($prevStats['timestamp'] ?? 0);
                    
                    // 计算单个频道的带宽
                    $timeDiff = $timestamp - $prevTimestamp;
                    $bytesDiffReceived = $bytesReceived - $prevBytesReceived;
                    $bytesDiffSent = $bytesSent - $prevBytesSent;
                    
                    // 修改这里：调整时间差和数据变化的判断逻辑
                    if ($timeDiff > 0 && $bytesDiffReceived > 0) {
                        // 如果时间差太大，使用一个合理的时间窗口
                        if ($timeDiff > 30) {
                            $timeDiff = 30;  // 使用30秒作为最大时间窗口
                        }
                        
                        $downloadSpeed = $bytesDiffReceived / $timeDiff;
                        $uploadSpeed = $bytesDiffSent / $timeDiff;
                        
                        $channelStats[$channel['id']] = [
                            'name' => $channel['name'],
                            'download_speed' => $downloadSpeed,
                            'upload_speed' => $uploadSpeed,
                            'time_diff' => $timeDiff,
                            'bytes_diff' => [
                                'received' => $bytesDiffReceived,
                                'sent' => $bytesDiffSent
                            ],
                            'adjusted_time' => ($timeDiff > 30)  // 标记是否进行了时间调整
                        ];
                        
                        $totalDownloadSpeed += $downloadSpeed;
                        $totalUploadSpeed += $uploadSpeed;
                        $activeChannelsWithTraffic++;
                    }
                }
                
                // 更新前一次统计数据
                $this->redis->hMSet($prevKey, [
                    'bytes_received' => $bytesReceived,
                    'bytes_sent' => $bytesSent,
                    'timestamp' => $timestamp
                ]);
            }
        }
        
        return [
            'traffic' => [
                'received' => $this->formatBytes($totalReceived),
                'sent' => $this->formatBytes($totalSent)
            ],
            'bandwidth' => [
                'download' => $this->formatBytes($totalDownloadSpeed) . '/s',
                'upload' => $this->formatBytes($totalUploadSpeed) . '/s'
            ],
            'last_update' => date('Y-m-d H:i:s', $timestamp),
            'active_channels' => count($channels),
            'channels_with_traffic' => $activeChannelsWithTraffic,
            'debug' => [
                'download_speed_raw' => $totalDownloadSpeed,
                'upload_speed_raw' => $totalUploadSpeed,
                'channels_checked' => count($channels),
                'active_channels_with_traffic' => $activeChannelsWithTraffic,
                'channel_stats' => $channelStats,
                'timestamp' => [
                    'current' => $timestamp,
                    'formatted' => date('Y-m-d H:i:s', $timestamp)
                ]
            ]
        ];
    }
    
    /**
     * 获取带宽统计数据
     * 
     * @return void 直接输出JSON格式的带宽统计信息
     */
    public function getBandwidthStats()
    {
        try {
            $channelId = $_GET['channel_id'] ?? null;
            $timestamp = time();
            
            if ($channelId) {
                // 获取单个频道的统计数据
                $stmt = $this->db->prepare("SELECT id, name FROM channels WHERE id = ?");
                $stmt->execute([$channelId]);
                $channel = $stmt->fetch(\PDO::FETCH_ASSOC);
                
                if (!$channel) {
                    $this->sendJsonResponse([
                        'success' => false,
                        'message' => '频道不存在'
                    ]);
                    return;
                }
                
                $key = "proxy:stats:{$channel['id']}";
                $currentStats = $this->redis->get($key);
                $stats = $currentStats ? json_decode($currentStats, true) : null;
                
                if ($stats) {
                    $formattedStats = [
                        'channel_id' => $channel['id'],
                        'name' => $channel['name'],
                        'stats' => [
                            'traffic' => [
                                'received' => $this->formatBytes($stats['bytes_received']),
                                'sent' => $this->formatBytes($stats['bytes_sent'])
                            ],
                            'bandwidth' => [
                                'download' => $this->formatBytes($stats['bandwidth_received']) . '/s',
                                'upload' => $this->formatBytes($stats['bandwidth_sent']) . '/s'
                            ],
                            'last_update' => date('Y-m-d H:i:s', $stats['last_update']),
                            'debug' => [
                                'bytes_received' => $stats['bytes_received'],
                                'bytes_sent' => $stats['bytes_sent'],
                                'bandwidth_received' => $stats['bandwidth_received'],
                                'bandwidth_sent' => $stats['bandwidth_sent'],
                                'last_update' => $stats['last_update'],
                                'last_reset' => $stats['last_reset']
                            ]
                        ]
                    ];
                    
                    $this->sendJsonResponse([
                        'success' => true,
                        'data' => $formattedStats
                    ]);
                } else {
                    $this->sendJsonResponse([
                        'success' => true,
                        'data' => [
                            'channel_id' => $channel['id'],
                            'name' => $channel['name'],
                            'stats' => [
                                'traffic' => ['received' => '0 B', 'sent' => '0 B'],
                                'bandwidth' => ['download' => '0 B/s', 'upload' => '0 B/s'],
                                'last_update' => date('Y-m-d H:i:s', $timestamp)
                            ]
                        ]
                    ]);
                }
            } else {
                // 获取所有频道的统计数据
                $stmt = $this->db->query("SELECT id, name FROM channels WHERE status = 1");
                $channels = $stmt->fetchAll(\PDO::FETCH_ASSOC);
                
                $stats = [];
                $totalDownloadSpeed = 0;
                $totalUploadSpeed = 0;
                $totalReceived = 0;
                $totalSent = 0;
                $activeChannelsWithTraffic = 0;
                
                foreach ($channels as $channel) {
                    $key = "proxy:stats:{$channel['id']}";
                    $currentStats = $this->redis->get($key);
                    $channelStats = $currentStats ? json_decode($currentStats, true) : null;
                    
                    if ($channelStats) {
                        // 累加总流量和带宽
                        $totalReceived += $channelStats['bytes_received'];
                        $totalSent += $channelStats['bytes_sent'];
                        $totalDownloadSpeed += $channelStats['bandwidth_received'];
                        $totalUploadSpeed += $channelStats['bandwidth_sent'];
                        
                        if ($channelStats['bandwidth_received'] > 0 || $channelStats['bandwidth_sent'] > 0) {
                            $activeChannelsWithTraffic++;
                        }
                        
                        $stats[$channel['id']] = [
                            'channel_id' => $channel['id'],
                            'name' => $channel['name'],
                            'stats' => [
                                'traffic' => [
                                    'received' => $this->formatBytes($channelStats['bytes_received']),
                                    'sent' => $this->formatBytes($channelStats['bytes_sent'])
                                ],
                                'bandwidth' => [
                                    'download' => $this->formatBytes($channelStats['bandwidth_received']) . '/s',
                                    'upload' => $this->formatBytes($channelStats['bandwidth_sent']) . '/s'
                                ],
                                'last_update' => date('Y-m-d H:i:s', $channelStats['last_update'])
                            ]
                        ];
                    }
                }
                
                $this->sendJsonResponse([
                    'success' => true,
                    'data' => [
                        'total' => [
                            'traffic' => [
                                'received' => $this->formatBytes($totalReceived),
                                'sent' => $this->formatBytes($totalSent)
                            ],
                            'bandwidth' => [
                                'download' => $this->formatBytes($totalDownloadSpeed) . '/s',
                                'upload' => $this->formatBytes($totalUploadSpeed) . '/s'
                            ],
                            'last_update' => date('Y-m-d H:i:s', $timestamp),
                            'active_channels' => count($channels),
                            'channels_with_traffic' => $activeChannelsWithTraffic,
                            'debug' => [
                                'download_speed_raw' => $totalDownloadSpeed,
                                'upload_speed_raw' => $totalUploadSpeed,
                                'channels_checked' => count($channels),
                                'active_channels_with_traffic' => $activeChannelsWithTraffic,
                                'timestamp' => [
                                    'current' => $timestamp,
                                    'formatted' => date('Y-m-d H:i:s', $timestamp)
                                ]
                            ]
                        ],
                        'channels' => $stats
                    ]
                ]);
            }
        } catch (\Exception $e) {
            $this->logError("获取带宽统计信息时发生错误: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            $this->sendJsonResponse([
                'success' => false,
                'message' => '获取带宽统计失败: ' . $e->getMessage()
            ]);
        }
    }

/**
 * 格式化字节大小
 * 将字节数转换为人类可读的格式
 * 
 * @param float $bytes 字节数
 * @param int $precision 精确度
 * @return string 格式化后的大小字符串
 */
private function formatBytes($bytes, $precision = 2)
{
    $units = ['B', 'KB', 'MB', 'GB', 'TB'];
    
    $bytes = max($bytes, 0);
    $pow = floor(($bytes ? log($bytes) : 0) / log(1024));
    $pow = min($pow, count($units) - 1);
    
    $bytes /= (1 << (10 * $pow));
    
    return round($bytes, $precision) . ' ' . $units[$pow];
}
    
    private function logError($message, $level = 'error', $file = null, $line = null)
    {
        // 获取调用堆栈
        $trace = debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS);
        array_shift($trace); // 移除当前方法的堆栈
        
        // 如果没有提供文件和行号，使用调用者的信息
        if ($file === null && !empty($trace[0]['file'])) {
            $file = $trace[0]['file'];
        }
        if ($line === null && !empty($trace[0]['line'])) {
            $line = $trace[0]['line'];
        }
        
        // 记录到错误日志数据库
        try {
            $this->errorLog->add([
                'level' => $level,
                'message' => $message,
                'file' => $file,
                'line' => $line,
                'trace' => json_encode($trace, JSON_UNESCAPED_UNICODE)
            ]);
        } catch (\Exception $e) {
            // 如果记录错误日志失败，至少要记录到系统日志
            error_log("Error logging to database: " . $e->getMessage());
        }
        
        // 同时记录到系统日志
        $this->logger->$level($message);
    }
} 