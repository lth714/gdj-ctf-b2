<?php
namespace App\Core;
use App\Models\ErrorLog;

class ChannelContentCache
{
    // 存储M3U8内容的缓存
    private static $m3u8Cache = [];
    // 存储TS文件的缓存
    private static $tsCache = [];
    // 存储M3U8分段信息
    private static $m3u8SegmentInfo = [];
    // 存储频道播放进度
    private static $channelProgress = [];
    // Redis实例
    private $redis;
    // 异步加载器实例
    private static $asyncLoader = null;
    // 单例实例
    private static $instance = null;
    // Logger实例
    private $logger;
    // 错误日志实例
    private $errorLog;

    private $enableMemoryCache;    // 是否启用内存缓存
    private $enableRedisCache;     // 是否启用Redis缓存
    private $maxMemoryCacheSize;   // 最大内存缓存大小(字节)
    private $cacheCleanupInterval; // 缓存清理时间(秒)
    private $lastCleanupTime;      // 上次清理时间
    
    private function __construct()
    {
        $this->redis = new Redis();
        $this->logger = new \App\Core\Logger();
        $this->errorLog = new ErrorLog();

        // 读取缓存配置
        $config = Config::getInstance();
        $this->enableMemoryCache = $config->get('enable_memory_cache', true);
        $this->enableRedisCache = $config->get('enable_redis_cache', true);
        // 将MB转换为字节
        $this->maxMemoryCacheSize = $config->get('max_memory_cache_size', 256) * 1024 * 1024;
        $this->cacheCleanupInterval = $config->get('cache_cleanup_interval', 30); // 默认30秒
        $this->lastCleanupTime = time();
        
        // 初始化缓存大小限制
        if (!isset(self::$tsCache)) {
            self::$tsCache = [];
        }
        
        // 初始化统计信息
        $this->resetCacheStats();

    }
    
    public static function getInstance()
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    /**
     * 解析并缓存M3U8内容
     * @param string $channelId 频道ID
     * @param string $content M3U8内容
     * @param string $baseUrl 基础URL
     * @return array 解析结果
     */
    public function parseAndCacheM3u8($channelId, $content, $baseUrl)
    {
        // 减少不必要的正则表达式操作
        $lines = explode("\n", $content);
        $segments = [];
        $duration = 0;
        $index = 0;
        
        //$this->errorLog("【parseAndCacheM3u8】开始异步处理分片信息", 'info', __FILE__, __LINE__);
        foreach ($lines as $line) {
            $line = trim($line);
            if (empty($line)) continue;
            
            if (strpos($line, '#EXTINF:') === 0) {
                $duration = (float)substr($line, 8);
            } else if (strpos($line, '#') !== 0) {
                $url = $line;
                if (!filter_var($url, FILTER_VALIDATE_URL)) {
                    $url = rtrim($baseUrl, '/') . '/' . ltrim($line, '/');
                }
                
                $segments[] = [
                    'index' => $index++,
                    'url' => $url,
                    'cache_url' => $this->getUrlWithoutParams($url),
                    'duration' => $duration,
                    'loaded' => false
                ];
                $duration = 0;
            }
        }
        //$this->errorLog("【parseAndCacheM3u8】分片信息解析完成", 'info', __FILE__, __LINE__);
        if (!empty($segments)) {
            //$this->errorLog("【parseAndCacheM3u8】分片信息不为空", 'info', __FILE__, __LINE__);
            $this->updateChannelSegments($channelId, $segments);
            //$this->triggerAsyncLoad($channelId);
        }
        
    }
    
    private function getUrlWithoutParams($url)
    {
        $parsedUrl = parse_url($url);
        $cleanUrl = $parsedUrl['scheme'] . '://' . $parsedUrl['host'];
        if (isset($parsedUrl['port'])) {
            $cleanUrl .= ':' . $parsedUrl['port'];
        }
        if (isset($parsedUrl['path'])) {
            $cleanUrl .= $parsedUrl['path'];
        }
        return $cleanUrl;
    }

    /**
     * 获取下一个需要预加载的分片信息
     * @param string $channelId
     * @return array|null
     */
    public function getNextSegmentToLoad($channelId)
    {
        if (!isset(self::$m3u8SegmentInfo[$channelId])) {
            return null;
        }
        
        $segments = self::$m3u8SegmentInfo[$channelId]['segments'];
        foreach ($segments as $segment) {
            if (!$segment['loaded']) {
                return $segment;
            }
        }
        
        return null;
    }

    /**
     * 标记分片已加载
     * @param string $channelId
     * @param string $url
     * @param int $index
     */
    public function markSegmentLoaded($channelId, $url, $index)
    {
        if (isset(self::$m3u8SegmentInfo[$channelId])) {
            self::$m3u8SegmentInfo[$channelId]['segments'][$index]['loaded'] = true;
            
            // 更新Redis缓存
            $this->redis->setex(
                "m3u8:segments:{$channelId}", 
                30,
                json_encode(self::$m3u8SegmentInfo[$channelId])
            );
        }
    }

    /**
     * 缓存TS文件内容
     * @param string $channelId 频道ID
     * @param string $url TS文件URL
     * @param string $content 文件内容
     */
    public function cacheTs($channelId, $url, $content)
    {
        try {
            //$this->errorLog("【cacheTs】开始处理", 'warning', __FILE__, __LINE__);
            // 读取缓存配置
            $config = Config::getInstance();
            $memoryCacheTTL = $config->get('memory_cache_ttl', 30);
            $redisCacheTTL = $config->get('redis_cache_ttl', 300);
            // 检查缓存清理
            $this->checkCacheCleanup();
            // 使用与预加载相同的缓存键生成逻辑
            $parsedUrl = parse_url($url);
            if ($parsedUrl === false || !isset($parsedUrl['path'])) {
                $this->errorLog("URL解析失败: {$url}", 'error', __FILE__, __LINE__);
                return;
            }
            
            // 处理路径，移除代理相关部分
            $path = $parsedUrl['path'];
            $baseUrl = str_replace('/proxy/', '/', $path);
            $baseUrl = preg_replace('/\/ch_[^\/]+\//', '/', $baseUrl);
            $cacheKey = "ts:{$channelId}:" . md5($baseUrl);
            //$this->errorLog("【cacheTs】生成缓存键 - 频道ID: {$channel['id']}, 缓存键: {$cacheKey},baseUrl:{$baseUrl}", 'info', __FILE__, __LINE__);
            // 内存缓存处理
            if ($this->enableMemoryCache) {
                // 检查内存限制
                $this->checkMemoryCacheSize();
                
                self::$tsCache[$cacheKey] = [
                    'content' => $content,
                    'time' => time(),
                    'size' => strlen($content)
                ];
                // 更新缓存统计
                $this->updateCacheStats('ts_memory_hit');
                $this->updateCacheStats('used_memory',strlen($content));
            }

            // Redis缓存处理
            if ($this->enableRedisCache) {
                $this->redis->setex($cacheKey, $redisCacheTTL, $content); // 设置过期时间及缓存
                // 更新缓存统计
                $this->updateCacheStats('ts_redis_hit');
            }
            $this->updateCacheStats('ts_count');
            
        } catch (\Exception $e) {
            $this->errorLog("cacheTs缓存TS文件失败[0x006]: " . $e->getMessage(), 'error', "ChannelContentCache.php", __LINE__);
        }
    }

    /**
     * 获取缓存的TS文件
     * @param string $channelId 频道ID
     * @param string $url TS文件URL
     * @return string|null
     */
    public function getTs($channelId, $url)
    {
        //$this->errorLog("【getTs】开始处理", 'info', __FILE__, __LINE__);
        $startTime = microtime(true);
        // 添加缓存清理检查
        $this->checkCacheCleanup();
        
        // 使用与预加载相同的缓存键生成逻辑
        $parsedUrl = parse_url($url);
        if ($parsedUrl === false || !isset($parsedUrl['path'])) {
            //$this->errorLog("URL解析失败: {$url}", 'error', __FILE__, __LINE__);
            return null;
        }
        
        // 处理路径，移除代理相关部分
        $path = $parsedUrl['path'];
        $baseUrl = str_replace('/proxy/', '/', $path);
        $baseUrl = preg_replace('/\/ch_[^\/]+\//', '/', $baseUrl);
        $cacheKey = "ts:{$channelId}:" . md5($baseUrl);
        //$this->errorLog("【getTs】生成缓存键 - 频道ID: {$channelId}, 缓存键: {$cacheKey},baseUrl:{$baseUrl}", 'info', __FILE__, __LINE__);
        // 优先检查内存缓存
        if ($this->enableMemoryCache && isset(self::$tsCache[$cacheKey])) {
            $this->updateCacheStats('memory_hit');
            $this->updateCacheStats('ts_memory_hit');
            /*
            $this->errorLog(
                sprintf("[getTs日志] 内存缓存命中，耗时: %.3f秒", microtime(true) - $startTime . "cacheKey:{$cacheKey},baseUrl:{$baseUrl}"),
                'info',
                __FILE__,
                __LINE__
            );*/
            return self::$tsCache[$cacheKey]['content'];
        }
        
        // 检查Redis缓存
        if ($this->enableRedisCache) {
            $content = $this->redis->get($cacheKey);
            if ($content !== false) {
                $this->updateCacheStats('redis_hit');
                $this->updateCacheStats('ts_redis_hit');
                // 如果内存缓存开启，同步到内存缓存
                if ($this->enableMemoryCache) {
                    $this->checkMemoryCacheSize(); // 检查内存限制
                    self::$tsCache[$cacheKey] = [
                        'content' => $content,
                        'time' => time(),
                        'size' => strlen($content)
                    ];
                    $this->updateCacheStats('ts_memory_hit');
                }
                
                $this->errorLog(
                    sprintf("[性能日志] Redis缓存命中，耗时: %.3f秒", microtime(true) - $startTime),
                    'info',
                    __FILE__,
                    __LINE__
                );
                return $content;
            }
        }
        
        // 缓存未命中
        $this->updateCacheStats('miss');
        return null;
    }

    /**
     * 检查是否需要预加载下一个M3U8
     * @param string $channelId
     * @return bool
     */
    public function shouldPreloadNextM3u8($channelId)
    {
        if (!isset(self::$m3u8SegmentInfo[$channelId])) {
            return false;
        }
        
        $info = self::$m3u8SegmentInfo[$channelId];
        $segments = $info['segments'];
        $loadedCount = count(array_filter($segments, function($seg) {
            return $seg['loaded'];
        }));
        
        return ($loadedCount / count($segments)) > 0.8;
    }

    /**
     * 初始化异步加载器
     */
    private function initAsyncLoader()
    {
        if (self::$asyncLoader === null) {
            self::$asyncLoader = new AsyncLoader();
        }
    }

    /**
     * 构建绝对URL
     * @param string $baseUrl
     * @param string $path
     * @return string
     */
    private function buildAbsoluteUrl($baseUrl, $path)
    {
        if (filter_var($path, FILTER_VALIDATE_URL)) {
            return $path;
        }
        return rtrim($baseUrl, '/') . '/' . ltrim($path, '/');
    }

    /**
     * 检查并控制缓存大小
     */
    private function checkCacheSize()
    {
        $config = Config::getInstance();
        $max_memory_cache_size = $config->get('max_memory_cache_size', 256);
        $maxCacheSize = $max_memory_cache_size * 1024 * 1024; 
        $totalSize = 0;
        
        foreach (self::$tsCache as $cache) {
            $totalSize += $cache['size'];
        }
        
        if ($totalSize > $maxCacheSize) {
            uasort(self::$tsCache, function($a, $b) {
                return $a['time'] - $b['time'];
            });
            
            foreach (self::$tsCache as $key => $cache) {
                unset(self::$tsCache[$key]);
                $totalSize -= $cache['size'];
                if ($totalSize <= $maxCacheSize) {
                    break;
                }
            }
        }
    }

    /**
     * 清理指定频道的TS缓存
     * @param string $channelId
     */
    public function cleanChannelTsCache($channelId)
    {
        $pattern = "ts:{$channelId}:*";
        $keys = $this->redis->keys($pattern);
        
        // 清理Redis缓存
        foreach ($keys as $key) {
            $this->redis->del($key);
        }
        
        // 清理内存缓存
        foreach (self::$tsCache as $key => $value) {
            if (strpos($key, "ts:{$channelId}:") === 0) {
                unset(self::$tsCache[$key]);
            }
        }
        
        // 清理分段信息
        unset(self::$m3u8SegmentInfo[$channelId]);
    }

    /**
     * 获取缓存状态
     * @return array
     */
    public function getCacheStatus()
    {
        try {
            //$this->errorLog("【getCacheStatus】开始处理", 'info', __FILE__, __LINE__);
            // Redis key
            $config = Config::getInstance();
            $key = $config->get('monitor_cache_stats', 'monitor:cache_stats');
            //$key = $monitor_cache_stats;
            
            // 从 Redis 读取统计数据
            $stats = [
                'm3u8_count' => intval($this->redis->hGet($key, 'm3u8_count')),
                'ts_count' => intval($this->redis->hGet($key, 'ts_count')),
                //'total_size' => array_sum(array_column(self::$tsCache, 'size')),
                //'channels' => array_keys(self::$m3u8SegmentInfo),

                'total_requests' => intval($this->redis->hGet($key, 'total_requests')),
                'total_hits' => intval($this->redis->hGet($key, 'total_hits')),
                'memory_hits' => intval($this->redis->hGet($key, 'memory_hits')),
                'redis_hits' => intval($this->redis->hGet($key, 'redis_hits')),
                'total_misses' => intval($this->redis->hGet($key, 'total_misses')),
                'm3u8_requests' => intval($this->redis->hGet($key, 'm3u8_requests')),
                'm3u8_hits' => intval($this->redis->hGet($key, 'm3u8_hits')),
                'm3u8_memory_hits' => intval($this->redis->hGet($key, 'm3u8_memory_hits')),
                'm3u8_redis_hits' => intval($this->redis->hGet($key, 'm3u8_redis_hits')),
                'm3u8_misses' => intval($this->redis->hGet($key, 'm3u8_misses')),
                'ts_requests' => intval($this->redis->hGet($key, 'ts_requests')),
                'ts_hits' => intval($this->redis->hGet($key, 'ts_hits')),
                'ts_memory_hits' => intval($this->redis->hGet($key, 'ts_memory_hits')),
                'ts_redis_hits' => intval($this->redis->hGet($key, 'ts_redis_hits')),
                'ts_misses' => intval($this->redis->hGet($key, 'ts_misses'))
            ];
            
            // 计算命中率
            $hitRate = $stats['total_requests'] > 0 
                ? round(($stats['total_hits'] / $stats['total_requests']) * 100, 2) . '%'
                : '0%';
                
            // 返回格式化的状态信息
            return [
                'm3u8_count' => count(self::$m3u8SegmentInfo),
                'ts_count' => count(self::$tsCache),
                'total_size' => array_sum(array_column(self::$tsCache, 'size')),
                'channels' => array_keys(self::$m3u8SegmentInfo),
                // 添加缓存统计信息
                'cache_stats' => [
                    'total_requests' => $stats['total_requests'],
                    'total_hits' => $stats['total_hits'],
                    'memory_hits' => $stats['memory_hits'],
                    'redis_hits' => $stats['redis_hits'],
                    'total_misses' => $stats['total_misses'],
                    'hit_rate' => $hitRate,
                    'm3u8' => [
                        'requests' => $stats['m3u8_requests'],
                        'hits' => $stats['m3u8_hits'],
                        'memory_hits' => $stats['m3u8_memory_hits'],
                        'redis_hits' => $stats['m3u8_redis_hits'],
                        'misses' => $stats['m3u8_misses']
                    ],
                    'ts' => [
                        'requests' => $stats['ts_requests'],
                        'hits' => $stats['ts_hits'],
                        'memory_hits' => $stats['ts_memory_hits'],
                        'redis_hits' => $stats['ts_redis_hits'],
                        'misses' => $stats['ts_misses']
                    ]
                ]
            ];
        } catch (\Exception $e) {
            //$this->errorLog("获取缓存状态失败: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            return [
                'm3u8_count' => 0,
                'ts_count' => 0,
                'total_size' => 0,
                'channels' => [],
                'cache_stats' => [
                    'total_requests' => 0,
                    'total_hits' => 0,
                    'memory_hits' => 0,
                    'redis_hits' => 0,
                    'total_misses' => 0,
                    'hit_rate' => '0%',
                    'm3u8' => [
                        'requests' => 0,
                        'hits' => 0,
                        'memory_hits' => 0,
                        'redis_hits' => 0,
                        'misses' => 0
                    ],
                    'ts' => [
                        'requests' => 0,
                        'hits' => 0,
                        'memory_hits' => 0,
                        'redis_hits' => 0,
                        'misses' => 0
                    ]
                ]
            ];
        }
    }

    /**
     * 获取或设置M3U8缓存
     * @param string $channelId
     * @param string|array $content
     * @return string|null
     */
    public function m3u8Cache($channelId, $content = null)
    {
        try {
            //$this->errorLog("【m3u8Cache】开始处理 - 频道ID: {$channelId}", 'info', __FILE__, __LINE__);
            
            // 读取缓存配置
            $config = Config::getInstance();
            $memoryCacheTTL = $config->get('memory_cache_ttl', 30);
            $redisCacheTTL = $config->get('redis_cache_ttl', 300);
            
            if ($content !== null) {
                // 设置缓存
                //$this->errorLog("【m3u8Cache】准备设置缓存", 'info', __FILE__, __LINE__);
                
                $cacheContent = is_array($content) ? $content['content'] : $content;
                
                // 保存到内存缓存
                if ($this->enableMemoryCache) {
                    //$this->errorLog("【m3u8Cache】正在写入内存缓存", 'info', __FILE__, __LINE__);
                    self::$m3u8Cache[$channelId] = [
                        'content' => $cacheContent,
                        'time' => time()
                    ];
                    // 更新缓存统计
                    //$this->errorLog("【m3u8Cache】内存缓存写入完成,准备更新统计", 'info', __FILE__, __LINE__);
                    $this->updateCacheStats('m3u8_memory_hit');
                    $this->updateCacheStats('used_memory', strlen($cacheContent));
                    //$this->errorLog("【m3u8Cache】内存缓存写入完成,统计更新完成", 'info', __FILE__, __LINE__);
                }
                
                // 同时保存到 Redis
                if ($this->enableRedisCache) {
                    //$this->errorLog("【m3u8Cache】正在写入Redis缓存", 'info', __FILE__, __LINE__);
                    $key = "m3u8:content:{$channelId}";
                    $this->redis->setex($key, $redisCacheTTL, json_encode([
                        'content' => $cacheContent,
                        'time' => time()
                    ]));
                    // 更新缓存统计
                    $this->updateCacheStats('m3u8_redis_hit');
                    //$this->errorLog("【m3u8Cache】Redis缓存写入完成", 'info', __FILE__, __LINE__);
                }
                
                $this->updateCacheStats('m3u8_count');
                //$this->errorLog("【m3u8Cache】缓存设置完成", 'info', __FILE__, __LINE__);
                return $cacheContent;
            }
            
            // 获取缓存
            //$this->errorLog("【m3u8Cache】准备获取缓存", 'info', __FILE__, __LINE__);
            
            // 检查内存缓存
            if ($this->enableMemoryCache && isset(self::$m3u8Cache[$channelId])) {
                //$this->errorLog("【m3u8Cache】检查内存缓存", 'info', __FILE__, __LINE__);
                // 检查缓存是否过期
                if (time() - self::$m3u8Cache[$channelId]['time'] < $memoryCacheTTL) {
                    // 更新缓存统计
                    $this->updateCacheStats('m3u8_memory_hit');
                    //$this->errorLog("【m3u8Cache】内存缓存命中,channelId:{$channelId}", 'info', __FILE__, __LINE__);
                    return self::$m3u8Cache[$channelId]['content'];
                }
                //$this->errorLog("【m3u8Cache】内存缓存已过期", 'info', __FILE__, __LINE__);
                unset(self::$m3u8Cache[$channelId]);
            }
            
            // 尝试从Redis获取
            if ($this->enableRedisCache) {
                //$this->errorLog("【m3u8Cache】尝试从Redis获取", 'info', __FILE__, __LINE__);
                $key = "m3u8:content:{$channelId}";
                $cached = $this->redis->get($key);
                if ($cached) {
                    // 更新缓存统计
                    $this->updateCacheStats('m3u8_redis_hit');
                    // 更新内存缓存
                    $this->updateCacheStats('m3u8_memory_hit');
                    $cachedData = json_decode($cached, true);
                    if ($cachedData === null) {
                        //$this->errorLog("【m3u8Cache】Redis缓存数据解析失败", 'error', __FILE__, __LINE__);
                        return null;
                    }
                    self::$m3u8Cache[$channelId] = $cachedData;
                    //$this->errorLog("【m3u8Cache】命中Redis缓存", 'info', __FILE__, __LINE__);
                    return $cachedData['content'];
                }
                //$this->errorLog("【m3u8Cache】Redis缓存未命中", 'info', __FILE__, __LINE__);
            }
            
            //$this->errorLog("【m3u8Cache】未找到缓存", 'info', __FILE__, __LINE__);
            return null;
            
        } catch (\Exception $e) {
            $this->errorLog("【m3u8Cache】处理异常: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            return null;
        }
    }

    /**
     * 预加载下一个分片
     * @param string $channelId 频道ID
     * @param array $currentSegment 当前分片信息
     * @return bool 是否成功触发预加载
     */
    public function preloadNextSegment($channelId, $currentSegment)
    {
        try {
            //$this->errorLog("【preloadNextSegment】开始处理 - 频道ID: {$channelId}", 'info', __FILE__, __LINE__);
            // 1. 检查频道信息
            if (!isset(self::$m3u8SegmentInfo[$channelId])) {
                return false;
            }

            // 2. 获取下一个分片
            $segments = self::$m3u8SegmentInfo[$channelId]['segments'];
            $currentIndex = $currentSegment['index'];
            $nextIndex = $currentIndex + 1;
            
            if (!isset($segments[$nextIndex])) {
                return false;
            }

            $nextSegment = $segments[$nextIndex];

            // 3. 生成缓存键
            $parsedUrl = parse_url($nextSegment['url']);
            if ($parsedUrl === false || !isset($parsedUrl['path'])) {
                return false;
            }
            
            $path = $parsedUrl['path'];
            $baseUrl = str_replace('/proxy/', '/', $path);
            $baseUrl = preg_replace('/\/ch_[^\/]+\//', '/', $baseUrl);
            $cacheKey = "ts:{$channelId}:" . md5($baseUrl);

            // 4. 检查缓存
            if ($this->redis->exists($cacheKey)) {
                return true;
            }

            // 5. 初始化异步加载器（提前初始化），会造成无日志输出的BUG
            /*
            if (self::$asyncLoader === null) {
                $initStart = microtime(true);
                try {
                    self::$asyncLoader = new AsyncLoader();
                    $this->errorLog("[预加载日志] 初始化异步加载器，耗时: " . round((microtime(true) - $initStart) * 1000, 2) . "ms", 'info', __FILE__, __LINE__);
                } catch (\Exception $e) {
                    $this->errorLog("[预加载日志] 初始化异步加载器失败: " . $e->getMessage(), 'error', __FILE__, __LINE__);
                    return false;
                }
            }
            */
            // 6. 添加异步任务
            if (self::$asyncLoader) {
                try {
                    // 设置任务超时和重试策略
                    $taskOptions = [
                        'timeout' => 3,
                        'retry' => 1,
                        'priority' => 'low'
                    ];
                    
                    self::$asyncLoader->addTask(
                        $channelId,
                        $nextSegment['url'],
                        'ts',
                        'low',
                        ['index' => $nextIndex],
                        3,
                        $taskOptions
                    );
                    return true;
                } catch (\Exception $e) {
                    $this->errorLog("[预加载日志] 添加异步任务失败: " . $e->getMessage(), 'error', __FILE__, __LINE__);
                    return false;
                }
            }

            return false;
        } catch (\Exception $e) {
            $this->errorLog("预加载处理失败[0x313]: " . $e->getMessage(), 'error', __FILE__, __LINE__);
            return false;
        }
    }

    /**
     * 下载分片内容
     * @param string $url
     * @return string|false
     */
    private function downloadSegment($url)
    {
        //$this->errorLog("【downloadSegment】开始处理 - 频道ID: {$channelId}", 'info', __FILE__, __LINE__);
        $config = Config::getInstance();
        $context = stream_context_create([
            'http' => [
                'timeout' => $config->get('proxy_timeout', 1),
                'user_agent' => 'VLC/3.0.20 LibVLC/3.0.20'
            ],
            'ssl' => [
                'verify_peer' => false,
                'verify_peer_name' => false
            ]
        ]);
        
        return @file_get_contents($url, false, $context);
    }

    /**
     * 预加载下一个M3U8文件
     * @param string $channelId 频道ID
     * @return bool 是否成功触发预加载
     */
    public function preloadNextM3u8($channelId)
    {
        //$this->errorLog("【preloadNextM3u8】开始处理 - 频道ID: {$channelId}", 'info', __FILE__, __LINE__);
        try {
            if (!isset(self::$m3u8SegmentInfo[$channelId])) {
                return false;
            }

            $info = self::$m3u8SegmentInfo[$channelId];
            $segments = $info['segments'];
            
            // 计算已加载的分片比例
            $loadedCount = count(array_filter($segments, function($seg) {
                return $seg['loaded'];
            }));
            
            $loadedRatio = $loadedCount / count($segments);
            
            // 如果已加载超过80%的分片，触发下一个M3U8的预加载
            if ($loadedRatio > 0.8) {
                $this->initAsyncLoader();
                self::$asyncLoader->addTask(
                    $channelId,
                    $info['source_url'],
                    'm3u8',
                    'low',  // 使用低优先级
                    ['sequence' => $info['sequence'] + 1]
                );
                //$this->errorLog("触发下一个M3U8预加载: Channel {" . $channelId . "}" , 'info', __FILE__, __LINE__);
                //$this->logger->info("触发下一个M3U8预加载: Channel {$channelId}", __FILE__, __LINE__);
                return true;
            }

            return false;
        } catch (\Exception $e) {
            $this->logger->error("预加载M3U8失败: " . $e->getMessage(), __FILE__, __LINE__);
            return false;
        }
    }

    /**
     * 更新播放进度并触发预加载
     * @param string $channelId 频道ID
     * @param int $segmentIndex 当前播放的分片索引
     */
    public function updatePlaybackProgress($channelId, $segmentIndex)
    {
        try {
            if (!isset(self::$channelProgress[$channelId])) {
                self::$channelProgress[$channelId] = [];
            }

            self::$channelProgress[$channelId] = [
                'current_segment' => $segmentIndex,
                'update_time' => time()
            ];

            // 获取当前分片信息
            if (isset(self::$m3u8SegmentInfo[$channelId]['segments'][$segmentIndex])) {
                $currentSegment = self::$m3u8SegmentInfo[$channelId]['segments'][$segmentIndex];
                $this->preloadNextSegment($channelId, $currentSegment);
            }
        } catch (\Exception $e) {
            $this->logger->error("更新播放进度失败: " . $e->getMessage(), __FILE__, __LINE__);
        }
    }

    /**
     * 重置缓存统计信息
     */
    public function resetCacheStats()
    {
        try {
            $config = Config::getInstance();
            $key = $config->get('monitor_cache_stats', 'monitor:cache_stats');

            $stats = [
                    'enabled' => $config->get('enable_memory_cache', 1),
                    'ttl' => $config->get('memory_cache_ttl', 30),
                    'max_size' => $config->get('max_memory_cache_size', 256) * 1024 * 1024,
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
                // 新增统计项
                'm3u8_requests' => 0,
                'm3u8_hits' => 0,
                'm3u8_memory_hits' => 0,
                'm3u8_redis_hits' => 0,
                'm3u8_misses' => 0,
                'ts_requests' => 0,
                'ts_hits' => 0,
                'ts_memory_hits' => 0,
                'ts_redis_hits' => 0,
                'ts_misses' => 0,
                'last_cleanup_time' => 0,
                'total_cleanup_count' => 0,
                'total_cleaned_items' => 0
            ];
            
            $this->redis->hMSet($key, $stats);
            $this->redis->expire($key, 86400); // 24小时过期
            
        } catch (\Exception $e) {
            $this->logger->error("重置缓存统计失败: " . $e->getMessage());
        }
    }

    /**
    * 更新缓存统计信息
    * @param string $type 统计类型 ('hit', 'miss', 'memory_hit', 'redis_hit')
    */
    private function updateCacheStats($type,$value=0)
    {
        try {
            //$this->errorLog("【updateCacheStats】开始处理 - 统计类型: {$type}", 'info', __FILE__, __LINE__);
            //这里的注释先保留，后续需要修改
            //$key = 'cache:stats';
            $config = Config::getInstance();
            $key = $config->get('monitor_cache_stats', 'monitor:cache_stats');
            //$key = 'monitor:cache_stats';
            $stats = json_decode($this->redis->get($key), true);
            //$this->errorLog("【缓存统计信息】保存前: " . json_encode($stats), 'error', __FILE__, __LINE__);
            if (empty($stats)) {
                //$this->resetCacheStats();
                $stats = [
                    'enabled' => $config->get('enable_memory_cache', 1),
                    'ttl' => $config->get('memory_cache_ttl', 30),
                    'max_size' => $config->get('max_memory_cache_size', 256) * 1024 * 1024,
                    'used_memory' => 0,
                    'items_count' => 0,
                    'hit_rate' => '0%',
                    'm3u8_count' => 0,
                    'ts_count' => 0,
                    'channel_count' => 0,

                    'total_requests' => 0,    // 总请求次数（M3U8和TS的总和）
                    'total_hits' => 0,        // 总命中次数（内存缓存+Redis缓存命中）
                    'memory_hits' => 0,       // 内存缓存命中次数
                    'redis_hits' => 0,        // Redis缓存命中次数
                    'total_misses' => 0,      // 总未命中次数（需要从源站获取）
                    // 新增统计项
                    'm3u8_requests' => 0,     // M3U8文件请求总次数
                    'm3u8_hits' => 0,         // M3U8文件缓存命中总次数
                    'm3u8_memory_hits' => 0,  // M3U8文件内存缓存命中次数
                    'm3u8_redis_hits' => 0,   // M3U8文件Redis缓存命中次数
                    'm3u8_misses' => 0,       // M3U8文件缓存未命中次数
                    'ts_requests' => 0,       // TS文件请求总次数
                    'ts_hits' => 0,          // TS文件缓存命中总次数
                    'ts_memory_hits' => 0,   // TS文件内存缓存命中次数
                    'ts_redis_hits' => 0,    // TS文件Redis缓存命中次数
                    'ts_misses' => 0,        // TS文件缓存未命中次数
                    'last_cleanup_time' => 0,      // 最后一次缓存清理的时间戳
                    'total_cleanup_count' => 0,    // 执行缓存清理的总次数
                    'total_cleaned_items' => 0,    // 被清理的缓存项目总数
                ];
                
            }
            
            // 将所有值转换为整数
            $stats = array_map('intval', $stats);
            
            // 更新基础统计
            $stats['total_requests']++;
            $stats['max_size'] = $config->get('max_memory_cache_size', 256) * 1024 * 1024;
            //$this->errorLog("【max_size】: " .$stats['max_size'], 'info', __FILE__, __LINE__);
            // 根据类型更新详细统计
            switch ($type) {
                case 'hit':
                    $stats['total_hits']++;
                    break;
                case 'miss':
                    $stats['total_misses']++;
                    break;
                case 'memory_hit':
                    $stats['memory_hits']++;
                    $stats['total_hits']++;
                    break;
                case 'redis_hit':
                    $stats['redis_hits']++;
                    $stats['total_hits']++;
                    break;
                case 'used_memory':
                    $stats['used_memory'] += $value;
                    break;
                case 'm3u8_memory_hit':
                    $stats['m3u8_memory_hits']++;
                    $stats['m3u8_hits']++;
                    $stats['m3u8_requests']++;
                    break;
                case 'm3u8_redis_hit':
                    $stats['m3u8_redis_hits']++;
                    $stats['m3u8_hits']++;
                    $stats['m3u8_requests']++;
                    break;
                case 'm3u8_miss':
                    $stats['m3u8_misses']++;
                    $stats['m3u8_requests']++;
                    break;
                case 'm3u8_count':
                    $stats['m3u8_count']++;
                    $stats['items_count']++;
                    break;
                case 'ts_memory_hit':
                    $stats['ts_memory_hits']++;
                    $stats['ts_hits']++;
                    $stats['ts_requests']++;
                    break;
                case 'ts_redis_hit':
                    $stats['ts_redis_hits']++;
                    $stats['ts_hits']++;
                    $stats['ts_requests']++;
                    break;
                case 'ts_miss':
                    $stats['ts_misses']++;
                    $stats['ts_requests']++;
                    break;
                case 'ts_count':
                    $stats['ts_count']++;
                    $stats['items_count']++;
                    break;
            }
            
            // 保存更新后的统计信息 
            //foreach ($stats as $field => $value) {
                //$this->redis->hIncrBy($key, $field, $value - intval($this->redis->hGet($key, $field)));
            //}
            
            $this->redis->setex($key, 86400, json_encode($stats));
            
            // 设置过期时间（24小时）
            //$this->redis->expire($key, 86400);
            // 读取并打印缓存内容
            $cachedStats = [];
            foreach ($stats as $field => $value) {
                $cachedStats[$field] = $this->redis->hGet($key, $field);
            }
            //$this->errorLog("【缓存统计信息】保存后: " . json_encode($cachedStats), 'error', __FILE__, __LINE__);
        } catch (\Exception $e) {
            $this->logger->error("更新缓存统计失败: " . $e->getMessage());
        }
    }

    /**
    * 获取缓存统计信息
    * @return array
    */
    public function getCacheStats()
    {
        //$this->errorLog("【getCacheStats】开始处理", 'info', __FILE__, __LINE__);
        try {
            $config = Config::getInstance();
            $key = $config->get('monitor_cache_stats', 'monitor:cache_stats');
            //$key = 'monitor:cache_stats';
            // 从 Redis 获取所有统计数据，如果不存在则使用默认值
            $stats = $this->redis->hGetAll($key) ?: [
                    'enabled' => $config->get('enable_memory_cache', 1),
                    'ttl' => $config->get('memory_cache_ttl', 30),
                    'max_size' => $config->get('max_memory_cache_size', 256) * 1024 * 1024,
                    'used_memory' => 0,
                    'items_count' => 0,
                    'hit_rate' => '0%',
                    'm3u8_count' => 0,
                    'ts_count' => 0,
                    'channel_count' => 0,

                    'total_requests' => 0,    // 总请求次数（M3U8和TS的总和）
                    'total_hits' => 0,        // 总命中次数（内存缓存+Redis缓存命中）
                    'memory_hits' => 0,       // 内存缓存命中次数
                    'redis_hits' => 0,        // Redis缓存命中次数
                    'total_misses' => 0,      // 总未命中次数（需要从源站获取）
                    // 新增统计项
                    'm3u8_requests' => 0,     // M3U8文件请求总次数
                    'm3u8_hits' => 0,         // M3U8文件缓存命中总次数
                    'm3u8_memory_hits' => 0,  // M3U8文件内存缓存命中次数
                    'm3u8_redis_hits' => 0,   // M3U8文件Redis缓存命中次数
                    'm3u8_misses' => 0,       // M3U8文件缓存未命中次数
                    'ts_requests' => 0,       // TS文件请求总次数
                    'ts_hits' => 0,          // TS文件缓存命中总次数
                    'ts_memory_hits' => 0,   // TS文件内存缓存命中次数
                    'ts_redis_hits' => 0,    // TS文件Redis缓存命中次数
                    'ts_misses' => 0,        // TS文件缓存未命中次数
                    'last_cleanup_time' => 0,      // 最后一次缓存清理的时间戳
                    'total_cleanup_count' => 0,    // 执行缓存清理的总次数
                    'total_cleaned_items' => 0,    // 被清理的缓存项目总数
            ];
            
            // 将所有值转换为整数
            $stats = array_map('intval', $stats);
            
            //计算总体信息
            $stats['items_count'] = $stats['items_count'];
            $stats['m3u8_count'] = $stats['m3u8_count'];
            $stats['ts_count'] = $stats['ts_count'];
            $stats['channel_count'] = $stats['channel_count'];
            // 计算总体命中率
            $totalRequests = max(1, $stats['total_requests']);
            $stats['hit_rate'] = ($stats['total_hits'] / $totalRequests) * 100;
            $stats['memory_hit_rate'] = ($stats['memory_hits'] / $totalRequests) * 100;
            $stats['redis_hit_rate'] = ($stats['redis_hits'] / $totalRequests) * 100;
            
            // 计算M3U8命中率
            $m3u8Requests = max(1, $stats['m3u8_requests']);
            $stats['m3u8_hit_rate'] = ($stats['m3u8_hits'] / $m3u8Requests) * 100;
            $stats['m3u8_memory_hit_rate'] = ($stats['m3u8_memory_hits'] / $m3u8Requests) * 100;
            $stats['m3u8_redis_hit_rate'] = ($stats['m3u8_redis_hits'] / $m3u8Requests) * 100;
            
            // 计算TS命中率
            $tsRequests = max(1, $stats['ts_requests']);
            $stats['ts_hit_rate'] = ($stats['ts_hits'] / $tsRequests) * 100;
            $stats['ts_memory_hit_rate'] = ($stats['ts_memory_hits'] / $tsRequests) * 100;
            $stats['ts_redis_hit_rate'] = ($stats['ts_redis_hits'] / $tsRequests) * 100;
            
            // 添加缓存大小信息
            $stats['memory_cache_size'] = $this->getMemoryCacheSize();
            $stats['memory_cache_size_mb'] = round($stats['memory_cache_size'] / 1024 / 1024, 2);
            $stats['memory_cache_count'] = count(self::$tsCache);
            $stats['redis_keys_count'] = $this->getRedisKeysCount();
            
            // 添加缓存配置信息
            $stats['memory_cache_enabled'] = $this->enableMemoryCache;
            $stats['redis_cache_enabled'] = $this->enableRedisCache;
            //$stats['max_memory_cache_size'] = $this->maxMemoryCacheSize;
            $stats['max_memory_cache_size'] = $config->get('max_memory_cache_size', 256) * 1024 * 1024;
            $stats['max_size'] = $config->get('max_memory_cache_size', 256) * 1024 * 1024;
            $stats['max_memory_cache_size_mb'] = round($this->maxMemoryCacheSize / 1024 / 1024, 2);
            $stats['cache_cleanup_interval'] = $this->cacheCleanupInterval;
            $stats['time_since_last_cleanup'] = time() - $this->lastCleanupTime;
            
            //$this->errorLog("【缓存统计信息】获取缓存信息结束。", 'error', __FILE__, __LINE__);
            return $stats;
            
        } catch (\Exception $e) {
            $this->errorLog("获取缓存统计失败: " . $e->getMessage(), 'error', __FILE__, __LINE__);
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
                'm3u8_requests' => 0,
                'm3u8_hits' => 0,
                'm3u8_memory_hits' => 0,
                'm3u8_redis_hits' => 0,
                'm3u8_misses' => 0,
                'ts_requests' => 0,
                'ts_hits' => 0,
                'ts_memory_hits' => 0,
                'ts_redis_hits' => 0,
                'ts_misses' => 0,
                'last_cleanup_time' => 0,
                'total_cleanup_count' => 0,
                'total_cleaned_items' => 0,
                'hit_rate' => 0,
                'memory_hit_rate' => 0,
                'redis_hit_rate' => 0,
                'm3u8_hit_rate' => 0,
                'm3u8_memory_hit_rate' => 0,
                'm3u8_redis_hit_rate' => 0,
                'ts_hit_rate' => 0,
                'ts_memory_hit_rate' => 0,
                'ts_redis_hit_rate' => 0,
                'memory_cache_size' => 0,
                'memory_cache_size_mb' => 0,
                'memory_cache_count' => 0,
                'redis_keys_count' => 0,
                'memory_cache_enabled' => false,
                'redis_cache_enabled' => false,
                'max_memory_cache_size' => 0,
                'max_memory_cache_size_mb' => 0,
                'cache_cleanup_interval' => 0,
                'time_since_last_cleanup' => 0
            ];
        }
    }

    /**
     * 更新频道分片信息
     * @param string $channelId 频道ID
     * @param array $segments 分片信息数组
     */
    private function updateChannelSegments($channelId, $segments)
    {
        //$this->errorLog("【updateChannelSegments】开始处理 - 频道ID: {$channelId}", 'info', __FILE__, __LINE__);
        // 更新内存中的分片信息
        self::$m3u8SegmentInfo[$channelId] = [
            'segments' => $segments,
            'update_time' => time()
        ];
        
        // 更新Redis缓存
        $key = "m3u8:segments:{$channelId}";
        $this->redis->setex(
            $key,
            30, // 30秒过期
            json_encode(self::$m3u8SegmentInfo[$channelId])
        );
        
        // 更新频道进度
        if (!isset(self::$channelProgress[$channelId])) {
            self::$channelProgress[$channelId] = [
                'current_index' => 0,
                'last_update' => time()
            ];
        }
    }

    /**
     * 触发异步加载
     * @param string $channelId 频道ID
     */
    private function triggerAsyncLoad($channelId)
    {
        try {
            $this->initAsyncLoader();
            if (self::$asyncLoader) {
                // 获取频道信息
                if (isset(self::$m3u8SegmentInfo[$channelId])) {
                    $segments = self::$m3u8SegmentInfo[$channelId]['segments'];
                    foreach ($segments as $segment) {
                        if (!$segment['loaded']) {
                            // 添加TS文件加载任务
                            self::$asyncLoader->addTask(
                                $channelId,
                                $segment['url'],
                                'ts',
                                'medium',
                                ['index' => $segment['index']]
                            );
                        }
                    }
                }
            }
        } catch (\Exception $e) {
            // 记录错误但不中断流程
            error_log("触发异步加载失败: " . $e->getMessage());
        }
    }

    /**
     * 获取Redis键数量
     */
    private function getRedisKeysCount()
    {
        try {
            return count($this->redis->keys("ts:*"));
        } catch (\Exception $e) {
            $this->logger->error("获取Redis键数量失败: " . $e->getMessage());
            return 0;
        }
    }

    /**
     * 清理内存缓存
     */
    private function cleanMemoryCache()
    {
        //$this->errorLog("【cleanMemoryCache】开始处理", 'info', __FILE__, __LINE__);
        $config = Config::getInstance();
        $max_memory_cache_size = $config->get('max_memory_cache_size', 256);
        $maxSize = $max_memory_cache_size * 1024 * 1024; 
        $currentSize = $this->getMemoryCacheSize();
        
        if ($currentSize > $maxSize) {
            // 按时间排序
            uasort(self::$tsCache, function($a, $b) {
                $timeA = is_array($a) ? ($a['time'] ?? 0) : time();
                $timeB = is_array($b) ? ($b['time'] ?? 0) : time();
                return $timeA - $timeB;
            });
            
            // 删除旧的缓存直到大小合适
            foreach (self::$tsCache as $key => $item) {
                unset(self::$tsCache[$key]);
                $currentSize = $this->getMemoryCacheSize();
                if ($currentSize <= $maxSize * 0.8) { // 留20%余量
                    break;
                }
            }
        }
    }

    private function errorLog($message, $level = 'error', $file = null, $line = null)
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

    /**
     * 获取频道的分片信息
     * @param string $channelId
     * @return array|null
     */
    public function getChannelSegments($channelId)
    {
        if (isset(self::$m3u8SegmentInfo[$channelId])) {
            return self::$m3u8SegmentInfo[$channelId]['segments'];
        }
        return null;
    }

    /**
     * 检查内存缓存大小并在必要时进行清理
     */
    private function checkMemoryCacheSize()
    {
        //$this->errorLog("【checkMemoryCacheSize】开始处理", 'info', __FILE__, __LINE__);
        if (!$this->enableMemoryCache) {
            return;
        }

        $currentSize = $this->getMemoryCacheSize();
        
        // 如果超过最大限制,清理最旧的缓存
        if ($currentSize > $this->maxMemoryCacheSize) {
            //$this->errorLog("[缓存管理] 内存缓存超出限制，开始清理", 'info', __FILE__, __LINE__);
            
            // 按时间排序
            uasort(self::$tsCache, function($a, $b) {
                return $a['time'] - $b['time'];
            });
            
            // 清理直到低于限制的80%
            $targetSize = $this->maxMemoryCacheSize * 0.8;
            foreach (self::$tsCache as $key => $item) {
                unset(self::$tsCache[$key]);
                $currentSize = $this->getMemoryCacheSize();
                if ($currentSize <= $targetSize) {
                    break;
                }
            }
            
            $this->errorLog(
                sprintf("[缓存管理] 内存缓存清理完成，当前大小: %.2fMB", $currentSize / 1024 / 1024),
                'info',
                __FILE__,
                __LINE__
            );
        }
    }

    /**
     * 检查是否需要执行定期缓存清理
     */
    private function checkCacheCleanup()
    {
        
        $now = time();
        // 添加调试日志
        /*
        $this->errorLog(
            sprintf(
                "[缓存管理] 检查清理间隔 - 当前时间: %d, 上次清理: %d, 间隔: %d秒, 配置间隔: %d秒",
                $now,
                $this->lastCleanupTime,
                ($now - $this->lastCleanupTime),
                $this->cacheCleanupInterval
            ),
            'info',
            __FILE__,
            __LINE__
        );
        */
        // 检查是否达到清理间隔
        if (($now - $this->lastCleanupTime) >= $this->cacheCleanupInterval) {
            //$this->errorLog("[缓存管理] 开始定期缓存清理", 'info', __FILE__, __LINE__);
            $this->cleanExpiredCache();
            $this->lastCleanupTime = $now;
        }
    }

    /**
     * 清理过期的缓存内容
     */
    private function cleanExpiredCache()
    {
        //$this->errorLog("【cleanExpiredCache】开始处理", 'info', __FILE__, __LINE__);
        $now = time();
        $cleanupStats = [
            'm3u8_cleaned' => 0,
            'ts_cleaned' => 0
        ];
        $config = Config::getInstance();
        $memoryCacheTTL = $config->get('memory_cache_ttl', 30);
        //$redisCacheTTL = $config->get('redis_cache_ttl', 300);
        if ($this->enableMemoryCache) {
            // 清理过期的M3U8缓存
            foreach (self::$m3u8Cache as $channelId => $data) {
                if (($now - $data['time']) >= $memoryCacheTTL) {
                    unset(self::$m3u8Cache[$channelId]);
                    $cleanupStats['m3u8_cleaned']++;
                }
            }
            
            // 清理过期的TS缓存
            foreach (self::$tsCache as $key => $data) {
                if (($now - $data['time']) >= $memoryCacheTTL) {
                    unset(self::$tsCache[$key]);
                    $cleanupStats['ts_cleaned']++;
                }
            }

            // 首先获取现有的统计数据
            $key = $config->get('monitor_cache_stats', 'monitor:cache_stats');
            $jsonData = $this->redis->get($key);
            $stats = !empty($jsonData) ? json_decode($jsonData, true) : [];
            
            //$this->errorLog("【缓存统计信息】更新前: " . json_encode($stats));
            
            // 只更新这几个字段
            $stats['used_memory'] = 0;
            $stats['items_count'] = 0;
            $stats['m3u8_count'] = 0;
            $stats['ts_count'] = 0;
            $stats['last_cleanup_time'] = time();
            $stats['total_cleanup_count'] += $cleanupStats['m3u8_cleaned']+$cleanupStats['ts_cleaned'];
            $stats['total_cleaned_items'] = $cleanupStats['m3u8_cleaned']+$cleanupStats['ts_cleaned'];
            
            // 重新计算这四个字段的实际值
            if (!empty(self::$m3u8SegmentInfo)) {
                $stats['m3u8_count'] = count(self::$m3u8SegmentInfo);
            }
            
            if (!empty(self::$tsCache)) {
                $stats['ts_count'] = count(self::$tsCache);
                foreach (self::$tsCache as $tsData) {
                    $stats['used_memory'] += strlen($tsData['content']);
                }
            }
            
            // 更新总项目数
            $stats['items_count'] = $stats['m3u8_count'] + $stats['ts_count'];
            
            // 保存更新后的统计信息
            $this->redis->setex($key, 86400, json_encode($stats));
            
            //$this->errorLog("【缓存统计信息】更新后: " . json_encode($stats));
            //用于重要调试，请勿删除
            $this->errorLog(
                sprintf(
                    "[缓存管理] 清理完成 - 清理M3U8: %d个, TS: %d个",
                    $cleanupStats['m3u8_cleaned'],
                    $cleanupStats['ts_cleaned']
                ),
                'info',
                __FILE__,
                __LINE__
            );
            return true;
        }
        
        
        
    }

    /**
     * 获取当前内存缓存大小(字节)
     * 已修改，可能会和其他方法不兼容，后面特别留意
     */
    private function getMemoryCacheSize()
    {
        $size = 0;
        
        // 计算TS缓存大小
        foreach (self::$tsCache as $item) {
            if (isset($item['size'])) {
                $size += $item['size'];
            }
        }
        
        // 计算M3U8缓存大小
        foreach (self::$m3u8Cache as $item) {
            if (isset($item['content'])) {
                $size += strlen($item['content']);
            }
        }
        
        return $size;
    }
}