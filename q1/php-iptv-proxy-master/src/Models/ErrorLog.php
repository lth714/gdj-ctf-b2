<?php
namespace App\Models;

use App\Core\Database;

class ErrorLog
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance()->getConnection();
        $this->ensureTableStructure();
    }

    private function ensureTableStructure()
    {
        try {
            $query = "CREATE TABLE IF NOT EXISTS error_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                level VARCHAR(20) NOT NULL,
                message TEXT NOT NULL,
                file VARCHAR(255),
                line INT,
                trace TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_level (level),
                INDEX idx_created_at (created_at)
            )";
            $this->db->exec($query);
        } catch (\PDOException $e) {
            error_log("Error creating error_logs table: " . $e->getMessage());
        }
    }

    public function add($data)
    {
        try {
            $query = "INSERT INTO error_logs (level, message, file, line, trace) 
                     VALUES (:level, :message, :file, :line, :trace)";
            
            $stmt = $this->db->prepare($query);
            $stmt->execute([
                ':level' => $data['level'],
                ':message' => $data['message'],
                ':file' => $data['file'],
                ':line' => $data['line'],
                ':trace' => $data['trace']
            ]);
            
            return true;
        } catch (\PDOException $e) {
            error_log("Error adding error log: " . $e->getMessage());
            return false;
        }
    }

    public function getLogs($page = 1, $perPage = 50, $type = null, $startDate = null, $endDate = null)
    {
        try {
            $where = [];
            $params = [];

            if ($type) {
                $where[] = "level = :type";
                $params[':type'] = $type;
            }

            if ($startDate) {
                $where[] = "created_at >= :start_date";
                $params[':start_date'] = $startDate . ' 00:00:00';
            }

            if ($endDate) {
                $where[] = "created_at <= :end_date";
                $params[':end_date'] = $endDate . ' 23:59:59';
            }

            $whereClause = !empty($where) ? "WHERE " . implode(" AND ", $where) : "";
            
            // 获取总数
            $countQuery = "SELECT COUNT(*) FROM error_logs {$whereClause}";
            $stmt = $this->db->prepare($countQuery);
            $stmt->execute($params);
            $total = $stmt->fetchColumn();

            // 计算偏移量
            $offset = ($page - 1) * $perPage;

            // 获取日志列表
            $query = "SELECT * FROM error_logs {$whereClause} 
                     ORDER BY created_at DESC 
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
            error_log("Error getting error logs: " . $e->getMessage());
            return ['logs' => [], 'total' => 0, 'totalPages' => 0];
        }
    }

    public function clearOldLogs($days = 30)
    {
        try {
            $query = "DELETE FROM error_logs WHERE created_at < DATE_SUB(NOW(), INTERVAL :days DAY)";
            $stmt = $this->db->prepare($query);
            $stmt->execute([':days' => $days]);
            return true;
        } catch (\PDOException $e) {
            error_log("Error clearing old error logs: " . $e->getMessage());
            return false;
        }
    }

    public function clearAll()
    {
        try {
            $query = "TRUNCATE TABLE error_logs";
            $this->db->exec($query);
            return true;
        } catch (\PDOException $e) {
            error_log("Error clearing error logs: " . $e->getMessage());
            throw new \Exception("清空日志失败: " . $e->getMessage());
        }
    }

    // 添加获取总数的方法
    public function getCount()
    {
        try {
            $stmt = $this->db->query("SELECT COUNT(*) as count FROM error_logs");
            return $stmt->fetch(\PDO::FETCH_ASSOC)['count'];
        } catch (\Exception $e) {
            return 0;
        }
    }
} 