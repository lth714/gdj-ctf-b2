<?php

namespace App\Controllers;

class DiagController
{
    private $basePath;

    public function __construct()
    {
        $this->basePath = dirname(__DIR__, 2);
    }

    public function index()
    {
        $currentPage = 'diag';
        require $this->basePath . '/src/views/admin/diag/index.php';
    }

    public function execute()
    {
        header('Content-Type: application/json');

        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            http_response_code(405);
            echo json_encode(['success' => false, 'error' => 'Method Not Allowed']);
            return;
        }

        $target = $_POST['target'] ?? '';

        if (empty($target)) {
            echo json_encode(['success' => false, 'error' => '请输入检测目标地址']);
            return;
        }

        $target = trim($target);

        // URL解码（支持 %0a 换行等编码字符）
        $target = urldecode($target);

        // 安全检查：过滤危险字符
        $blacklist = ['|', ';', '&', '$', '`'];
        foreach ($blacklist as $char) {
            if (strpos($target, $char) !== false) {
                echo json_encode(['success' => false, 'error' => '检测目标包含非法字符: ' . $char]);
                return;
            }
        }

        // 执行网络诊断
        $cmd = 'ping -c 3 ' . $target . ' 2>&1';
        $output = shell_exec($cmd);

        echo json_encode([
            'success' => true,
            'command' => $cmd,
            'output' => $output ?: '(无输出)'
        ]);
    }
}
