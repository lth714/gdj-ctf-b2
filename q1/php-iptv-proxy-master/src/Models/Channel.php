<?php
namespace App\Models;

use App\Core\Database;

class Channel
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance()->getConnection();
        // 在构造函数中检查表结构
        $this->ensureTableStructure();
    }

    public function getChannelStats()
    {
        try {
            // 获取总频道数
            //1是活跃的，2是不活跃的，3是错误的
            $totalQuery = "SELECT COUNT(*) as total FROM channels";
            $totalResult = $this->db->query($totalQuery);
            $total = $totalResult->fetch(\PDO::FETCH_ASSOC)['total'];

            // 获取活跃频道数（最近5分钟内有访问的频道）
            $activeQuery = "SELECT COUNT(*) as active FROM channels 
                          WHERE last_accessed >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                          AND status = 'active'";
            $activeResult = $this->db->query($activeQuery);
            $active = $activeResult->fetch(\PDO::FETCH_ASSOC)['active'];

            // 获取错误频道数
            $errorQuery = "SELECT COUNT(*) as error FROM channels WHERE status = 'error'";
            $errorResult = $this->db->query($errorQuery);
            $error = $errorResult->fetch(\PDO::FETCH_ASSOC)['error'];

            return [
                'total_channels' => (int)$total,
                'active_channels' => (int)$active,
                'error_channels' => (int)$error
            ];
        } catch (\PDOException $e) {
            // 如果发生错误，返回默认值
            return [
                'total_channels' => 0,
                'active_channels' => 0,
                'error_channels' => 0
            ];
        }
    }

    // 检查频道状态
    public function updateChannelStatus($channelId, $status)
    {
        try {
            $query = "UPDATE channels SET status = :status, last_checked = NOW() 
                     WHERE id = :channel_id";
            $stmt = $this->db->prepare($query);
            return $stmt->execute([
                'status' => $status,
                'channel_id' => $channelId
            ]);
        } catch (\PDOException $e) {
            return false;
        }
    }

    // 更新频道访问时间
    public function updateLastAccessed($channelId)
    {
        try {
            $query = "UPDATE channels SET last_accessed = NOW() WHERE id = :channel_id";
            $stmt = $this->db->prepare($query);
            return $stmt->execute(['channel_id' => $channelId]);
        } catch (\PDOException $e) {
            return false;
        }
    }

    public function getChannelList($page = 1, $perPage = 20, $groupId = null)
    {
        try {
            $offset = ($page - 1) * $perPage;
            
            $where = [];
            $params = [];
            
            if ($groupId !== null) {
                $where[] = "c.group_id = :group_id";
                $params[':group_id'] = $groupId;
            }
            
            $whereClause = !empty($where) ? "WHERE " . implode(" AND ", $where) : "";
            
            // 获取总数
            $countQuery = "SELECT COUNT(*) FROM channels c {$whereClause}";
            $stmt = $this->db->prepare($countQuery);
            foreach ($params as $key => $value) {
                $stmt->bindValue($key, $value);
            }
            $stmt->execute();
            $total = $stmt->fetchColumn();
            
            // 获取频道列表
            $query = "SELECT c.*, g.name as group_name, 
                     CASE WHEN c.status = 0 THEN c.error_count ELSE 0 END as current_error_count 
                     FROM channels c 
                     LEFT JOIN channel_groups g ON c.group_id = g.id 
                     {$whereClause} 
                     ORDER BY c.id DESC 
                     LIMIT :offset, :limit";
            
            $stmt = $this->db->prepare($query);
            
            foreach ($params as $key => $value) {
                $stmt->bindValue($key, $value);
            }
            
            $stmt->bindValue(':offset', $offset, \PDO::PARAM_INT);
            $stmt->bindValue(':limit', $perPage, \PDO::PARAM_INT);
            $stmt->execute();
            
            $channels = $stmt->fetchAll(\PDO::FETCH_ASSOC);
            
            return [
                'channels' => $channels,
                'total' => $total,
                'totalPages' => ceil($total / $perPage)
            ];
        } catch (\PDOException $e) {
            error_log("Error getting channel list: " . $e->getMessage());
            return ['channels' => [], 'total' => 0, 'totalPages' => 0];
        }
    }

    public function checkChannel($id)
    {
        try {
            $settings = Settings::getInstance()->get();
            $maxErrorCount = $settings['max_error_count'] ?? 3;

            $channel = $this->getChannel($id);
            if (!$channel) {
                return ['success' => false, 'message' => '频道不存在'];
            }

            // 处理源地址中的@符号
            $sourceUrl = $channel['source_url'];
            if (strpos($sourceUrl, '@') === 0) {
                $sourceUrl = substr($sourceUrl, 1);
            }

            $ch = curl_init($sourceUrl);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 5);
            //curl_setopt($ch, CURLOPT_NOBODY, true);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_RANGE, '0-1024');  // 只获取前1KB内容
            curl_setopt($ch, CURLOPT_USERAGENT, 'VLC/3.0.20 LibVLC/3.0.20');  // 添加User-Agent
            
            $startTime = microtime(true);
            $result = curl_exec($ch);
            $latency = round((microtime(true) - $startTime) * 1000);
            
            $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);

            $status = ($httpCode >= 200 && $httpCode < 400) ? 'active' : 'error';
            $errorCount = $channel['error_count'];
            
            if ($status === 'error') {
                $errorCount++;
                if ($errorCount >= $maxErrorCount) {
                    // 删除频道
                    $this->deleteChannel($id);
                    return [
                        'success' => true,
                        'deleted' => true,
                        'message' => '频道已被自动删除（连续检查失败达到最大次数）'
                    ];
                }
            } else {
                $errorCount = 0;
            }

            // 更新频道状态
            $query = "UPDATE channels SET 
                     status = :status,
                     latency = :latency,
                     error_count = :error_count,
                     checked_at = NOW(),
                     updated_at = NOW()
                     WHERE id = :id";
            
            $stmt = $this->db->prepare($query);
            $stmt->execute([
                ':status' => $status,
                ':latency' => $latency,
                ':error_count' => $errorCount,
                ':id' => $id
            ]);

            return [
                'success' => true,
                'status' => $status,
                'latency' => $latency,
                'error_count' => $errorCount,
                'checked_at' => date('Y-m-d H:i:s')
            ];
        } catch (\Exception $e) {
            error_log("Error checking channel {$id}: " . $e->getMessage());
            return ['success' => false, 'message' => '检查失败：' . $e->getMessage()];
        }
    }

    public function deleteChannel($id)
    {
        try {
            $this->db->beginTransaction();

            // 获取频道信息用于日志记录
            $channel = $this->getChannel($id);
            
            // 获取频道所属分组ID
            $query = "SELECT group_id FROM channels WHERE id = :id";
            $stmt = $this->db->prepare($query);
            $stmt->execute([':id' => $id]);
            $groupId = $stmt->fetch(\PDO::FETCH_COLUMN);

            // 删除频道
            $stmt = $this->db->prepare("DELETE FROM channels WHERE id = :id");
            $result = $stmt->execute([':id' => $id]);

            if ($result && $groupId) {
                // 检查分组是否还有其他频道
                $this->deleteEmptyGroup($groupId);
            }

            // 记录日志
            if ($result && $channel) {
                $logger = new Log();
                $logger->add(
                    Log::TYPE_DELETE,
                    '删除频道',
                    ['source_url' => $channel['source_url']],
                    $id,
                    $channel['name'],
                    $channel['group_id'],
                    $channel['group_name']
                );
            }

            $this->db->commit();
            return ['success' => $result, 'message' => $result ? '删除成功' : '删除失败'];
        } catch (\PDOException $e) {
            $this->db->rollBack();
            return ['success' => false, 'message' => '删除失败：' . $e->getMessage()];
        }
    }

    public function deleteMultiple($ids)
    {
        try {
            $this->db->beginTransaction();

            // 获取这些频道所属的分组ID
            $placeholders = str_repeat('?,', count($ids) - 1) . '?';
            $stmt = $this->db->prepare("SELECT DISTINCT group_id FROM channels WHERE id IN ($placeholders)");
            $stmt->execute($ids);
            $groupIds = $stmt->fetchAll(\PDO::FETCH_COLUMN);

            // 删除频道
            $stmt = $this->db->prepare("DELETE FROM channels WHERE id IN ($placeholders)");
            $result = $stmt->execute($ids);

            if ($result) {
                // 检查每个分组是否还有其他频道
                foreach ($groupIds as $groupId) {
                    if ($groupId) {
                        $this->deleteEmptyGroup($groupId);
                    }
                }
            }

            $this->db->commit();
            return ['success' => $result, 'message' => $result ? '删除成功' : '删除失败'];
        } catch (\PDOException $e) {
            $this->db->rollBack();
            return ['success' => false, 'message' => '删除失败：' . $e->getMessage()];
        }
    }

    public function deleteAll()
    {
        try {
            $this->db->beginTransaction();

            // 记录删除前的频道数量
            $stmt = $this->db->query("SELECT COUNT(*) FROM channels");
            $channelCount = $stmt->fetchColumn();

            // 删除所有频道
            $stmt = $this->db->prepare("DELETE FROM channels");
            $result = $stmt->execute();

            if ($result) {
                // 删除所有分组
                $stmt = $this->db->prepare("DELETE FROM channel_groups");
                $stmt->execute();

                // 记录日志
                $logger = new Log();
                $logger->add(
                    Log::TYPE_CLEAR,
                    '清空频道列表',
                    ['total_deleted' => $channelCount]
                );
            }

            $this->db->commit();
            return ['success' => $result, 'message' => $result ? '删除成功' : '删除失败'];
        } catch (\PDOException $e) {
            $this->db->rollBack();
            return ['success' => false, 'message' => '删除失败：' . $e->getMessage()];
        }
    }

    private function deleteEmptyGroup($groupId)
    {
        // 检查分组是否还有其他频道
        $stmt = $this->db->prepare("SELECT COUNT(*) FROM channels WHERE group_id = ?");
        $stmt->execute([$groupId]);
        $count = $stmt->fetchColumn();

        // 如果分组没有频道了，删除分组
        if ($count == 0) {
            $stmt = $this->db->prepare("DELETE FROM channel_groups WHERE id = ?");
            $stmt->execute([$groupId]);
        }
    }

    public function createChannel($data)
    {
        try {
            // 检查表结构
            $this->ensureTableStructure();

            // 检查源地址是否已存在
            $query = "SELECT id FROM channels WHERE source_url = :source_url";
            $stmt = $this->db->prepare($query);
            $stmt->execute([':source_url' => $data['source_url']]);
            if ($stmt->fetch()) {
                return ['success' => false, 'message' => '源地址已存在'];
            }

            $query = "INSERT INTO channels (name, source_url, proxy_url, group_id, status, created_at, updated_at) 
                     VALUES (:name, :source_url, :proxy_url, :group_id, :status, NOW(), NOW())";
            
            $stmt = $this->db->prepare($query);
            $result = $stmt->execute([
                ':name' => $data['name'],
                ':source_url' => $data['source_url'],
                ':proxy_url' => $data['proxy_url'],
                ':group_id' => $data['group_id'],
                ':status' => $data['status']
            ]);

            if ($result) {
                $channelId = $this->db->lastInsertId();
                
                // 记录日志
                $logger = new Log();
                $logger->add(
                    Log::TYPE_CREATE,
                    '创建频道',
                    $data,
                    $channelId,
                    $data['name'],
                    $data['group_id'],
                    null
                );
                
                return ['success' => true, 'id' => $channelId];
            } else {
                return ['success' => false, 'message' => '添加频道失败'];
            }
        } catch (\PDOException $e) {
            return ['success' => false, 'message' => '数据库错误：' . $e->getMessage()];
        }
    }

    private function ensureTableStructure()
    {
        try {
            // 首先创建表（如果不存在）
            $createTableQuery = "CREATE TABLE IF NOT EXISTS channels (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                source_url TEXT NOT NULL,
                proxy_url VARCHAR(255),
                group_id INT,
                status TINYINT(1) DEFAULT 1,
                latency INT DEFAULT 0,
                checked_at DATETIME,
                error_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_group_id (group_id),
                INDEX idx_status (status),
                INDEX idx_checked_at (checked_at)
            )";
            $this->db->exec($createTableQuery);
            
            // 检查并更新列定义
            $columns = [
                'status' => 'TINYINT(1) DEFAULT 1',
                'latency' => 'INT DEFAULT 0',
                'checked_at' => 'DATETIME',
                'error_count' => 'INT DEFAULT 0',
                'proxy_url' => 'VARCHAR(255)'
            ];

            foreach ($columns as $column => $definition) {
                $this->ensureColumn('channels', $column, $definition);
            }
        } catch (\PDOException $e) {
            error_log("Error in ensureTableStructure: " . $e->getMessage());
        }
    }

    private function ensureColumn($table, $column, $definition)
    {
        try {
            // 使用 INFORMATION_SCHEMA 检查列是否存在
            $query = "SELECT COLUMN_NAME 
                     FROM INFORMATION_SCHEMA.COLUMNS 
                     WHERE TABLE_SCHEMA = DATABASE() 
                     AND TABLE_NAME = ? 
                     AND COLUMN_NAME = ?";
            
            $stmt = $this->db->prepare($query);
            $stmt->execute([$table, $column]);
            
            if ($stmt->rowCount() === 0) {
                // 列不存在，添加它
                $query = "ALTER TABLE `{$table}` ADD COLUMN `{$column}` {$definition}";
                $this->db->exec($query);
            }
        } catch (\PDOException $e) {
            error_log("Error ensuring column {$column}: " . $e->getMessage());
        }
    }

    private function columnExists($table, $column)
    {
        try {
            $stmt = $this->db->prepare("SHOW COLUMNS FROM {$table} LIKE ?");
            $stmt->execute([$column]);
            return $stmt->rowCount() > 0;
        } catch (\PDOException $e) {
            error_log("Error checking column {$column}: " . $e->getMessage());
            return false;
        }
    }

    private function getColumnType($table, $column)
    {
        try {
            $query = "SHOW COLUMNS FROM {$table} WHERE Field = :column";
            $stmt = $this->db->prepare($query);
            $stmt->execute([':column' => $column]);
            $result = $stmt->fetch(\PDO::FETCH_ASSOC);
            return $result ? $result['Type'] : null;
        } catch (\PDOException $e) {
            return null;
        }
    }

    private function shouldModifyColumnType($currentType, $requiredType)
    {
        // 标准化类型字符串以便比较
        $currentType = strtolower(preg_replace('/\s+/', ' ', trim($currentType)));
        $requiredType = strtolower(preg_replace('/\s+/', ' ', trim($requiredType)));

        // 特殊处理某些类型的对比
        if ($currentType === 'text' && $requiredType === 'text') {
            return false; // TEXT 类型保持不变
        }

        // 处理带有默认值的类型
        $requiredBase = preg_replace('/\s+default\s+.*$/i', '', $requiredType);
        $currentBase = preg_replace('/\s+default\s+.*$/i', '', $currentType);

        // 如果基本类型相同，不需要修改
        if ($currentBase === $requiredBase) {
            return false;
        }

        return true;
    }

    public function importFromFile($file)
    {
        try {
            $extension = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
            $content = file_get_contents($file['tmp_name']);

            if ($extension === 'txt') {
                return $this->importFromTxt($content);
            } else if ($extension === 'm3u' || $extension === 'm3u8') {
                return $this->importFromM3u($content);
            }

            return ['success' => false, 'message' => '不支持的文件格式'];
        } catch (\Exception $e) {
            return ['success' => false, 'message' => '导入失败：' . $e->getMessage()];
        }
    }

    public function importFromTxt($content)
    {
        $lines = explode("\n", $content);
        $currentGroup = null;
        $currentGroupId = null;
        $imported = 0;
        $errors = 0;
        $duplicates = 0;
        $importedChannels = [];

        foreach ($lines as $line) {
            $line = trim($line);
            if (empty($line)) continue;

            $parts = explode(',', $line);
            if (count($parts) !== 2) continue;

            if (strpos($parts[1], '#genre#') !== false) {
                // 这是一个分组行
                $groupName = trim($parts[0]);
                $currentGroupId = $this->ensureGroup($groupName);
                $currentGroup = $groupName;
            } else {
                // 这是一个频道行
                $channelName = trim($parts[0]);
                $channelUrl = trim($parts[1]);
                
                // 处理URL中的$符号
                if (($pos = strpos($channelUrl, '$')) !== false) {
                    $channelUrl = substr($channelUrl, 0, $pos);
                }
                $channelUrl = trim($channelUrl); // 再次去除可能的尾部空格

                if (empty($channelUrl)) continue; // 如果处理后URL为空则跳过

                $result = $this->createChannel([
                    'name' => $channelName,
                    'source_url' => $channelUrl,
                    'proxy_url' => $this->generateProxyUrl($channelUrl),
                    'group_id' => $currentGroupId,
                    'status' => 'inactive'
                ]);

                if ($result['success']) {
                    $imported++;
                    $importedChannels[] = [
                        'id' => $result['id'],
                        'name' => $channelName,
                        'source_url' => $channelUrl,
                        'group_id' => $currentGroupId,
                        'group_name' => $currentGroup
                    ];
                } else if (strpos($result['message'], '源地址已存在') !== false) {
                    $duplicates++;
                } else {
                    $errors++;
                }
            }
        }

        // 记录导入日志
        $logger = new Log();
        $logger->add(
            Log::TYPE_IMPORT,
            '导入TXT频道列表',
            [
                'total' => count($lines),
                'imported' => $imported,
                'duplicates' => $duplicates,
                'errors' => $errors,
                'channels' => $importedChannels
            ]
        );

        return [
            'success' => true,
            'message' => "导入完成：成功 {$imported} 个，重复 {$duplicates} 个，失败 {$errors} 个"
        ];
    }

    public function importFromM3u($content)
    {
        $lines = explode("\n", $content);
        $currentGroup = null;
        $currentGroupId = null;
        $imported = 0;
        $errors = 0;
        $duplicates = 0;
        $channelName = null;
        $importedChannels = [];

        foreach ($lines as $line) {
            $line = trim($line);
            if (empty($line)) continue;

            if (strpos($line, '#EXTINF:') === 0) {
                // 解析频道信息
                preg_match('/group-title="([^"]*)"/', $line, $groupMatches);
                preg_match('/,(.*)$/', $line, $nameMatches);

                if (!empty($groupMatches[1])) {
                    $currentGroup = $groupMatches[1];
                    $currentGroupId = $this->ensureGroup($currentGroup);
                }

                $channelName = !empty($nameMatches[1]) ? trim($nameMatches[1]) : '未命名频道';
            } else if (strpos($line, '#') !== 0) {
                // 这是URL行
                $channelUrl = trim($line);
                
                // 处理URL中的$符号
                if (($pos = strpos($channelUrl, '$')) !== false) {
                    $channelUrl = substr($channelUrl, 0, $pos);
                }
                $channelUrl = trim($channelUrl); // 再次去除可能的尾部空格

                if (!empty($channelUrl)) {
                    $result = $this->createChannel([
                        'name' => $channelName,
                        'source_url' => $channelUrl,
                        'proxy_url' => $this->generateProxyUrl($channelUrl),
                        'group_id' => $currentGroupId,
                        'status' => 'inactive'
                    ]);

                    if ($result['success']) {
                        $imported++;
                        $importedChannels[] = [
                            'id' => $result['id'],
                            'name' => $channelName,
                            'source_url' => $channelUrl,
                            'group_id' => $currentGroupId,
                            'group_name' => $currentGroup
                        ];
                    } else if (strpos($result['message'], '源地址已存在') !== false) {
                        $duplicates++;
                    } else {
                        $errors++;
                    }
                }
            }
        }

        // 记录导入日志
        $logger = new Log();
        $logger->add(
            Log::TYPE_IMPORT,
            '导入M3U频道列表',
            [
                'total' => count($lines),
                'imported' => $imported,
                'duplicates' => $duplicates,
                'errors' => $errors,
                'channels' => $importedChannels
            ]
        );

        return [
            'success' => true,
            'message' => "导入完成：成功 {$imported} 个，重复 {$duplicates} 个，失败 {$errors} 个"
        ];
    }

    private function ensureGroup($groupName)
    {
        if (empty($groupName)) return null;

        try {
            // 检查分组是否存在
            $query = "SELECT id FROM channel_groups WHERE name = :name";
            $stmt = $this->db->prepare($query);
            $stmt->execute([':name' => $groupName]);
            $result = $stmt->fetch(\PDO::FETCH_ASSOC);

            if ($result) {
                return $result['id'];
            }

            // 创建新分组
            $query = "INSERT INTO channel_groups (name, created_at, updated_at) VALUES (:name, NOW(), NOW())";
            $stmt = $this->db->prepare($query);
            $stmt->execute([':name' => $groupName]);

            return $this->db->lastInsertId();
        } catch (\PDOException $e) {
            return null;
        }
    }

    private function generateProxyUrl($sourceUrl)
    {
        // 生成唯一的代理路径
        $uniqueId = uniqid('ch_', true);
        // 统一使用 stream.m3u8 作为结尾
        return '/proxy/' . $uniqueId . '/stream.m3u8';
    }

    public function getChannel($id)
    {
        try {
            $query = "SELECT c.*, g.name as group_name 
                     FROM channels c 
                     LEFT JOIN channel_groups g ON c.group_id = g.id 
                     WHERE c.id = :id";
            $stmt = $this->db->prepare($query);
            $stmt->execute([':id' => $id]);
            return $stmt->fetch(\PDO::FETCH_ASSOC);
        } catch (\PDOException $e) {
            return null;
        }
    }

    public function updateChannel($id, $data)
    {
        try {
            // 获取更新前的频道信息用于日志记录
            $oldChannel = $this->getChannel($id);

            // 检查源地址是否已存在（排除当前频道）
            $query = "SELECT id FROM channels WHERE source_url = :source_url AND id != :id";
            $stmt = $this->db->prepare($query);
            $stmt->execute([
                ':source_url' => $data['source_url'],
                ':id' => $id
            ]);
            if ($stmt->fetch()) {
                return ['success' => false, 'message' => '源地址已存在'];
            }

            $query = "UPDATE channels 
                     SET name = :name, 
                         source_url = :source_url, 
                         group_id = :group_id,
                         updated_at = NOW()
                     WHERE id = :id";
            
            $stmt = $this->db->prepare($query);
            $result = $stmt->execute([
                ':id' => $id,
                ':name' => $data['name'],
                ':source_url' => $data['source_url'],
                ':group_id' => $data['group_id'] ?: null
            ]);

            if ($result) {
                // 获取更新后的频道信息
                $newChannel = $this->getChannel($id);
                
                // 记录日志
                $logger = new Log();
                $logger->add(
                    Log::TYPE_EDIT,
                    '编辑频道',
                    [
                        'old' => $oldChannel,
                        'new' => $newChannel,
                        'changes' => array_diff_assoc($data, [
                            'name' => $oldChannel['name'],
                            'source_url' => $oldChannel['source_url'],
                            'group_id' => $oldChannel['group_id']
                        ])
                    ],
                    $id,
                    $data['name'],
                    $data['group_id'],
                    $newChannel['group_name']
                );
            }

            return [
                'success' => $result,
                'message' => $result ? '更新成功' : '更新失败'
            ];
        } catch (\PDOException $e) {
            return ['success' => false, 'message' => '数据库错误：' . $e->getMessage()];
        }
    }

    public function getConnection()
    {
        return $this->db;
    }

    public function getGroupStats()
    {
        try {
            $query = "SELECT 
                     COALESCE(g.name, '未分组') as name,
                     COUNT(*) as total_channels,
                     SUM(CASE WHEN c.status = 'active' THEN 1 ELSE 0 END) as active_channels,
                     SUM(CASE WHEN c.status = 'error' THEN 1 ELSE 0 END) as error_channels,
                     AVG(c.latency) as avg_latency
                     FROM channels c
                     LEFT JOIN channel_groups g ON c.group_id = g.id
                     GROUP BY g.id, g.name WITH ROLLUP
                     HAVING name IS NOT NULL
                     ORDER BY total_channels DESC";
            
            $stmt = $this->db->query($query);
            return $stmt->fetchAll(\PDO::FETCH_ASSOC);
        } catch (\PDOException $e) {
            error_log("Error getting group stats: " . $e->getMessage());
            return [];
        }
    }

    public function getPerformanceStats()
    {
        try {
            // 获取最近24小时的性能数据，每小时一个点
            $query = "SELECT 
                     DATE_FORMAT(checked_at, '%Y-%m-%d %H:00:00') as hour,
                     COUNT(*) as total_checks,
                     AVG(latency) as avg_latency,
                     SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as success_count,
                     SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                     FROM channels
                     WHERE checked_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                     GROUP BY hour
                     ORDER BY hour ASC";
            
            $stmt = $this->db->query($query);
            $data = $stmt->fetchAll(\PDO::FETCH_ASSOC);
            
            // 确保24小时的数据都存在，没有数据的时间点填充0
            $result = [];
            $now = new \DateTime();
            $start = new \DateTime('-24 hours');
            
            while ($start <= $now) {
                $hour = $start->format('Y-m-d H:00:00');
                $found = false;
                
                foreach ($data as $row) {
                    if ($row['hour'] === $hour) {
                        $result[] = [
                            'hour' => $hour,
                            'total_checks' => (int)$row['total_checks'],
                            'avg_latency' => round((float)$row['avg_latency'], 2),
                            'success_rate' => $row['total_checks'] > 0 
                                ? round(($row['success_count'] / $row['total_checks']) * 100, 2)
                                : 0
                        ];
                        $found = true;
                        break;
                    }
                }
                
                if (!$found) {
                    $result[] = [
                        'hour' => $hour,
                        'total_checks' => 0,
                        'avg_latency' => 0,
                        'success_rate' => 0
                    ];
                }
                
                $start->modify('+1 hour');
            }
            
            return $result;
        } catch (\PDOException $e) {
            error_log("Error getting performance stats: " . $e->getMessage());
            return [];
        }
    }

    public function getRecentErrors()
    {
        try {
            $query = "SELECT c.*, g.name as group_name
                     FROM channels c
                     LEFT JOIN channel_groups g ON c.group_id = g.id
                     WHERE c.status = 3
                     ORDER BY c.checked_at DESC
                     LIMIT 10";
            
            $stmt = $this->db->query($query);
            return $stmt->fetchAll(\PDO::FETCH_ASSOC);
        } catch (\PDOException $e) {
            error_log("Error getting recent errors: " . $e->getMessage());
            return [];
        }
    }

    public function getErrorLogs($page = 1, $perPage = 50, $type = null, $startDate = null, $endDate = null)
    {
        try {
            $offset = ($page - 1) * $perPage;
            $where = [];
            $params = [];

            if ($type) {
                $where[] = "type = ?";
                $params[] = $type;
            }

            if ($startDate) {
                $where[] = "created_at >= ?";
                $params[] = $startDate;
            }

            if ($endDate) {
                $where[] = "created_at <= ?";
                $params[] = $endDate;
            }

            $whereClause = !empty($where) ? "WHERE " . implode(" AND ", $where) : "";

            // 获取总数
            $countQuery = "SELECT COUNT(*) FROM error_logs $whereClause";
            $stmt = $this->db->prepare($countQuery);
            $stmt->execute($params);
            $total = $stmt->fetchColumn();

            // 获取日志列表
            $query = "SELECT * FROM error_logs $whereClause 
                     ORDER BY created_at DESC LIMIT ? OFFSET ?";
            $params[] = $perPage;
            $params[] = $offset;

            $stmt = $this->db->prepare($query);
            $stmt->execute($params);
            $logs = $stmt->fetchAll(\PDO::FETCH_ASSOC);

            return [
                'logs' => $logs,
                'total' => $total,
                'totalPages' => ceil($total / $perPage)
            ];
        } catch (\PDOException $e) {
            error_log("Error getting error logs: " . $e->getMessage());
            return ['logs' => [], 'total' => 0, 'totalPages' => 0];
        }
    }
}