<?php
namespace App\Core;

class AsyncLoader
{
    // 任务队列
    private $taskQueue = [];
    // 优先级队列
    private $priorityQueue = [];
    // 运行状态
    private $running = false;
    // 最大并发数
    private $maxConcurrent = 5;
    // 当前并发数
    private $currentConcurrent = 0;
    // 统计信息
    private $stats = [
        'total_tasks' => 0,
        'completed_tasks' => 0,
        'failed_tasks' => 0,
        'bytes_loaded' => 0
    ];
    // 缓存实例
    private $cache;
    // curl多句柄
    private $multiHandle;
    // 活动的curl句柄
    private $activeHandles = [];

    private $redis;
    private $config;
    private $queue = [];

    private $isProcessing = false;
    private $logger;
    private $errorLog;
    
    public function __construct()
    {
        $this->cache = ChannelContentCache::getInstance();
        $this->initPriorityQueue();
        $this->multiHandle = curl_multi_init();
        $this->logger = new \App\Core\Logger();
        $this->errorLog = new \App\Models\ErrorLog();  // 添加这行
        $this->queue = [];                             // 添加这行
        $this->isProcessing = false;                   // 添加这行
    }
    
    /**
     * 初始化优先级队列
     */
    private function initPriorityQueue()
    {
        $this->priorityQueue = [
            'high' => [],    // 当前M3U8的下一个TS
            'medium' => [],  // 当前M3U8的后续TS
            'low' => []      // 下一个M3U8及其TS
        ];
    }
    
    /**
     * 添加加载任务
     */
    // 修改前的方法完全替换为以下内容
    public function addTask($channelId, $url, $type, $priority = 'normal', $metadata = [], $timeout = 10)
    {
        $startTime = microtime(true);
        try {
            $task = [
                'channel_id' => $channelId,
                'url' => $url,
                'type' => $type,
                'priority' => $priority,
                'metadata' => $metadata,
                'timeout' => $timeout,
                'add_time' => time()
            ];

            // 将任务添加到队列
            $this->queue[] = $task;

            // 使用非阻塞方式处理任务
            if (!$this->isProcessing) {
                $this->isProcessing = true;
                // 启动一个新的进程来处理任务
                $pid = pcntl_fork();
                if ($pid == 0) {
                    // 子进程
                    $this->processQueuedTasks();
                    exit(0);
                } elseif ($pid == -1) {
                    // fork失败，回退到同步处理
                    $this->processTask($task);
                }
                $this->isProcessing = false;
            }

            return true;
        } catch (\Exception $e) {
            $this->errorLog->add([
                'level' => 'error',
                'message' => "添加异步任务失败: " . $e->getMessage(),
                'file' => __FILE__,
                'line' => __LINE__
            ]);
            return false;
        }
    }
    
    private function processQueuedTasks()
    {
        while (!empty($this->queue)) {
            $task = array_shift($this->queue);
            try {
                $startTime = microtime(true);
                
                // 设置上下文选项
                $context = stream_context_create([
                    'http' => [
                        'timeout' => $task['timeout'],
                        'user_agent' => 'VLC/3.0.20 LibVLC/3.0.20'
                    ],
                    'ssl' => [
                        'verify_peer' => false,
                        'verify_peer_name' => false
                    ]
                ]);

                // 使用非阻塞方式获取内容
                $content = @file_get_contents($task['url'], false, $context);
                if ($content === false) {
                    continue;
                }

                // 根据任务类型处理内容
                if ($task['type'] === 'ts') {
                    // 添加带宽统计，从源服务器获取的数据是下行带宽
                    $this->updateBandwidthStats($task['channel_id'], strlen($content), 0);
                    $cache = ChannelContentCache::getInstance();
                    $cache->cacheTs($task['channel_id'], $task['url'], $content);
                }

            } catch (\Exception $e) {
                $this->errorLog->add([
                    'level' => 'error',
                    'message' => "处理队列任务失败: " . $e->getMessage(),
                    'file' => __FILE__,
                    'line' => __LINE__
                ]);
            }
        }
    }

    private function processTask($task)
    {
        try {
            $startTime = microtime(true);
            
            // 设置上下文选项
            $context = stream_context_create([
                'http' => [
                    'timeout' => $task['timeout'],
                    'user_agent' => 'VLC/3.0.20 LibVLC/3.0.20'
                ],
                'ssl' => [
                    'verify_peer' => false,
                    'verify_peer_name' => false
                ]
            ]);

            // 使用非阻塞方式获取内容
            $content = @file_get_contents($task['url'], false, $context);
            if ($content === false) {
                throw new \Exception("获取内容失败");
            }

            // 根据任务类型处理内容
            if ($task['type'] === 'ts') {
                $cache = ChannelContentCache::getInstance();
                $cache->cacheTs($task['channel_id'], $task['url'], $content);
            }

            $endTime = microtime(true);
            $duration = ($endTime - $startTime) * 1000;
            $this->errorLog->add([
                'level' => 'info',
                'message' => "异步任务处理完成，耗时: {$duration}ms",
                'file' => __FILE__,
                'line' => __LINE__
            ]);

        } catch (\Exception $e) {
            $this->errorLog->add([
                'level' => 'error',
                'message' => "处理异步任务失败: " . $e->getMessage(),
                'file' => __FILE__,
                'line' => __LINE__
            ]);
        }
    }

    /**
     * 启动异步加载器
     */
    public function start()
    {
        if ($this->running) {
            return;
        }
        
        $this->running = true;
        $this->processTasks();
    }
    
    /**
     * 处理任务队列
     */
    private function processTasks()
    {
        while ($this->running && $this->currentConcurrent < $this->maxConcurrent) {
            $task = $this->getNextTask();
            if (!$task) {
                break;
            }
            
            $this->startTask($task);
        }
        
        $this->executeMultiHandle();
    }
    
    /**
     * 开始一个任务
     */
    private function startTask($task)
    {
        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $task['url'],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT => 10,
            CURLOPT_CONNECTTIMEOUT => 3,
            CURLOPT_USERAGENT => 'VLC/3.0.20 LibVLC/3.0.20',
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_SSL_VERIFYHOST => false
        ]);
        
        curl_multi_add_handle($this->multiHandle, $ch);
        $this->activeHandles[(int)$ch] = [
            'handle' => $ch,
            'task' => $task
        ];
        
        $this->currentConcurrent++;
    }
    
    /**
     * 执行多句柄请求
     */
    private function executeMultiHandle()
    {
        $running = null;
        do {
            $status = curl_multi_exec($this->multiHandle, $running);
            if ($running) {
                curl_multi_select($this->multiHandle, 0.1);
            }
            
            $this->processCompletedTasks();
            
        } while ($running > 0 && $this->running);
    }
    
    /**
     * 处理完成的任务
     */
    private function processCompletedTasks()
    {
        while ($done = curl_multi_info_read($this->multiHandle)) {
            $ch = $done['handle'];
            $handleId = (int)$ch;
            
            if (!isset($this->activeHandles[$handleId])) {
                continue;
            }
            
            $task = $this->activeHandles[$handleId]['task'];
            $content = curl_multi_getcontent($ch);
            $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            
            if ($httpCode === 200 && $content) {
                $this->handleSuccessfulTask($task, $content);
            } else {
                $this->handleFailedTask($task);
            }
            
            curl_multi_remove_handle($this->multiHandle, $ch);
            curl_close($ch);
            unset($this->activeHandles[$handleId]);
            $this->currentConcurrent--;
            
            // 处理新的任务
            $this->processTasks();
        }
    }
    
    /**
     * 处理成功的任务
     */
    private function handleSuccessfulTask($task, $content)
    {
        if ($task['type'] === 'm3u8') {
            $this->handleM3u8Content($task['channel_id'], $content, $task['url']);
        } else {
            $this->handleTsContent($task['channel_id'], $task['url'], $content, $task['extra']);
        }
        
        $this->stats['completed_tasks']++;
        $this->stats['bytes_loaded'] += strlen($content);
    }
    
    /**
     * 处理M3U8内容
     */
    private function handleM3u8Content($channelId, $content, $url)
    {
        $baseUrl = dirname($url);
        $this->cache->parseAndCacheM3u8($channelId, $content, $baseUrl);
        
        $nextSegment = $this->cache->getNextSegmentToLoad($channelId);
        if ($nextSegment) {
            $this->addTask($channelId, $nextSegment['url'], 'ts', 'high', [
                'index' => $nextSegment['index']
            ]);
        }
    }
    
    /**
     * 处理TS内容
     */
    private function handleTsContent($channelId, $url, $content, $extra)
    {
        $this->cache->cacheTs($channelId, $url, $content);
        
        if (isset($extra['index'])) {
            $this->cache->markSegmentLoaded($channelId, $url, $extra['index']);
        }
        
        $nextSegment = $this->cache->getNextSegmentToLoad($channelId);
        if ($nextSegment) {
            $this->addTask($channelId, $nextSegment['url'], 'ts', 'medium', [
                'index' => $nextSegment['index']
            ]);
        }
    }
    
    /**
     * 处理失败的任务
     */
    private function handleFailedTask($task)
    {
        $task['retry_count']++;
        $this->stats['failed_tasks']++;
        
        if ($task['retry_count'] < 3) {
            // 使用指数退避策略
            $delay = pow(2, $task['retry_count']);
            $this->priorityQueue[$task['priority']][] = array_merge($task, [
                'add_time' => microtime(true) + $delay
            ]);
        }
    }
    
    /**
     * 停止加载器
     */
    public function stop()
    {
        $this->running = false;
        
        // 清理所有活动的句柄
        foreach ($this->activeHandles as $handle) {
            curl_multi_remove_handle($this->multiHandle, $handle['handle']);
            curl_close($handle['handle']);
        }
        
        curl_multi_close($this->multiHandle);
        $this->activeHandles = [];
        $this->currentConcurrent = 0;
    }
    
    /**
     * 获取加载器状态
     */
    public function getStatus()
    {
        return [
            'running' => $this->running,
            'concurrent' => $this->currentConcurrent,
            'queue_sizes' => [
                'high' => count($this->priorityQueue['high']),
                'medium' => count($this->priorityQueue['medium']),
                'low' => count($this->priorityQueue['low'])
            ],
            'stats' => $this->stats
        ];
    }
    
    /**
     * 清理指定频道的任务
     */
    public function clearChannelTasks($channelId)
    {
        foreach ($this->priorityQueue as $priority => $tasks) {
            $this->priorityQueue[$priority] = array_filter($tasks, function($task) use ($channelId) {
                return $task['channel_id'] !== $channelId;
            });
        }
    }
    
    public function __destruct()
    {
        $this->stop();
    }

    /**
     * 获取下一个要处理的任务
     * @return array|null 任务数组或null（如果没有任务）
     */
    private function getNextTask()
    {
        // 按优先级顺序检查队列
        foreach (['high', 'medium', 'low'] as $priority) {
            if (!empty($this->priorityQueue[$priority])) {
                return array_shift($this->priorityQueue[$priority]);
            }
        }
        return null;
    }

    public function loadSegments($channelId, $segments)
    {
        $key = "async:ts:queue:{$channelId}";
        $task = [
            'channel_id' => $channelId,
            'segments' => $segments,
            'time' => time()
        ];
        
        // 添加到Redis队列
        $this->redis->setex($key, 300, json_encode($task));
    }
    
    public function processQueue()
    {
        while (true) {
            $keys = $this->redis->keys("async:ts:queue:*");
            foreach ($keys as $key) {
                $data = $this->redis->get($key);
                if (!$data) continue;
                
                $task = json_decode($data, true);
                if (!$task) continue;
                
                foreach ($task['segments'] as $segment) {
                    $this->loadSegment($task['channel_id'], $segment);
                }
                
                $this->redis->del($key);
            }
            usleep(100000);
        }
    }
    
    private function loadSegment($channelId, $segment)
    {
        $cacheKey = "ts:{$channelId}:" . md5($segment['cache_url']);
        
        // 检查是否已缓存
        if ($this->redis->exists($cacheKey)) {
            return;
        }
        
        // 下载并缓存TS文件
        $content = $this->downloadTs($segment['url']);
        if ($content !== false) {
            // 在这里更新带宽统计，因为这里是确实下载到了内容
            $this->updateBandwidthStats($task['channel_id'], strlen($content), 0);
            
            $this->redis->setex($cacheKey, 30, $content);
        }
    }

   /**
     * 更新带宽统计信息
     * 记录和更新频道的异步加载带宽使用情况
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
            error_log("AsyncLoader: 更新带宽统计失败: " . $e->getMessage());
        }
    }
}