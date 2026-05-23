<?php

class InstallController
{
    private $installer;
    private $currentStep;
    private $totalSteps = 5;

    public function __construct()
    {
        // 检查是否已安装
        if (file_exists(BASE_PATH . '/storage/installed.lock') && !isset($_GET['force'])) {
            die('系统已安装。如需重新安装，请删除 storage/installed.lock 文件或在URL中添加 force 参数。');
        }

        $this->installer = new Installer();
        $this->currentStep = isset($_GET['step']) ? (int)$_GET['step'] : 1;
    }

    public function run()
    {
        try {
            switch ($this->currentStep) {
                case 1:
                    return $this->handleStep1();
                case 2:
                    return $this->handleStep2();
                case 3:
                    return $this->handleStep3();
                case 4:
                    return $this->handleStep4();
                case 5:
                    return $this->handleStep5();
                default:
                    header('Location: install.php?step=1');
                    exit;
            }
        } catch (Exception $e) {
            $this->showError($e->getMessage());
        }
    }

    private function handleStep1()
    {
        // 处理环境检查
        if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['check'])) {
            header('Content-Type: application/json');
            echo json_encode($this->installer->checkEnvironment());
            exit;
        }

        // 显示环境检查页面
        $results = $this->installer->checkEnvironment();
        require __DIR__ . '/../../public/install/templates/step1.php';
    }

    private function handleStep2()
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $action = $_GET['action'] ?? '';
            
            header('Content-Type: application/json');
            
            try {
                switch ($action) {
                    case 'test':
                        echo json_encode($this->installer->testDatabaseConnection($_POST));
                        break;
                        
                    case 'configure':
                        $result = $this->installer->configureDatabase($_POST);
                        if (!$result['success']) {
                            error_log('Database configuration error: ' . $result['message']);
                        }
                        echo json_encode($result);
                        break;
                        
                    default:
                        echo json_encode([
                            'success' => false,
                            'message' => '无效的操作'
                        ]);
                }
            } catch (Exception $e) {
                error_log('Installation error: ' . $e->getMessage());
                echo json_encode([
                    'success' => false,
                    'message' => '安装过程出错: ' . $e->getMessage()
                ]);
            }
            exit;
        }

        // 显示数据库配置页面
        require __DIR__ . '/../../public/install/templates/step2.php';
    }

    private function handleStep3()
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $action = $_GET['action'] ?? '';
            
            header('Content-Type: application/json');
            
            try {
                switch ($action) {
                    case 'test':
                        echo json_encode($this->installer->testRedisConnection($_POST));
                        break;
                        
                    case 'configure':
                        echo json_encode($this->installer->configureRedis($_POST));
                        break;
                        
                    default:
                        echo json_encode([
                            'success' => false,
                            'message' => '无效的操作'
                        ]);
                }
            } catch (Exception $e) {
                echo json_encode([
                    'success' => false,
                    'message' => '操作失败: ' . $e->getMessage()
                ]);
            }
            exit;
        }

        // 显示Redis配置页面
        require __DIR__ . '/../../public/install/templates/step3.php';
    }

    private function handleStep4()
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            header('Content-Type: application/json');
            echo json_encode($this->installer->configureAdmin($_POST));
            exit;
        }

        // 显示管理员配置页面
        require __DIR__ . '/../../public/install/templates/step4.php';
    }

    private function handleStep5()
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            header('Content-Type: application/json');
            echo json_encode($this->installer->finishInstallation());
            exit;
        }

        // 显示完成安装页面
        require __DIR__ . '/../../public/install/templates/step5.php';
    }

    private function showError($message)
    {
        header('Content-Type: application/json');
        echo json_encode([
            'success' => false,
            'message' => $message
        ]);
        exit;
    }

    public function configureDatabase($data)
    {
        header('Content-Type: application/json');
        echo json_encode($this->installer->configureDatabase($data));
        exit;
    }
    public function testDatabaseConnection()
    {
        header('Content-Type: application/json');
        echo json_encode($this->installer->testDatabaseConnection($_POST));
        exit;
    }
    
}