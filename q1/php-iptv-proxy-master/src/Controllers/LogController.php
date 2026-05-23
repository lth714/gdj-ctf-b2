<?php
namespace App\Controllers;

use App\Models\Log;

class LogController
{
    private $log;

    public function __construct()
    {
        $this->log = new Log();
    }

    public function index()
    {
        $currentPage = 'logs';
        require __DIR__ . '/../views/admin/logs/index.php';
    }

    public function getLogs()
    {
        $page = isset($_GET['page']) ? (int)$_GET['page'] : 1;
        $type = isset($_GET['type']) ? $_GET['type'] : null;
        
        $startDate = !empty($_GET['start_date']) ? $_GET['start_date'] . ' 00:00:00' : null;
        $endDate = !empty($_GET['end_date']) ? $_GET['end_date'] . ' 23:59:59' : null;
        
        $result = $this->log->getLogs($page, 50, $type, $startDate, $endDate, 'id', 'DESC');
        
        header('Content-Type: application/json');
        echo json_encode($result);
    }

    public function clear()
    {
        try {
            $this->log->clearAll();
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