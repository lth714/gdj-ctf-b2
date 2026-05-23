<?php
namespace App\Proxy;

use App\Models\Channel;
use App\Models\ErrorLog;
use App\Core\Logger;
use App\Core\Config;
use App\Core\Database;
use App\Core\Redis;
use App\Core\ChannelContentCache;
use App\Core\AsyncLoader;

/**
 * IPTV代理服务器类
 * 负责处理IPTV流媒体代理、缓存和分发
 */
class Server 
{
    private $logger;
    private $config;
    private $isRunning = false;
    private $socket;
    private $clients = [];
    private $channels = [];
    private $db;
    private $errorLog;
    private $redis;
    private $cache;
    private $asyncLoader;
    
    /**
     * 构造函数
     * 初始化代理服务器所需的各种组件和依赖
     * 包括日志记录器、配置、数据库连接、Redis缓存等
     */
    public function __construct()
    {
        $this->logger = new Logger();
        $this->config = Config::getInstance();
        $this->loadChannels();
        $this->db = \App\Core\Database::getInstance()->getConnection();
        $this->errorLog = new ErrorLog();
        $this->redis = new Redis();
        $this->cache = ChannelContentCache::getInstance();
        //$this->asyncLoader = new AsyncLoader();
        $this->asyncLoader = new AsyncLoader($this->redis);  // 传入redis实例
    }
    /**
     * 记录程序错误日志
     * 将错误信息记录到数据库和系统日志中
     * 
     * @param string $message 错误信息
     * @param string $level 错误级别
     * @param string|null $file 文件路径
     * @param mixed $context 行号或额外信息
     */
    private function logError($message, $level = 'error', $file = null, $context = null)
    {
        // 获取调用堆栈
        $trace = debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS);
        array_shift($trace); // 移除当前方法的堆栈
        
        // 如果没有提供文件，使用调用者的信息
        if ($file === null && !empty($trace[0]['file'])) {
            $file = $trace[0]['file'];
        }

        // 初始化行号和额外信息
        $line = null;
        $additionalInfo = '';
        
        // 处理 $context 参数
        if (is_numeric($context)) {
            $line = $context;
        } else {
            $additionalInfo = $context;
        }
        
        // 如果没有提供行号且堆栈中有行号，使用堆栈中的行号
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
                'trace' => $additionalInfo ?: json_encode($trace, JSON_UNESCAPED_UNICODE) // 如果有额外信息，使用额外信息，否则使用堆栈
            ]);
        } catch (\Exception $e) {
            // 如果记录错误日志失败，至少要记录到系统日志
            error_log("Error logging to database: " . $e->getMessage());
        }
        
        // 同时记录到系统日志
        $this->logger->$level($message . ($additionalInfo ? " | {$additionalInfo}" : ''));
    }
    
    
    /**
     * 加载频道列表
     * 从数据库中获取前1000个频道的信息
     */
    private function loadChannels()
    {
        try {
            $channelModel = new Channel();
            $result = $channelModel->getChannelList(1, 1000); // 获取前1000个频道
            $this->channels = $result['channels'];
        } catch (\Exception $e) {
            $this->logError("加载频道列表失败: " . $e->getMessage(), 'error', __FILE__, __LINE__);
        }
    }
    
    /**
     * 启动代理服务器
     * 创建TCP服务器并开始监听指定端口
     * 
     * @return bool 启动是否成功
     */
    public function start()
    {
        if ($this->isRunning) {
            return false;
        }
        
        try {
            // 创建 TCP 服务器
            $address = $this->config->get('proxy_host', '0.0.0.0');
            $port = $this->config->get('proxy_port', 8080);
            
            $this->logError("正在启动代理服务器...", 'info', __FILE__, __LINE__);
            
            $this->socket = stream_socket_server("tcp://{$address}:{$port}", $errno, $errstr);
            if (!$this->socket) {
                $this->logError("创建服务器失败: {$errstr} ({$errno})", 'error', __FILE__, __LINE__);
                return false;
            }
            
            $this->isRunning = true;
            $this->logError("代理服务器已启动: {$address}:{$port}", 'info', __FILE__, __LINE__);
            
            return true;
        } catch (\Exception $e) {
            $this->logError("启动代理服务器失败: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            return false;
        }
    }
    
    /**
     * 处理客户端错误
     * 记录客户端连接过程中的错误信息
     * 
     * @param resource $client 客户端连接资源
     * @param string $message 错误信息
     * @param string $level 错误级别
     */
    private function handleClientError($client, $message, $level = 'error')
    {
        $clientId = (int)$client;
        $clientIp = stream_socket_get_name($client, true);
        $channelId = $this->clients[$clientId]['channel_id'] ?? null;
        
        $errorMessage = sprintf(
            "客户端错误 [IP: %s, Channel: %s]: %s",
            $clientIp,
            $channelId ? "#{$channelId}" : 'Unknown',
            $message
        );
        
        $this->logError($errorMessage, $level, __FILE__, __LINE__);
    }
    
    /**
     * 处理客户端连接
     * 主要的连接处理循环，负责接受新连接和处理现有连接的数据
     */
    private function processConnections()
    {
        try {
            // 准备 socket 数组用于 select
            $read = [];
            foreach ($this->clients as $clientInfo) {
                if (!is_resource($clientInfo['socket']) || @feof($clientInfo['socket'])) {
                    $this->removeClient($clientInfo['socket']);
                    continue;
                }
                $read[] = $clientInfo['socket'];
            }
            $read[] = $this->socket;
            $write = null;
            $except = null;
            
            // 使用 select 监听连接，设置超时时间为 0.2 秒
            if (@stream_select($read, $write, $except, 0, 200000) > 0) {
                // 检查新连接
                if (in_array($this->socket, $read)) {
                    $client = @stream_socket_accept($this->socket);
                    if ($client) {
                        stream_set_blocking($client, false);
                        stream_set_timeout($client, $this->config->get('proxy_timeout', 10));
                        $clientId = (int)$client;
                        $this->clients[$clientId] = [
                            'socket' => $client,
                            'last_activity' => time()
                        ];
                    }
                    unset($read[array_search($this->socket, $read)]);
                }
                
                // 处理现有连接
                foreach ($read as $client) {
                    $clientId = (int)$client;
                    $data = @fread($client, 4096);
                    
                    if ($data === false || $data === '') {
                        $this->removeClient($client);
                        continue;
                    }
                    
                    // 更新最后活动时间
                    if (isset($this->clients[$clientId])) {
                        $this->clients[$clientId]['last_activity'] = time();
                    }
                    
                    try {
                        // 处理 HTTP 请求
                        $this->handleRequest($client, $data);
                    } catch (\Exception $e) {
                        $this->logError("处理客户端请求时发生错误 (ID: $clientId): " . $e->getMessage(), 'error', __FILE__, __LINE__);
                        $this->removeClient($client);
                    }
                }
            }
            
            // 清理超时连接
            $this->cleanupTimeoutConnections();
            
        } catch (\Exception $e) {
            $this->logError("处理连接时发生错误: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            $this->logError("错误堆栈: " . $e->getTraceAsString(), 'error', __FILE__, __LINE__);
        }
    }
    
    /**
     * 清理超时连接
     * 检查并关闭超过指定时间未活动的连接
     */
    private function cleanupTimeoutConnections()
    {
        $now = time();
        $timeout = $this->config->get('connection_timeout', 60); // 60秒超时
        
        foreach ($this->clients as $clientId => $clientInfo) {
            if (isset($clientInfo['last_activity']) && ($now - $clientInfo['last_activity'] > $timeout)) {
                $this->logError("连接超时，正在清理 (ID: $clientId)", 'info', __FILE__, __LINE__);
                $this->removeClient($clientInfo['socket']);
            }
        }
    }
    
    /**
     * 记录客户端连接信息
     * 将新的客户端连接信息记录到数据库和Redis中
     * 
     * @param resource $client 客户端连接资源
     * @param string $channelId 频道ID
     */
    private function recordConnection($client, $channelId)
    {
        try {
            $clientId = (int)$client;
            
            // 获取 User-Agent
            $userAgent = '-';
            $request = $this->clients[$clientId]['request'] ?? '';
            if (preg_match('/User-Agent: (.*?)[\r\n]/i', $request, $matches)) {
                $userAgent = trim($matches[1]);
            }
            
            // 获取客户端 IP，去除端口号
            $clientIp = stream_socket_get_name($client, true);
            $clientIp = preg_replace('/:\d+$/', '', $clientIp); // 移除端口号
            
            // 使用 IP（不含端口）、User-Agent 和频道 ID 生成唯一会话 ID
            $sessionId = md5($clientIp . $userAgent . $channelId);
            
            // 先检查是否存在活跃连接
            $stmt = $this->db->prepare("SELECT session_id FROM channel_connections 
                WHERE client_ip LIKE ? 
                AND user_agent = ? 
                AND channel_id = ? 
                AND status = 'active' 
                AND last_active_time > DATE_SUB(NOW(), INTERVAL 1 MINUTE)");
            $stmt->execute([$clientIp . '%', $userAgent, $channelId]);
            $existingSession = $stmt->fetch(\PDO::FETCH_ASSOC);
            
            if ($existingSession) {
                // 使用现有会话
                if (!isset($this->clients[$clientId])) {
                    $this->clients[$clientId] = ['socket' => $client];
                }
                $this->clients[$clientId]['session_id'] = $existingSession['session_id'];
                $this->clients[$clientId]['channel_id'] = $channelId;
                
                // 更新最后活跃时间
                $this->updateConnectionStatus($client);
                return;
            }
            
            // 如果没有活跃连接，清理旧连接并创建新连接
            $stmt = $this->db->prepare("UPDATE channel_connections 
                SET status = 'disconnected', 
                    disconnect_time = NOW() 
                WHERE client_ip LIKE ? 
                AND user_agent = ? 
                AND channel_id = ? 
                AND status = 'active'");
            $stmt->execute([$clientIp . '%', $userAgent, $channelId]);
            
            // 记录新连接
            $stmt = $this->db->prepare("INSERT INTO channel_connections 
                (channel_id, client_ip, user_agent, session_id, connect_time, last_active_time, status) 
                VALUES (?, ?, ?, ?, NOW(), NOW(), 'active')");
            $stmt->execute([$channelId, $clientIp, $userAgent, $sessionId]);
            
            // 存储 session_id 到 clients 数组中
            if (!isset($this->clients[$clientId])) {
                $this->clients[$clientId] = ['socket' => $client];
            }
            $this->clients[$clientId]['session_id'] = $sessionId;
            $this->clients[$clientId]['channel_id'] = $channelId;
            
            // Redis 连接计数只在新会话时增加
            $key = "proxy:connections:{$channelId}";
            $count = $this->redis->get($key) ?: 0;
            $this->redis->set($key, $count + 1);
            
            // 记录会话活跃时间
            $activeKey = "proxy:connection:active:{$channelId}:{$sessionId}";
            $this->redis->set($activeKey, time());
            
        } catch (\Exception $e) {
            $this->logError("记录连接信息时发生错误: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            $this->logError("错误堆栈: " . $e->getTraceAsString(), 'error', __FILE__, __LINE__);
            // 继续处理请求，不要因为记录失败而中断服务
        }
    }
    
    /**
     * 更新连接状态
     * 更新数据库和Redis中的连接活跃状态
     * 
     * @param resource $client 客户端连接资源
     */
    private function updateConnectionStatus($client)
    {
        try {
            $clientId = (int)$client;
            if (isset($this->clients[$clientId]['session_id'])) {
                $sessionId = $this->clients[$clientId]['session_id'];
                $channelId = $this->clients[$clientId]['channel_id'];

                // 更新数据库中的连接状态
                $stmt = $this->db->prepare("UPDATE channel_connections 
                    SET last_active_time = NOW(), status = 'active' 
                    WHERE session_id = ?");
                $stmt->execute([$sessionId]);
                
                // 更新最后活跃时间
                $activeKey = "proxy:connection:active:{$channelId}:{$sessionId}";
                $this->redis->set($activeKey, time());
            }
        } catch (\Exception $e) {
            $this->logError("更新连接状态时发生错误: " . $e->getMessage(), 'error', __FILE__, __LINE__);
        }
    }
        
    /**
     * 关闭连接
     * 清理连接相关的资源和记录
     * 
     * @param resource $client 客户端连接资源
     */
    private function closeConnection($client)
    {
        try {
            $clientId = (int)$client;
            if (isset($this->clients[$clientId]['session_id'])) {
                $sessionId = $this->clients[$clientId]['session_id'];
                $channelId = $this->clients[$clientId]['channel_id'];
                
                // 更新数据库状态
                $stmt = $this->db->prepare("UPDATE channel_connections 
                    SET status = 'disconnected', 
                        disconnect_time = NOW() 
                    WHERE session_id = ? 
                    AND status = 'active'");
                $stmt->execute([$sessionId]);
                
                // 减少 Redis 中的连接计数
                $key = "proxy:connections:{$channelId}";
                $count = $this->redis->get($key) ?: 0;
                if ($count > 0) {
                    $this->redis->set($key, $count - 1);
                }
                
                // 删除活跃会话记录
                $activeKey = "proxy:connection:active:{$channelId}:{$sessionId}";
                $this->redis->del($activeKey);
            }
        } catch (\Exception $e) {
            $this->logError("关闭连接时发生错误: " . $e->getMessage(), 'error', __FILE__, __LINE__);
        }
    }
    
    /**
     * 清理不活跃连接
     * 定期检查并清理Redis中的不活跃连接记录
     */
    private function cleanInactiveConnections()
    {
        try {
            // 获取所有活跃会话
            $keys = $this->redis->keys('proxy:connection:active:*');
            $now = time();
            
            foreach ($keys as $key) {
                $lastActive = $this->redis->get($key);
                if ($now - $lastActive > 180) { // 60秒无活动视为断开
                    // 解析频道ID和会话ID
                    $parts = explode(':', $key);
                    $channelId = $parts[3];
                    $sessionId = $parts[4];
                    
                    // 更新数据库状态
                    $stmt = $this->db->prepare("UPDATE channel_connections 
                        SET status = 'disconnected',
                            disconnect_time = NOW() 
                        WHERE session_id = ? 
                        AND status = 'active'");
                    $stmt->execute([$sessionId]);
                    
                    // 减少连接计数
                    $countKey = "proxy:connections:{$channelId}";
                    $count = $this->redis->get($countKey) ?: 0;
                    if ($count > 0) {
                        $this->redis->set($countKey, $count - 1);
                    }
                    
                    // 删除活跃会话记录
                    $this->redis->del($key);
                }
            }
        } catch (\Exception $e) {
            $this->logError("清理不活跃连接时发生错误: " . $e->getMessage(), 'warning', __FILE__, __LINE__);
        }
    }
    
    /**
     * 处理HTTP请求
     * 解析和处理客户端的HTTP请求，包括m3u8和ts文件的请求
     * 
     * @param resource $client 客户端连接资源
     * @param string $data 请求数据
     */
    private function handleRequest($client, $data)
    {
        $clientId = (int)$client;
        // 存储请求数据供后续使用
        //$this->logError("【handleRequest】开始处理", 'warning', __FILE__, __LINE__);
        if (!isset($this->clients[$clientId])) {
            $this->clients[$clientId] = [];
        }
        $this->clients[$clientId]['request'] = $data;

        // 解析 HTTP 请求
        $lines = explode("\r\n", $data);
        $firstLine = explode(' ', $lines[0]);
        
        if (count($firstLine) < 2) {
            $this->removeClient($client);
            return;
        }
        
        $method = $firstLine[0];
        $path = $firstLine[1];
        
        // 获取User-Agent
        $userAgent = '-';
        foreach ($lines as $line) {
            if (stripos($line, 'User-Agent:') === 0) {
                $userAgent = trim(substr($line, 11));
                break;
            }
        }
        
        // 从路径中提取频道ID和请求类型
        if (preg_match('/^\/proxy\/(ch_[^\/]+)\/([^\/\?]+(?:\?[^\/?]+)?)/', $path, $matches)) {
            $channelId = $matches[1];
            $requestFile = $matches[2];
            
            // 查找对应的频道
            $channel = $this->findChannel($channelId);
            
            if (!$channel) {
                //$this->logError("未找到频道: $channelId", 'warning', __FILE__, __LINE__);
                $response = "HTTP/1.1 404 Not Found\r\n";
                $response .= "Content-Type: text/plain\r\n";
                $response .= "Connection: close\r\n\r\n";
                $response .= "Channel not found";
                @fwrite($client, $response);
                $this->removeClient($client);
                return;
            }

            //$this->logError("【handleRequest】找到频道 - 频道ID: {$channel['id']}, 客户端ID: {$clientId}", 'info', __FILE__, __LINE__);
            
            // 获取客户端IP
            $clientIp = stream_socket_get_name($client, true);
            
            // 使用 Redis 分布式锁处理 stream.m3u8 请求
            if ($requestFile === 'stream.m3u8') {
                $lockKey = "lock:connection:{$channel['id']}:{$clientIp}:{$userAgent}";
                
                try {
                    // 尝试获取锁，超时时间为5秒
                    if ($this->redis->set($lockKey, 1, ['NX', 'EX' => 5])) {
                        try {
                            $stmt = $this->db->prepare("SELECT session_id FROM channel_connections 
                                WHERE client_ip = ? 
                                AND user_agent = ? 
                                AND channel_id = ? 
                                AND status = 'active' 
                                AND last_active_time > DATE_SUB(NOW(), INTERVAL 1 MINUTE)");
                            $stmt->execute([$clientIp, $userAgent, $channel['id']]);
                            $existingSession = $stmt->fetch(\PDO::FETCH_ASSOC);

                            if (!$existingSession) {
                                $this->recordConnection($client, $channel['id']);
                            } else {
                                if (!isset($this->clients[$clientId])) {
                                    $this->clients[$clientId] = ['socket' => $client];
                                }
                                $this->clients[$clientId]['session_id'] = $existingSession['session_id'];
                                $this->clients[$clientId]['channel_id'] = $channel['id'];
                                $this->updateConnectionStatus($client);
                            }
                        } finally {
                            // 确保释放锁
                            $this->redis->del($lockKey);
                        }
                    } else {
                        // 如果获取锁失败，等待短暂时间后继续处理
                        usleep(100000); // 等待100ms
                    }
                } catch (\Exception $e) {
                    $this->logError("检查活跃连接时发生错误: " . $e->getMessage(), 'warning', __FILE__, __LINE__);
                }
            }

            // 根据请求类型选择不同的处理方式
            if ($requestFile === 'stream.m3u8') {
                $this->proxyM3U8($client, $channel);
            } else if (preg_match('/\.ts*/', $requestFile)) {
                //$this->logError("【handleRequest】开始处理 - 频道ID: {$channel['id']}, tsFile: {$requestFile}", 'info', __FILE__, __LINE__);
                $this->proxyTS($client, $channel, $requestFile);
            } else {
                $this->logError("不支持的文件类型: $requestFile", 'warning', __FILE__, __LINE__);
                $response = "HTTP/1.1 400 Bad Request\r\n";
                $response .= "Content-Type: text/plain\r\n";
                $response .= "Connection: close\r\n\r\n";
                $response .= "Unsupported file type";
                @fwrite($client, $response);
                $this->removeClient($client);
            }
        } else {
            $this->logError("无效的URL格式: $path", 'warning', __FILE__, __LINE__);
            $response = "HTTP/1.1 404 Not Found\r\n";
            $response .= "Content-Type: text/plain\r\n";
            $response .= "Connection: close\r\n\r\n";
            $response .= "Invalid channel URL format";
            @fwrite($client, $response);
            $this->removeClient($client);
            return;
        }
    }
    
    /**
     * 处理M3U8文件请求
     * 获取、缓存和发送M3U8播放列表
     * 
     * @param resource $client 客户端连接资源
     * @param array $channel 频道信息
     */
    private function proxyM3U8($client, $channel)
    {
        $clientId = (int)$client;
        //$this->logError("【proxyM3U8】开始处理 - 频道ID: {$channel['id']}, 客户端ID: {$clientId}", 'info', __FILE__, __LINE__);
        
        // 尝试获取缓存的内容
        $content = $this->cache->m3u8Cache($channel['id']);
        
        if ($content === null) {
            //$this->logError("【proxyM3U8】缓存未命中，准备从源获取 - URL: {$channel['source_url']}", 'info', __FILE__, __LINE__);
            
            // 获取原始m3u8内容
            $context = stream_context_create([
                'http' => [
                    'timeout' => $this->config->get('proxy_timeout', 10),
                    'user_agent' => 'VLC/3.0.20 LibVLC/3.0.20'
                ]
            ]);
            
            $content = @file_get_contents($channel['source_url'], false, $context);
            if ($content === false) {
                //$this->logError("【proxyM3U8】获取源内容失败 - 频道ID: {$channel['id']}", 'error', __FILE__, __LINE__);
                $this->removeClient($client);
                return;
            }
            
            //$this->logError("【proxyM3U8】成功获取源内容 - 长度: " . strlen($content) . "内容：" . $content, 'info', __FILE__, __LINE__);
            
            // 缓存M3U8内容
            
            $this->cache->m3u8Cache($channel['id'], [
                'content' => $content,
                'time' => time()
            ]);
            
            //$this->logError("【proxyM3U8】已缓存M3U8内容,channel[id]:{$channel['id']}", 'info', __FILE__, __LINE__);
        } else {
            //$this->logError("【proxyM3U8】使用缓存内容 - 长度: " . strlen($content), 'info', __FILE__, __LINE__);
        }
        //$this->logError("【proxyM3U8】准备修改TS路径", 'info', __FILE__, __LINE__);
        // 修改m3u8内容中的ts文件路径
        $baseUrl = dirname($channel['proxy_url']);
        $content = preg_replace_callback('/^(.*\.ts*)/m', function($matches) use ($baseUrl) {
            $tsFile = basename($matches[0]);
            $proxyPath = $baseUrl . '/' . $tsFile;
            return $proxyPath;
        }, $content);
        //$this->logError("【proxyM3U8】修改TS路径后的文件：" . $content, 'info', __FILE__, __LINE__);
       
        // 发送响应
        $response = "HTTP/1.1 200 OK\r\n";
        $response .= "Content-Type: application/vnd.apple.mpegurl\r\n";
        $response .= "Access-Control-Allow-Origin: *\r\n";
        $response .= "Cache-Control: no-cache\r\n";
        $response .= "Content-Length: " . strlen($content) . "\r\n";
        $response .= "Connection: close\r\n\r\n";
        $response .= $content;
        
        $writeResult = @fwrite($client, $response);
        if ($writeResult === false) {
            //$this->logError("【proxyM3U8】响应写入失败 - 频道ID: {$channel['id']}", 'error', __FILE__, __LINE__);
        } else {
            //$this->logError("【proxyM3U8】成功发送响应 - 长度: " . strlen($response), 'info', __FILE__, __LINE__);
        }
        
        // 异步处理分片信息
        if ($content !== null) {
            try {
                $baseUrl = dirname($channel['source_url']);
                //$this->logError("【proxyM3U8】开始异步处理分片信息", 'info', __FILE__, __LINE__);
                $this->cache->parseAndCacheM3u8($channel['id'], $content, $baseUrl);
                //$this->logError("【proxyM3U8】完成异步处理分片信息", 'info', __FILE__, __LINE__);
            } catch (\Exception $e) {
                //$this->logError("【proxyM3U8】异步处理分片信息失败: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            }
        }
    }
    
    /**
     * 使用分块传输发送响应
     * 支持大文件的高效传输
     * 
     * @param resource $client 客户端连接资源
     * @param string|resource $content 要发送的内容或源文件流
     * @param array $channel 频道信息
     * @param bool $isStream 是否是流式内容
     * @return bool|string 发送是否成功或处理后的内容
     */
    private function sendChunkedResponse($client, $content, $channel, $isStream = false)
    {
        try {
            //$this->logError("【sendChunkedResponse】开始处理", 'info', __FILE__, __LINE__);
            // 发送 HTTP 头
            $headers = [
                "HTTP/1.1 200 OK",
                "Content-Type: video/mp2t",
                "Access-Control-Allow-Origin: *",
                "Cache-Control: no-cache",
                "Connection: close",
                "Transfer-Encoding: chunked",
                ""
            ];
            
            if (@fwrite($client, implode("\r\n", $headers) . "\r\n") === false) {
                return false;
            }

            // 使用分块传输
            $totalReceived = 0;
            $totalSent = 0;
            $bufferSize = ($this->config->get('proxy_buffer_size', 4096) * 1024 * 1024); // 缓冲区的大小
            $tempContent = ''; // 用于累积完整内容以便缓存

            if ($isStream) {
                //$this->logError("【sendChunkedResponse】开始流媒体数据发送", 'info', __FILE__, __LINE__);
                // 处理流式内容
                while (!feof($content)) {
                    $chunk = @fread($content, $bufferSize);
                    if ($chunk === false) {
                        //$this->logError("读取块失败[0x015]", 'warning', __FILE__, __LINE__);
                        break;
                    }

                    $chunkLength = strlen($chunk);
                    $tempContent .= $chunk;

                    // 写入块大小（十六进制）
                    if (@fwrite($client, dechex($chunkLength) . "\r\n") === false) {
                        break;
                    }
                    // 写入块内容
                    $written = @fwrite($client, $chunk . "\r\n");
                    if ($written === false) {
                        //$this->logError("写入块内容失败[0x018]", 'warning', __FILE__, __LINE__);
                        break;
                    }

                    $totalReceived += $chunkLength;
                    $totalSent += $written;
                }
                // 从源服务器读取的数据是下行带宽，发送给客户端的是上行带宽
                $this->updateBandwidthStats($channel['id'], $totalReceived, $totalSent);
                //$this->logError("【sendChunkedResponse】流媒体数据发送结束", 'info', __FILE__, __LINE__);
            } else {
                //$this->logError("【sendChunkedResponse】开始处理字符串内容", 'info', __FILE__, __LINE__);
                // 处理字符串内容
                for ($i = 0; $i < strlen($content); $i += $bufferSize) {
                    $chunk = substr($content, $i, $bufferSize);
                    $chunkLength = strlen($chunk);
                    /*
                    // 写入块大小
                    $hexLength = dechex($chunkLength) . "\r\n";
                    $written1 = 0;
                    while ($written1 < strlen($hexLength)) {
                        $result = @fwrite($client, substr($hexLength, $written1));
                        if ($result === false) {
                            //$this->logError("写入块大小失败", 'error', __FILE__, __LINE__);
                            return false;
                        }
                        $written1 += $result;
                    }
                    */
                    // 写入块内容
                    $chunk = dechex($chunkLength) . "\r\n" . $chunk . "\r\n";
                    //$chunk .= "\r\n";
                    $written2 = 0;
                    while ($written2 < strlen($chunk)) {
                        $result = @fwrite($client, substr($chunk, $written2));
                        if ($result === false) {
                            //$this->logError("写入块内容失败", 'error', __FILE__, __LINE__);
                            return false;
                        }
                        $written2 += $result;
                    }
                
                    $totalReceived += $chunkLength;
                    $totalSent += $written2;
                }
                //从缓存读取不产生下行带宽，只有发送给客户端的上行带宽
                $this->updateBandwidthStats($channel['id'], 0, $totalSent);
                //$this->logError("[sendChunkedResponse]结束向客户端发送缓存内容，原始数据量：" . $totalReceived . ", 发送大小：" . $totalSent, 'warning', __FILE__, __LINE__);
            }
            // 写入结束块
            @fwrite($client, "0\r\n\r\n");
            //$this->logError("【sendChunkedResponse】结束块写入", 'info', __FILE__, __LINE__);
            return $isStream ? $tempContent : true;
        } catch (\Exception $e) {
            $this->logError("分块传输失败: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            return false;
        }
    }

    /**
     * 处理TS文件请求
     * 获取、缓存和发送TS视频片段
     * 
     * @param resource $client 客户端连接资源
     * @param array $channel 频道信息
     * @param string $tsFile TS文件名
     */
    private function proxyTS($client, $channel, $tsFile)
    {
        try {
            //$this->logError("【proxyTS】开始处理 - 频道ID: {$channel['id']}, tsFile: {$tsFile}", 'info', __FILE__, __LINE__);
            $clientId = (int)$client;

            // 构建源URL
            $baseUrl = dirname($channel['source_url']);
            $sourceUrl = $this->buildSourceUrl($baseUrl, $tsFile);
            //$this->logError("【proxyTS】sourceUrl：" . $sourceUrl, 'info', __FILE__, __LINE__);
            if (($this->config->get('enable_memory_cache', false)==true || $this->config->get('enable_redis_cache', false)==true)){
                // 生成缓存键
                $parsedUrl = parse_url($sourceUrl);
                $path = $parsedUrl['path'];
                $baseUrl = str_replace('/proxy/', '/', $path);
                $baseUrl = preg_replace('/\/ch_[^\/]+\//', '/', $baseUrl);
                $cacheKey = "ts:{$channel['id']}:" . md5($baseUrl);
                //$this->logError("【proxyTS】尝试从缓存获取 - 频道ID: {$channel['id']}, 缓存键: {$cacheKey},baseUrl:{$baseUrl}", 'info', __FILE__, __LINE__);
                // 尝试从缓存获取
                $cachedContent = $this->cache->getTs($channel['id'], $sourceUrl);
                if ($cachedContent !== null) {
                    $this->logError("【proxyTS】缓存命中 - 频道ID: {$channel['id']}, 缓存键: {$cacheKey}", 'info',"", "");
                    // 发送缓存的内容
                    $this->sendChunkedResponse($client, $cachedContent, $channel, false);
                    return;
                }
                //$this->logError("【proxyTS】缓存未命中 - 频道ID: {$channel['id']}, 缓存键: {$cacheKey}", 'info', __FILE__, __LINE__);
            }
            // 设置自定义标头
            $customHeaders = [
                "Accept-Language: zh-CN,zh;q=0.9",
                "Cache-Control: max-age=0",
                "Upgrade-Insecure-Requests: 1",
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.95 Safari/537.36",
                "Referrer-Policy: strict-origin-when-cross-origin"
            ];
            // 设置上下文选项
            $context = stream_context_create([
                'http' => [
                    'timeout' => $this->config->get('proxy_timeout', 10),
                    'user_agent' => 'VLC/3.0.20 LibVLC/3.0.20',
                    'header' => implode("\r\n", $customHeaders)  // 在上下文中添加自定义标头
                ],
                'ssl' => [
                    'verify_peer' => false,
                    'verify_peer_name' => false
                ]
            ]);
            //$this->logError("【proxyTS】设置上下文选项", 'info', __FILE__, __LINE__);
            // 打开源文件流
            $source = @fopen($sourceUrl, 'rb', false, $context);
            if ($source) {
                $bufferSize = ($this->config->get('proxy_buffer_size', 4096) * 1024 * 1024); // 缓冲区的大小
                stream_set_read_buffer($source, $bufferSize);  // 读取缓冲
                stream_set_chunk_size($source, $bufferSize);   // 块大小
                stream_set_write_buffer($client, $bufferSize); // 写入缓冲

                if (function_exists('socket_import_stream')) {
                    $socket = socket_import_stream($source);
                    socket_set_option($socket, SOL_SOCKET, SO_RCVBUF, $bufferSize);
                }
                //$this->logError("【proxyTS】打开源文件流", 'info', __FILE__, __LINE__);
            }
            if (!$source) {
                $error = error_get_last();
                
                //$this->logError("【proxyTS】无法打开TS文件[0x009]: " . ($error['message'] ?? '未知错误'), 'warning', __FILE__, __LINE__);
                $this->removeClient($client);
                return;
            }
            //$this->logError("【proxyTS】打开源文件流成功", 'info', __FILE__, __LINE__);
            // 使用分块传输发送内容并获取完整内容
            $content = $this->sendChunkedResponse($client, $source, $channel, true);
            //$this->logError("【proxyTS】分块传输发送内容并获取完整内容", 'info', __FILE__, __LINE__);
            //下面注释掉的代码，不要删除，以后可能用得上
            if ($content !== false && ($this->config->get('enable_memory_cache', false)==true || $this->config->get('enable_redis_cache', false)==true)) {
                // 缓存完整的内容
                $this->cache->cacheTs($channel['id'], $sourceUrl, $content);
                //$this->logError("【proxyTS】缓存完整的内容,sourceUrl:{$sourceUrl}", 'info', __FILE__, __LINE__);
            }
            // 触发预加载下一个分片
            $this->triggerNextSegmentPreload($channel['id'], $tsFile);
            //$this->logError("【proxyTS】触发预加载下一个分片", 'info', __FILE__, __LINE__);
            @fclose($source);
            $this->removeClient($client);
            //$this->logError("【proxyTS】关闭源文件流", 'info', __FILE__, __LINE__);

        } catch (\Exception $e) {
            $this->logError("处理TS文件时发生错误[0x026]: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            $this->logError("错误堆栈[0x027]: " . $e->getTraceAsString(), 'error', __FILE__, __LINE__);
            if (isset($source)) {
                @fclose($source);
            }
            $this->removeClient($client);
        }
    }

    /**
     * 格式化字节大小
     * 将字节数转换为人类可读的格式
     * 
     * @param int $bytes 字节数
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

    /**
     * 查找频道信息
     * 根据频道ID在已加载的频道列表中查找对应频道
     * 
     * @param string $channelId 频道ID
     * @return array|null 频道信息或null
     */
    private function findChannel($channelId)
    {
        foreach ($this->channels as $channel) {
            // 从代理URL中提取频道ID
            if (preg_match('/^\/proxy\/(ch_[^\/]+)\//', $channel['proxy_url'], $matches)) {
                if ($matches[1] === $channelId) {
                    return $channel;
                }
            }
        }
        return null;
    }
    
    /**
     * 移除客户端连接
     * 清理客户端连接相关的所有资源和记录
     * 
     * @param resource $client 客户端连接资源
     */
    private function removeClient($client)
    {
        $clientId = (int)$client;
        
        try {
            // 在移除客户端之前，记录最后一次状态
            if (isset($this->clients[$clientId]['session_id'])) {
                $this->updateConnectionStatus($client);
            }
            
            // 确保关闭连接
            if (is_resource($client)) {
                stream_socket_shutdown($client, STREAM_SHUT_RDWR);
                @fclose($client);
            }
            
            // 移除客户端记录
            unset($this->clients[$clientId]);
            
        } catch (\Exception $e) {
            $this->logError("移除客户端时发生错误 (ID: $clientId): " . $e->getMessage(), 'warning', __FILE__, __LINE__);
        }
    }
    
    /**
     * 停止代理服务器
     * 关闭所有连接并停止服务器运行
     * 
     * @return bool 停止是否成功
     */
    public function stop()
    {
        $this->logError("正在停止代理服务器...", 'info', __FILE__, __LINE__);
        
        $this->isRunning = false;
        
        // 关闭所有客户端连接
        $clientCount = count($this->clients);
        foreach ($this->clients as $clientInfo) {
            $this->removeClient($clientInfo['socket']);
        }
        $this->clients = [];
        //$this->logError("已关闭 $clientCount 个客户端连接", 'info', __FILE__, __LINE__);
        
        // 关闭服务器 socket
        if ($this->socket) {
            @fclose($this->socket);
            $this->socket = null;
            $this->logError("已关闭服务器 socket", 'info', __FILE__, __LINE__);
        }
        
        // 清理异步加载器的子进程
        $this->cleanupAsyncProcesses();

        $this->logError("代理服务器已停止", 'info', __FILE__, __LINE__);
        return true;
    }
    /**
     * 清理异步进程
     * 等待并清理所有子进程
     */
    private function cleanupAsyncProcesses()
    {
        // 等待所有子进程结束
        while (pcntl_wait($status, WNOHANG) > 0) {
            continue;
        }
    }

    /**
     * 清理已断开的连接
     * 检查并移除已断开或无效的连接
     */
    private function cleanupDeadConnections()
    {
        try {
            foreach ($this->clients as $clientId => $clientInfo) {
                if (!is_resource($clientInfo['socket']) || @feof($clientInfo['socket'])) {
                    $this->removeClient($clientInfo['socket']);
                }
            }
        } catch (\Exception $e) {
            $this->logError("清理死连接时发生错误: " . $e->getMessage(), 'warning', __FILE__, __LINE__);
        }
    }

    /**
     * 获取服务器运行状态
     * 
     * @return bool 服务器是否正在运行
     */
    public function isRunning()
    {
        return $this->isRunning;
    }
    
    /**
     * 获取服务器状态信息
     * 返回当前服务器的运行状态、连接数等信息
     * 
     * @return array 状态信息数组
     */
    public function getStatus()
    {
        try {
            // 清理不活跃连接
            $this->cleanInactiveConnections();
            
            // 获取活跃连接数
            $stmt = $this->db->query("SELECT COUNT(*) as count FROM channel_connections WHERE status = 'active'");
            $totalConnections = $stmt->fetch(\PDO::FETCH_ASSOC)['count'];
            
            return [
                'running' => $this->isRunning,
                'clients' => count($this->clients),
                'channels' => count($this->channels),
                'connections' => $totalConnections
            ];
        } catch (\Exception $e) {
            $this->logError("获取状态时发生错误: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            return [
                'running' => $this->isRunning,
                'clients' => count($this->clients),
                'channels' => count($this->channels),
                'connections' => 0
            ];
        }
    }
    
    /**
     * 运行代理服务器
     * 服务器的主循环，处理所有连接和请求
     * 
     * @return bool 运行是否成功
     */
    public function run()
    {
        try {
            while ($this->isRunning) {
                try {
                    $this->processConnections();
                    usleep(10000); // 10ms，避免CPU占用过高
                } catch (\Exception $e) {
                    $this->logError("处理连接时发生错误: " . $e->getMessage(), 'error', __FILE__, __LINE__);
                    $this->logError("错误堆栈: " . $e->getTraceAsString(), 'error', __FILE__, __LINE__);
                    // 给系统一些恢复的时间
                    sleep(1);
                    
                    // 尝试清理可能的死连接
                    $this->cleanupDeadConnections();
                }
            }
            return true;
        } catch (\Exception $e) {
            $this->logError("代理服务器运行时发生错误: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            $this->logError("错误堆栈: " . $e->getTraceAsString(), 'error', __FILE__, __LINE__);
            return false;
        }
    }

    /**
     * 更新带宽统计信息
     * 记录和更新频道的带宽使用情况
     * 
     * @param string $channelId 频道ID
     * @param int $bytesReceived 接收的字节数
     * @param int $bytesSent 发送的字节数
     */
    private function updateBandwidthStats($channelId, $bytesReceived = 0, $bytesSent = 0)
    {
        try {
            $key = "proxy:stats:{$channelId}";
            $now = time();
            
            // 获取当前统计数据
            $currentStats = $this->redis->get($key);
            $stats = $currentStats ? json_decode($currentStats, true) : [
                'bytes_received' => 0,
                'bytes_sent' => 0,
                'last_update' => $now,
                'last_reset' => $now,
                'bandwidth_received' => 0,
                'bandwidth_sent' => 0
            ];
            
            // 累加新的字节数
            $stats['bytes_received'] += $bytesReceived;
            $stats['bytes_sent'] += $bytesSent;
            
            // 计算时间差（秒）
            $timeDiff = $now - $stats['last_reset'];
            
            // 每秒重置一次计数并计算带宽
            if ($timeDiff >= 1) {
                // 计算每秒的带宽（字节/秒）
                $stats['bandwidth_received'] = $stats['bytes_received'] / $timeDiff;
                $stats['bandwidth_sent'] = $stats['bytes_sent'] / $timeDiff;
                
                // 重置计数器
                $stats = [
                    'bytes_received' => $bytesReceived,  // 重置为新的字节数
                    'bytes_sent' => $bytesSent,
                    'bandwidth_received' => $stats['bandwidth_received'],
                    'bandwidth_sent' => $stats['bandwidth_sent'],
                    'last_update' => $now,
                    'last_reset' => $now
                ];
            }
            
            // 更新最后更新时间
            $stats['last_update'] = $now;
            
            // 将数据存储为JSON字符串
            $this->redis->setex($key, 60, json_encode($stats));  // 60秒过期
            
        } catch (\Exception $e) {
            $this->logError("更新带宽统计失败: " . $e->getMessage(), 'warning', __FILE__, __LINE__);
        }
    }

    /**
     * 从M3U8内容中获取TS片段时长
     * 
     * @param string $content M3U8内容
     * @return float TS片段的时长（秒）
     */
    private function getTsDurationFromM3U8($content)
    {
        $duration = 10; // 默认10秒
        
        // 按行分割
        $lines = explode("\n", $content);
        
        foreach ($lines as $line) {
            // 查找 #EXTINF 标签
            if (preg_match('/#EXTINF:([\d.]+)/', $line, $matches)) {
                $duration = floatval($matches[1]);
                break; // 找到第一个就返回
            }
        }
        
        return $duration;
    }

    /**
     * 触发下一个分片的预加载
     * 根据当前播放的分片预测并预加载下一个分片
     * 
     * @param string $channelId 频道ID
     * @param string $currentTsFile 当前TS文件名
     */
    private function triggerNextSegmentPreload($channelId, $currentTsFile)
    {
        try {
            //$this->logError("开始预加载处理[0x101] - 频道ID: {$channelId}, 当前TS: {$currentTsFile}", 'info', __FILE__, __LINE__);
            
            // 获取当前分片的信息
            $currentSegment = $this->getCurrentSegmentInfo($channelId, $currentTsFile);
            if ($currentSegment) {
                    // 触发预加载
                $this->cache->preloadNextSegment($channelId, $currentSegment);
            } 
        } catch (\Exception $e) {
            $this->logError("触发预加载失败[0x105]: " . $e->getMessage(), 'warning', __FILE__, __LINE__);
        }
    }

    /**
     * 获取当前分片信息
     * 根据文件名获取分片的详细信息
     * 
     * @param string $channelId 频道ID
     * @param string $tsFile TS文件名
     * @return array|null 分片信息或null
     */
    private function getCurrentSegmentInfo($channelId, $tsFile)
    {
        try {
            
            $segments = $this->cache->getChannelSegments($channelId);
            if (!$segments) {
                return null;
            }

            //$this->logError("【getCurrentSegmentInfo】tsFile：" . $tsFile, 'info', __FILE__, __LINE__);
            $tsBasename = basename($tsFile);
            //$this->logError("【getCurrentSegmentInfo】tsBasename：" . $tsBasename, 'info', __FILE__, __LINE__);
            foreach ($segments as $segment) {
                $segmentBasename = basename($segment['url']);
                //$this->logError("【getCurrentSegmentInfo】segmentBasename：" . $segmentBasename, 'info', __FILE__, __LINE__);
                
                // 使用正则表达式匹配文件名模式
                if ($this->matchTsFilenames($tsBasename, $segmentBasename)) {
                    return $segment;
                }
            }
            
            // 如果没有找到完全匹配，尝试通过序号匹配
            $tsNumber = null;
            if (preg_match('/(\d+)-(\d+)-(\d+)/', $tsBasename, $matches)) {
                $tsNumber = $matches[1];
                foreach ($segments as $segment) {
                    $segmentBasename = basename($segment['url']);
                    if (preg_match('/(\d+)-(\d+)-(\d+)/', $segmentBasename, $matches2) && 
                        $matches2[1] === $tsNumber) {
                        //$this->logError("【getCurrentSegmentInfo】segment：" . $segment, 'info', __FILE__, __LINE__);
                        return $segment;
                    }
                }
            }
            
        } catch (\Exception $e) {
            $this->logError("获取分片信息失败[0x206]: " . $e->getMessage(), 'warning', __FILE__, __LINE__);
        }
        return null;
    }

    /**
     * 匹配两个TS文件名是否相关
     * 比较两个TS文件名是否指向同一个分片
     * 
     * @param string $filename1 第一个文件名
     * @param string $filename2 第二个文件名
     * @return bool 是否匹配
     */
    private function matchTsFilenames($filename1, $filename2)
    {
        // 移除查询参数
        $filename1 = strtok($filename1, '?');
        $filename2 = strtok($filename2, '?');
        
        // 提取文件名中的数字部分
        if (preg_match('/(\d+)-(\d+)-(\d+)/', $filename1, $matches1) &&
            preg_match('/(\d+)-(\d+)-(\d+)/', $filename2, $matches2)) {
            
            // 完全匹配文件名
            return $filename1 === $filename2;
        }
        
        return false;
    }

    /**
     * 构建源URL
     * 根据基础URL和TS文件名构建完整的源URL
     * 
     * @param string $baseUrl 基础URL
     * @param string $tsFile TS文件名
     * @return string 完整的源URL
     */
    private function buildSourceUrl($baseUrl, $tsFile)
    {
        // 如果tsFile已经是完整的URL，直接返回
        if (filter_var($tsFile, FILTER_VALIDATE_URL)) {
            return $tsFile;
        }
        
        // 确保baseUrl和tsFile之间只有一个斜杠
        $baseUrl = rtrim($baseUrl, '/');
        //$this->logError("【buildSourceUrl】baseUrl：" . $baseUrl, 'info', __FILE__, __LINE__);
        $tsFile = ltrim($tsFile, '/');
        //$this->logError("【buildSourceUrl】tsFile：" . $tsFile, 'info', __FILE__, __LINE__);
        // 组合URL
        return $baseUrl . '/' . $tsFile;
    }
} 