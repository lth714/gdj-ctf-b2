<?php
namespace App\Controllers;

use App\Core\Config;
use App\Models\Channel;
use App\Models\Settings;
use Redis;


class MonitorController
{
    private $channelModel;
    private $settingsModel;
    private $db;
    private $redis;

    public function __construct()
    {
        $this->channelModel = new Channel();
        $this->settingsModel = Settings::getInstance();
        $this->db = $this->channelModel->getConnection();
        
        // 初始化Redis连接
        $settings = $this->settingsModel->get();
        $this->redis = new Redis();
        try {
            $this->redis->connect(
                $settings['redis_host'] ?? '127.0.0.1',
                $settings['redis_port'] ?? 6379
            );
            if (!empty($settings['redis_password'])) {
                $this->redis->auth($settings['redis_password']);
            }
        } catch (\Exception $e) {
            error_log("Redis connection error: " . $e->getMessage());
        }
    }

    public function index()
    {
        $settings = $this->settingsModel->get();
        $refreshInterval = $settings['monitor_refresh_interval'] ?? 5;
        
        // 获取初始数据，避免页面空白
        $initialData = $this->getStats();
        
        require __DIR__ . '/../views/admin/monitor/index.php';
    }

    public function getStats()
    {
        try {
            // 尝试从缓存获取所有统计数据
            $config = Config::getInstance();
            $monitor_cache_stats_key = $config->get('monitor_cache_stats', 'monitor:cache_stats');

            $cacheKey = 'monitor:all_stats';
            $allStats = $this->getFromCache($cacheKey, 10);
            
            if ($allStats !== false) {
                return [
                    'success' => true,
                    'data' => $allStats
                ];
            }
            
            // 如果缓存不存在，重新计算所有统计数据
            
            // 1. 基础统计数据
            $query = "SELECT 
                     COUNT(*) as total_channels,
                     SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_channels,
                     SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_channels,
                     AVG(latency) as avg_latency
                     FROM channels";
            
            $stmt = $this->db->query($query);
            $channelStats = $stmt->fetch(\PDO::FETCH_ASSOC);
            
            // 2. 分组统计信息（使用Redis缓存，缓存时间5分钟）
            $groupStats = $this->getFromCache('monitor:group_stats', 300);
            if ($groupStats === false) {
                $groupStats = $this->channelModel->getGroupStats();
                $this->saveToCache('monitor:group_stats', $groupStats, 300);
            }
            
            // 3. 性能指标（使用Redis缓存，缓存时间1小时）
            $performanceStats = $this->getFromCache('monitor:perf_stats', 3600);
            if ($performanceStats === false) {
                $performanceStats = $this->channelModel->getPerformanceStats();
                $this->saveToCache('monitor:perf_stats', $performanceStats, 3600);
            }
            
            // 4. 最近的错误（实时数据，不缓存）
            $recentErrors = $this->channelModel->getRecentErrors();
            
            // 5. Redis性能数据（缓存10秒）
            $redisStats = $this->getFromCache('monitor:redis_stats', 10);
            if ($redisStats === false) {
                $redisStats = $this->getRedisStats();
                $this->saveToCache('monitor:redis_stats', $redisStats, 10);
            }

            // 6. 内存缓存统计数据（缓存10秒）
            $memoryCacheStats = $this->getFromCache($monitor_cache_stats_key, 10);
            if ($memoryCacheStats === false) {
                $memoryCacheStats = $this->getMemoryCacheStats();
                $this->saveToCache($monitor_cache_stats_key, $memoryCacheStats, 10);
            }
            
            // 组合所有数据
            $allStats = [
                'channelStats' => $channelStats,
                'groupStats' => array_map(function($group) {
                    return [
                        'name' => $group['name'],
                        'value' => (int)$group['total_channels'],
                        'active' => (int)$group['active_channels'],
                        'error' => (int)$group['error_channels'],
                        'avg_latency' => round((float)$group['avg_latency'], 2)
                    ];
                }, $groupStats),
                'performanceStats' => $performanceStats,
                'recentErrors' => $recentErrors,
                'redisStats' => $redisStats,
                'memoryCacheStats' => $memoryCacheStats  // 添加内存缓存统计
            ];
            
            // 缓存组合后的数据（10秒）
            $this->saveToCache($cacheKey, $allStats, 10);
            
            return [
                'success' => true,
                'data' => $allStats
            ];
        } catch (\Exception $e) {
            error_log("Error getting monitor stats: " . $e->getMessage());
            return [
                'success' => false,
                'message' => $e->getMessage()
            ];
        }
    }

    private function getRedisStats()
    {
        try {
            if (!$this->redis) {
                return null;
            }

            $info = $this->redis->info();
            return [
                'version' => $info['redis_version'] ?? '',
                //'used_memory' => $this->formatBytes($info['used_memory'] ?? 0),
                'used_memory' => $info['used_memory'] ?? 0,
                //'used_memory_peak' => $this->formatBytes($info['used_memory_peak'] ?? 0),
                'used_memory_peak' =>$info['used_memory_peak'] ?? 0,
                'connected_clients' => $info['connected_clients'] ?? 0,
                'total_connections_received' => $info['total_connections_received'] ?? 0,
                'total_commands_processed' => $info['total_commands_processed'] ?? 0,
                'keyspace_hits' => $info['keyspace_hits'] ?? 0,
                'keyspace_misses' => $info['keyspace_misses'] ?? 0,
                'uptime_in_seconds' => $info['uptime_in_seconds'] ?? 0,
                'hit_rate' => $this->calculateHitRate(
                    $info['keyspace_hits'] ?? 0,
                    $info['keyspace_misses'] ?? 0
                ),
                'uptime_days' => floor(($info['uptime_in_seconds'] ?? 0) / 86400),
                'total_keys' => $this->getTotalKeys(),
                'expired_keys' => $info['expired_keys'] ?? 0,
                'evicted_keys' => $info['evicted_keys'] ?? 0,
                'connected_slaves' => $info['connected_slaves'] ?? 0,
                'last_save_time' => isset($info['rdb_last_save_time']) ? 
                    date('Y-m-d H:i:s', $info['rdb_last_save_time']) : '-'
            ];
        } catch (\Exception $e) {
            error_log("Error getting Redis stats: " . $e->getMessage());
            return null;
        }
    }

    private function formatBytes($bytes)
    {
        if ($bytes < 1024) {
            return $bytes . ' B';
        }
        $units = ['KB', 'MB', 'GB', 'TB'];
        $exp = floor(log($bytes) / log(1024));
        return sprintf('%.2f %s', $bytes / pow(1024, $exp), $units[$exp - 1]);
    }

    private function calculateHitRate($hits, $misses)
    {
        $total = $hits + $misses;
        if ($total == 0) {
            return '0%';
        }
        return round(($hits / $total) * 100, 2) . '%';
    }

    private function getTotalKeys()
    {
        try {
            $dbs = $this->redis->info('keyspace');
            $total = 0;
            foreach ($dbs as $db => $stats) {
                if (preg_match('/keys=(\d+)/', $stats, $matches)) {
                    $total += (int)$matches[1];
                }
            }
            return $total;
        } catch (\Exception $e) {
            return 0;
        }
    }

    private function getFromCache($key, $ttl)
    {
        try {
            if (!$this->redis) {
                return false;
            }

            $data = $this->redis->get($key);
            if ($data === false) {
                return false;
            }

            return json_decode($data, true);
        } catch (\Exception $e) {
            error_log("Redis get error: " . $e->getMessage());
            return false;
        }
    }

    private function saveToCache($key, $data, $ttl)
    {
        try {
            if (!$this->redis) {
                return false;
            }

            return $this->redis->setex(
                $key,
                $ttl,
                json_encode($data)
            );
        } catch (\Exception $e) {
            error_log("Redis set error: " . $e->getMessage());
            return false;
        }
    }

    public function logs()
    {
        $currentPage = 'error_logs';
        require __DIR__ . '/../views/admin/monitor/logs.php';
    }

    public function getLogs()
    {
        try {
            $page = $_GET['page'] ?? 1;
            $perPage = $_GET['per_page'] ?? 50;
            $type = $_GET['type'] ?? null;
            $startDate = $_GET['start_date'] ?? null;
            $endDate = $_GET['end_date'] ?? null;

            $logs = $this->channelModel->getErrorLogs($page, $perPage, $type, $startDate, $endDate);
            
            return [
                'success' => true,
                'data' => $logs
            ];
        } catch (\Exception $e) {
            return [
                'success' => false,
                'message' => $e->getMessage()
            ];
        }
    }

    public function __destruct()
    {
        // 关闭Redis连接
        if ($this->redis) {
            try {
                $this->redis->close();
            } catch (\Exception $e) {
                error_log("Redis close error: " . $e->getMessage());
            }
        }
    }

    private function getMemoryCacheStats()
    {
        try {
            // 获取缓存实例
            $cache = \App\Core\ChannelContentCache::getInstance();
            
            // 获取缓存状态
            $stats = $cache->getCacheStats();
            
            // 获取配置
            $enabled = $this->settingsModel->get('enable_memory_cache', false);
            $maxSize = $this->settingsModel->get('max_memory_cache_size', 256) * 1024 * 1024; // 转换为字节
            
            return [
                'enabled' => $enabled,
                'ttl' => $this->settingsModel->get('memory_cache_ttl', 30),
                'max_size' => $maxSize,
                'used_memory' => $this->formatBytes($stats['used_memory']),
                'items_count' => $stats['items_count'],
                'hit_rate' => round($stats['hit_rate'], 2) . '%',
                'm3u8_count' => $stats['m3u8_count'],
                'ts_count' => $stats['ts_count'],
                'channel_count' => count($stats['channels'] ?? []),
                // 添加详细的命中统计
                'total_requests' => $stats['total_requests'],
                'total_hits' => $stats['total_hits'],
                'memory_hits' => $stats['memory_hits'],
                'redis_hits' => $stats['redis_hits'],
                'total_misses' => $stats['total_misses'],
                // M3U8 详细统计
                'm3u8_hits' => $stats['m3u8_hits'],
                'm3u8_memory_hits' => $stats['m3u8_memory_hits'],
                'm3u8_redis_hits' => $stats['m3u8_redis_hits'],
                'm3u8_misses' => $stats['m3u8_misses'],
                'm3u8_hit_rate' => round($stats['m3u8_hit_rate'], 2) . '%',
                // TS 详细统计
                'ts_hits' => $stats['ts_hits'],
                'ts_memory_hits' => $stats['ts_memory_hits'],
                'ts_redis_hits' => $stats['ts_redis_hits'],
                'ts_misses' => $stats['ts_misses'],
                'ts_hit_rate' => round($stats['ts_hit_rate'], 2) . '%',
                // 清理统计
                'last_cleanup_time' => $stats['last_cleanup_time'],
                'total_cleanup_count' => $stats['total_cleanup_count'],
                'total_cleaned_items' => $stats['total_cleaned_items'],
                // 缓存配置信息
                'memory_cache_enabled' => $stats['memory_cache_enabled'],
                'redis_cache_enabled' => $stats['redis_cache_enabled'],
                'max_memory_cache_size_mb' => $stats['max_memory_cache_size_mb'],
                'cache_cleanup_interval' => $stats['cache_cleanup_interval'],
                'time_since_last_cleanup' => $stats['time_since_last_cleanup']
            ];
        } catch (\Exception $e) {
            error_log("Error getting memory cache stats: " . $e->getMessage());
            return [
                'enabled' => false,
                'ttl' => 0,
                'max_size' => 0,
                'used_memory' => 0,
                'items_count' => 0,
                'hit_rate' => '0%',
                'm3u8_count' => 0,
                'ts_count' => 0,
                'channel_count' => 0,
                'total_requests' => 0,
                'total_hits' => 0,
                'memory_hits' => 0,
                'redis_hits' => 0,
                'total_misses' => 0,
                'm3u8_hits' => 0,
                'm3u8_memory_hits' => 0,
                'm3u8_redis_hits' => 0,
                'm3u8_misses' => 0,
                'm3u8_hit_rate' => '0%',
                'ts_hits' => 0,
                'ts_memory_hits' => 0,
                'ts_redis_hits' => 0,
                'ts_misses' => 0,
                'ts_hit_rate' => '0%',
                'last_cleanup_time' => 0,
                'total_cleanup_count' => 0,
                'total_cleaned_items' => 0,
                'memory_cache_enabled' => false,
                'redis_cache_enabled' => false,
                'max_memory_cache_size_mb' => 0,
                'cache_cleanup_interval' => 0,
                'time_since_last_cleanup' => 0
            ];
        }
    }
} 