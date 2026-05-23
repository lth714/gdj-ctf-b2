<?php
require __DIR__ . '/../../vendor/autoload.php';

use App\Core\Redis;
use App\Core\Config;
use App\Core\Database;

class BandwidthMonitor
{
    private $redis;
    private $config;
    private $db;
    private $interval = 1; // 1秒更新一次
    private $lastBytes = [];
    
    public function __construct()
    {
        $this->redis = new Redis();
        $this->config = Config::getInstance();
        $this->db = Database::getInstance()->getConnection();
    }
    
    public function start()
    {
        echo "带宽监控服务已启动...\n";
        
        while (true) {
            $this->updateBandwidth();
            sleep($this->interval);
        }
    }
    
    private function updateBandwidth()
    {
        try {
            // 获取所有活跃频道
            $stmt = $this->db->query("SELECT id, proxy_port FROM channels WHERE status = 1");
            $channels = $stmt->fetchAll(\PDO::FETCH_ASSOC);
            
            $totalUpload = 0;
            $totalDownload = 0;
            
            foreach ($channels as $channel) {
                $channelId = $channel['id'];
                $proxyPort = $channel['proxy_port'];
                
                // 获取当前字节数
                $currentBytes = $this->getProxyBytes($proxyPort);
                
                if (!isset($this->lastBytes[$channelId])) {
                    $this->lastBytes[$channelId] = $currentBytes;
                    continue;
                }
                
                // 计算带宽
                $uploadBytes = $currentBytes['upload'] - $this->lastBytes[$channelId]['upload'];
                $downloadBytes = $currentBytes['download'] - $this->lastBytes[$channelId]['download'];
                
                // 转换为 MB/s
                $upload = round($uploadBytes / (1024 * 1024) / $this->interval, 2);
                $download = round($downloadBytes / (1024 * 1024) / $this->interval, 2);
                
                // 更新总带宽
                $totalUpload += $upload;
                $totalDownload += $download;
                
                // 更新Redis中的带宽数据
                $this->redis->hMSet("channel:{$channelId}:bandwidth", [
                    'upload' => $upload,
                    'download' => $download,
                    'timestamp' => time()
                ]);
                
                // 保存当前字节数
                $this->lastBytes[$channelId] = $currentBytes;
                
                echo "频道 {$channelId} - 上传: {$upload} MB/s, 下载: {$download} MB/s\n";
            }
            
            // 更新总带宽
            $this->redis->hMSet("bandwidth:total", [
                'upload' => $totalUpload,
                'download' => $totalDownload,
                'timestamp' => time()
            ]);
            
            echo "总带宽 - 上传: {$totalUpload} MB/s, 下载: {$totalDownload} MB/s\n";
            
        } catch (\Exception $e) {
            echo "Error: " . $e->getMessage() . "\n";
        }
    }
    
    private function getProxyBytes($port)
    {
        // 获取代理服务器的字节统计
        // 这里需要根据您的代理服务器实现来获取数据
        // 例如：从代理服务器的日志或状态接口获取
        
        // 示例：从代理服务器获取数据
        $stats = $this->getProxyStats($port);
        
        return [
            'upload' => $stats['bytes_sent'] ?? 0,     // 发送到客户端的字节数
            'download' => $stats['bytes_received'] ?? 0 // 从源服务器接收的字节数
        ];
    }
    
    private function getProxyStats($port)
    {
        // 从Redis获取代理服务器统计数据
        $stats = $this->redis->hGetAll("proxy:stats:{$port}");
        
        if (empty($stats)) {
            return [
                'bytes_sent' => 0,
                'bytes_received' => 0
            ];
        }
        
        return [
            'bytes_sent' => intval($stats['bytes_sent']),
            'bytes_received' => intval($stats['bytes_received'])
        ];
    }
}

// 启动监控
$monitor = new BandwidthMonitor();
$monitor->start(); 