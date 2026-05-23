<?php
namespace App\Controllers;

use App\Models\ErrorLog;

class ErrorLogController
{
    private $errorLogModel;

    public function __construct()
    {
        $this->errorLogModel = new ErrorLog();
    }

    public function index()
    {
        $currentPage = 'error_logs';
        // 使用模型获取错误日志总数
        $errorCount = $this->errorLogModel->getCount();
        require __DIR__ . '/../views/admin/error_logs/index.php';
    }

    public function getLogs()
    {
        try {
            $page = $_GET['page'] ?? 1;
            $perPage = $_GET['per_page'] ?? 50;
            $type = $_GET['type'] ?? null;
            $startDate = $_GET['start_date'] ?? null;
            $endDate = $_GET['end_date'] ?? null;

            $logs = $this->errorLogModel->getLogs($page, $perPage, $type, $startDate, $endDate);
            
            header('Content-Type: application/json');
            echo json_encode([
                'success' => true,
                'data' => $logs
            ]);
            exit;
        } catch (\Exception $e) {
            header('Content-Type: application/json');
            echo json_encode([
                'success' => false,
                'message' => $e->getMessage()
            ]);
            exit;
        }
    }

    public function addLog($channelId, $channelName, $type, $message, $details = [])
    {
        try {
            $this->errorLogModel->add($channelId, $channelName, $type, $message, $details);
            return true;
        } catch (\Exception $e) {
            error_log("Error adding error log: " . $e->getMessage());
            return false;
        }
    }

    public function clear()
    {
        try {
            $this->errorLogModel->clearAll();
            echo json_encode([
                'success' => true,
                'message' => '日志已清空'
            ]);
        } catch (\Exception $e) {
            echo json_encode([
                'success' => false,
                'message' => $e->getMessage()
            ]);
        }
    }

} 