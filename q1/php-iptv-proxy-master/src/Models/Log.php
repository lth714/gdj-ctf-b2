<?php
namespace App\Models;

use App\Core\Database;

class Log
{
    private $db;
    
    // 定义日志类型常量
    const TYPE_IMPORT = 'import';
    const TYPE_DELETE = 'delete';
    const TYPE_EDIT = 'edit';
    const TYPE_CREATE = 'create';
    const TYPE_CLEAR = 'clear';

    public function __construct()
    {
        $this->db = Database::getInstance()->getConnection();
        $this->ensureTableStructure();
    }

    private function ensureTableStructure()
    {
        try {
            $query = "CREATE TABLE IF NOT EXISTS channel_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                type VARCHAR(20) NOT NULL,
                action VARCHAR(255) NOT NULL,
                channel_id INT,
                channel_name VARCHAR(255),
                group_id INT,
                group_name VARCHAR(255),
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_type (type),
                INDEX idx_channel_id (channel_id),
                INDEX idx_created_at (created_at)
            )";
            $this->db->exec($query);
        } catch (\PDOException $e) {
            error_log("Error creating logs table: " . $e->getMessage());
        }
    }

    public function add($type, $action, $details = [], $channelId = null, $channelName = null, $groupId = null, $groupName = null)
    {
        try {
            $query = "INSERT INTO channel_logs (type, action, channel_id, channel_name, group_id, group_name, details) 
                     VALUES (:type, :action, :channel_id, :channel_name, :group_id, :group_name, :details)";
            
            $stmt = $this->db->prepare($query);
            $stmt->execute([
                ':type' => $type,
                ':action' => $action,
                ':channel_id' => $channelId,
                ':channel_name' => $channelName,
                ':group_id' => $groupId,
                ':group_name' => $groupName,
                ':details' => json_encode($details, JSON_UNESCAPED_UNICODE)
            ]);
            
            return true;
        } catch (\PDOException $e) {
            error_log("Error adding log: " . $e->getMessage());
            return false;
        }
    }

    public function getLogs($page = 1, $perPage = 50, $type = null, $startDate = null, $endDate = null)
    {
        try {
            $where = [];
            $params = [];

            if ($type) {
                $where[] = "type = :type";
                $params[':type'] = $type;
            }

            if ($startDate) {
                $where[] = "created_at >= :start_date";
                $params[':start_date'] = $startDate;
            }

            if ($endDate) {
                $where[] = "created_at <= :end_date";
                $params[':end_date'] = $endDate;
            }

            $whereClause = !empty($where) ? "WHERE " . implode(" AND ", $where) : "";
            
            // 获取总数
            $countQuery = "SELECT COUNT(*) FROM channel_logs {$whereClause}";
            $stmt = $this->db->prepare($countQuery);
            $stmt->execute($params);
            $total = $stmt->fetchColumn();

            // 计算偏移量
            $offset = ($page - 1) * $perPage;

            // 获取日志列表，按 ID 降序排序
            $query = "SELECT * FROM channel_logs {$whereClause} 
                     ORDER BY id DESC 
                     LIMIT :limit OFFSET :offset";

            $stmt = $this->db->prepare($query);
            
            // 绑定分页参数
            $stmt->bindValue(':limit', $perPage, \PDO::PARAM_INT);
            $stmt->bindValue(':offset', $offset, \PDO::PARAM_INT);
            
            // 绑定其他参数
            foreach ($params as $key => $value) {
                $stmt->bindValue($key, $value);
            }

            $stmt->execute();
            $logs = $stmt->fetchAll(\PDO::FETCH_ASSOC);

            return [
                'logs' => $logs,
                'total' => $total,
                'totalPages' => ceil($total / $perPage)
            ];
        } catch (\PDOException $e) {
            error_log("Error getting logs: " . $e->getMessage());
            return ['logs' => [], 'total' => 0, 'totalPages' => 0];
        }
    }

    public function clearAll()
    {
        try {
            $query = "TRUNCATE TABLE channel_logs";
            $this->db->exec($query);
            return true;
        } catch (\PDOException $e) {
            error_log("Error clearing channel logs: " . $e->getMessage());
            throw new \Exception("清空日志失败: " . $e->getMessage());
        }
    }
} 