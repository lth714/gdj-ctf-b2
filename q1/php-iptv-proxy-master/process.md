# PHP IPTV 代理服务器工作流程分析

## 1. 客户端连接建立
当客户端首次连接时，会经过以下步骤：

1. 服务器监听端口，等待客户端连接
2. 客户端发起连接请求
3. 服务器通过 `handleRequest` 方法处理请求
   ```php
   private function handleRequest($client, $data)
   {
       $clientId = (int)$client;
       // 记录原始请求数据
       $this->logError("handleRequest收到请求数据 - 客户端ID: {$clientId}, 数据: " . substr($data, 0, 200));
       
       // 存储客户端信息
       if (!isset($this->clients[$clientId])) {
           $this->clients[$clientId] = [];
       }
       $this->clients[$clientId]['request'] = $data;
   ```

## 2. 请求解析
服务器解析 HTTP 请求，提取关键信息：

1. 解析 HTTP 请求行
   ```php
   $lines = explode("\r\n", $data);
   $firstLine = explode(' ', $lines[0]);
   $method = $firstLine[0];
   $rawPath = $firstLine[1];
   ```

2. 解析 URL 路径
   ```php
   $path = parse_url($rawPath, PHP_URL_PATH);
   ```

3. 提取频道 ID 和请求类型
   ```php
   if (!preg_match('/^\/proxy\/(ch_[^\/]+)\/([^\/]+)$/', $path, $matches)) {
       // 处理错误
   }
   $channelId = $matches[1];
   $requestFile = $matches[2];
   ```

## 3. 请求类型判断
根据请求的文件类型，分为两种处理流程：

1. M3U8 请求（playlist）
   ```php
   if ($requestFile === 'stream.m3u8') {
       $this->proxyM3U8($client, $channel);
   }
   ```

2. TS 文件请求（视频片段）
   ```php
   else if (preg_match('/\.ts/', $requestFile)) {
       $this->proxyTS($client, $channel, $requestFile);
   }
   ```

## 4. M3U8 处理流程 (proxyM3U8)
当客户端请求 M3U8 文件时：

1. 构建源站 URL
2. 从源站获取 M3U8 内容
   ```php
   $content = curl_exec($ch);
   ```

3. 处理 M3U8 内容
   - 验证内容有效性
   - 处理 TS 文件 URL
   - 保留参数信息

4. 缓存处理
   ```php
   $channelContentCache->parseAndCacheM3u8($channelId, $processedContent, $baseUrl);
   ```

5. 发送响应
   ```php
   $this->sendStreamData($client, $processedContent, 'application/vnd.apple.mpegurl');
   ```

## 5. TS 文件处理流程 (proxyTS)
当客户端请求 TS 文件时：

1. 解析 TS 文件 URL
   ```php
   $tsPath = parse_url($tsFile, PHP_URL_PATH);
   $tsQuery = parse_url($tsFile, PHP_URL_QUERY);
   ```

2. 构建源站和缓存 URL
   ```php
   $sourceUrl = $this->buildSourceUrl($channel['source_url'], $tsFile);
   $cacheUrl = $this->buildSourceUrl($channel['source_url'], $tsPath);
   ```

3. 检查缓存
   ```php
   $cacheKey = $this->generateCacheKey($channel['id'], $cacheUrl);
   $content = $this->getFromCache($cacheKey);
   ```

4. 如果缓存命中：
   - 更新带宽统计
   - 发送缓存内容
   ```php
   $this->updateBandwidthStats(0, $contentSize);
   $this->sendStreamData($client, $content, 'video/MP2T');
   ```

5. 如果缓存未命中：
   - 从源站获取内容
   ```php
   $content = $this->readFromSource($sourceUrl);
   ```
   - 更新带宽统计
   ```php
   $this->updateBandwidthStats($contentSize, $contentSize);
   ```
   - 保存到缓存
   ```php
   $this->saveToCache($cacheKey, $content);
   ```
   - 发送响应
   ```php
   $this->sendStreamData($client, $content, 'video/MP2T');
   ```

## 6. 数据发送流程 (sendStreamData)
发送数据到客户端的过程：

1. 构建响应头
   ```php
   $headers = [
       "HTTP/1.1 200 OK",
       "Content-Type: " . $contentType,
       "Content-Length: " . $totalLength,
       "Access-Control-Allow-Origin: *",
       "Cache-Control: no-cache",
       "Connection: close",
       "",
       ""
   ];
   ```

2. 发送响应头并更新带宽统计
   ```php
   $written = @fwrite($client, $headerStr);
   $this->updateBandwidthStats(0, $written);
   ```

3. 分块发送内容
   ```php
   $chunkSize = 65536; // 64KB
   while ($offset < $totalLength) {
       $chunk = substr($data, $offset, $chunkSize);
       $written = @fwrite($client, $chunk);
       $this->updateBandwidthStats(0, $written);
   }
   ```

## 7. 带宽统计流程
整个过程中的带宽统计：

1. 下行带宽（从源站获取）
   - 在 `readFromSource` 中统计
   - 使用 `updateBandwidthStats($downloadSize, 0)`

2. 上行带宽（发送给客户端）
   - 在 `sendStreamData` 中统计
   - 使用 `updateBandwidthStats(0, $written)`

3. 统计存储
   ```php
   $statsKey = "proxy:bandwidth_stats";
   $this->redis->hMSet($statsKey, $stats);
   $this->redis->expire($statsKey, 60);
   ```

## 8. 缓存机制
系统使用两级缓存：

1. 内存缓存
   - 存储在 `ChannelContentCache::$tsCache` 中
   - 快速访问，容量有限

2. Redis 缓存
   - 持久化存储
   - 更大容量
   - 支持分布式

## 9. 错误处理
全流程都有完整的错误处理：

1. 请求错误处理
   ```php
   $this->handleClientError($client, "错误信息");
   ```

2. 日志记录
   ```php
   $this->logError("错误信息", 'error', __FILE__, __LINE__);
   ```

3. 错误响应
   ```php
   $this->sendErrorResponse($client, 状态码, "错误信息");
   ```

这就是整个系统的完整工作流程。每个步骤都有详细的日志记录，方便调试和监控。系统通过缓存机制提高性能，通过带宽统计实现流量监控，通过错误处理确保稳定性。 