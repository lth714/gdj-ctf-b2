<?php
session_start();
require __DIR__ . '/../vendor/autoload.php';

// 检查是否已安装
if (!file_exists(__DIR__ . '/../config/config.php') && !str_contains($_SERVER['REQUEST_URI'], '/install')) {
    header('Location: /install.php');
    exit;
}

// 获取当前路径
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// 不需要登录检查的路径
$publicPaths = [
    '/install',
    '/install.php',
    '/login',
    '/login.php',
    '/auth/login',
    '/reset-password',
    '/auth/reset-password'
];

// 检查是否需要登录验证
$needsAuth = true;
foreach ($publicPaths as $publicPath) {
    if (str_starts_with($path, $publicPath)) {
        $needsAuth = false;
        break;
    }
}

// 如果需要登录验证，则检查登录状态
if ($needsAuth) {
    \App\Controllers\AuthController::checkLogin();
}
// 路由处理
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$method = $_SERVER['REQUEST_METHOD'];

try {
    switch ($path) {
        case '/':
            $controller = new \App\Controllers\IndexController();
            $controller->index();
            break;

        // 代理服务器相关路由
        case '/admin/proxy/status':
            $controller = new \App\Controllers\ProxyController();
            $controller->status();
            break;

        case '/admin/proxy/start':
            if ($method === 'POST') {
                $controller = new \App\Controllers\ProxyController();
                $controller->start();
            } else {
                http_response_code(405);
                echo 'Method Not Allowed';
            }
            break;

        case '/admin/proxy/stop':
            if ($method === 'POST') {
                $controller = new \App\Controllers\ProxyController();
                $controller->stop();
            } else {
                http_response_code(405);
                echo 'Method Not Allowed';
            }
            break;

        case '/admin/proxy/connection-stats':
            $controller = new \App\Controllers\ProxyController();
            $controller->getConnectionStats();
            break;

        case '/admin/channels':
            $controller = new \App\Controllers\ChannelController();
            $controller->index();
            break;

        case (preg_match('/^\/admin\/channels\/check\/(\d+)$/', $path, $matches) ? true : false):
            $controller = new \App\Controllers\ChannelController();
            $controller->checkChannel($matches[1]);
            break;

        case '/admin/channels/check-multiple':
            $controller = new \App\Controllers\ChannelController();
            $controller->checkMultiple();
            break;

        case (preg_match('/^\/admin\/channels\/check-progress\/(.+)$/', $path, $matches) ? true : false):
            $controller = new \App\Controllers\ChannelController();
            $controller->checkProgress($matches[1]);
            break;

        case '/admin/channels/check-all':
            $controller = new \App\Controllers\ChannelController();
            $controller->checkAll();
            break;

        case (preg_match('/^\/admin\/channels\/delete\/(\d+)$/', $path, $matches) ? true : false):
            $controller = new \App\Controllers\ChannelController();
            $controller->deleteChannel($matches[1]);
            break;

        case '/admin/channels/delete-multiple':
            $controller = new \App\Controllers\ChannelController();
            $controller->deleteMultiple();
            break;

        case '/admin/channels/delete-all':
            $controller = new \App\Controllers\ChannelController();
            $controller->deleteAll();
            break;

        case '/admin/channels/add':
            $controller = new \App\Controllers\ChannelController();
            $controller->add();
            break;

        case '/admin/channels/create':
            if ($method === 'POST') {
                $controller = new \App\Controllers\ChannelController();
                $controller->create();
            } else {
                http_response_code(405);
                echo 'Method Not Allowed';
            }
            break;

        case '/admin/channels/import':
            $controller = new \App\Controllers\ChannelController();
            if ($method === 'POST') {
                $controller->import();
            } else {
                $controller->showImport();
            }
            break;

        case (preg_match('/^\/admin\/channels\/edit\/(\d+)$/', $path, $matches) ? true : false):
            $controller = new \App\Controllers\ChannelController();
            $controller->edit($matches[1]);
            break;

        case (preg_match('/^\/admin\/channels\/update\/(\d+)$/', $path, $matches) ? true : false):
            if ($method === 'POST') {
                $controller = new \App\Controllers\ChannelController();
                $controller->update($matches[1]);
            } else {
                http_response_code(405);
                echo 'Method Not Allowed';
            }
            break;

        case '/admin/import':
            // 重定向到正确的导入页面
            header('Location: /admin/channels/import');
            exit;
            break;

        case '/admin/settings':
            $controller = new \App\Controllers\SettingsController();
            $controller->index();
            break;

        case '/admin/settings/save':
            if ($method === 'POST') {
                $controller = new \App\Controllers\SettingsController();
                $controller->save();
            } else {
                http_response_code(405);
                echo 'Method Not Allowed';
            }
            break;

        case '/admin/monitor':
            $controller = new \App\Controllers\MonitorController();
            $controller->index();
            break;

        case '/admin/monitor/stats':
            $controller = new \App\Controllers\MonitorController();
            header('Content-Type: application/json');
            echo json_encode($controller->getStats());
            break;

        case '/admin/monitor/logs':
            if ($method === 'GET' && isset($_SERVER['HTTP_X_REQUESTED_WITH'])) {
                $controller = new \App\Controllers\MonitorController();
                header('Content-Type: application/json');
                echo json_encode($controller->getLogs());
            } else {
                $controller = new \App\Controllers\MonitorController();
                $controller->logs();
            }
            break;

        case '/admin/logs':
            $controller = new \App\Controllers\LogController();
            $controller->index();
            break;

        case '/admin/logs/data':
            $controller = new \App\Controllers\LogController();
            $controller->getLogs();
            break;

        case '/admin/logs/clear':
            if ($method === 'POST') {
                $controller = new \App\Controllers\LogController();
                $controller->clear();
            } else {
                http_response_code(405);
                echo 'Method Not Allowed';
            }
            break;

        // 错误日志相关路由
        case '/admin/error-logs':
            $controller = new \App\Controllers\ErrorLogController();
            $controller->index();
            break;

        case '/admin/error-logs/data':
            $controller = new \App\Controllers\ErrorLogController();
            $controller->getLogs();
            break;

        case '/admin/error-logs/clear':
            if ($method === 'POST') {
                $controller = new \App\Controllers\ErrorLogController();
                $controller->clear();
            } else {
                http_response_code(405);
                echo 'Method Not Allowed';
            }
            break;

        // 带宽监控相关路由
        case '/api/bandwidth':
            $controller = new \App\Controllers\Api\BandwidthController();
            $controller->getAll();
            break;
            
        case (preg_match('/^\/api\/bandwidth\/(\d+)$/', $path, $matches) ? true : false):
            $controller = new \App\Controllers\Api\BandwidthController();
            $controller->getOne($matches[1]);
            break;

        case '/admin/proxy/bandwidth-stats':
            $controller = new \App\Controllers\ProxyController();
            $controller->getBandwidthStats();
            break;
        
        // 安装相关路由
        case '/install':
            if (!file_exists(BASE_PATH . '/storage/installed.lock')) {
                $controller = new \App\Install\InstallController();
                $controller->run();
            } else {
                header('Location: /');
            }
            break;
            
        case '/install/check':
            if (!file_exists(BASE_PATH . '/storage/installed.lock')) {
                $controller = new \App\Install\InstallController();
                if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                    $controller->checkEnvironment();
                }
            }
            break;
            
        case '/install/database':
            if (!file_exists(BASE_PATH . '/storage/installed.lock')) {
                $controller = new \App\Install\InstallController();
                if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                    $controller->configureDatabase($_POST);
                }
            }
            break;
            
        case '/install/admin':
            if (!file_exists(BASE_PATH . '/storage/installed.lock')) {
                $controller = new \App\Install\InstallController();
                if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                    $controller->configureAdmin($_POST);
                }
            }
            break;
            
        case '/install/finish':
            if (!file_exists(BASE_PATH . '/storage/installed.lock')) {
                $controller = new \App\Install\InstallController();
                $controller->finish();
            }
            break;
        
        case '/install/database/test':
            if (!file_exists(BASE_PATH . '/storage/installed.lock')) {
                $controller = new \App\Install\InstallController();
                if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                    $controller->testDatabaseConnection();
                }
               }
            break;
            
        case '/install/database/configure':
            if (!file_exists(BASE_PATH . '/storage/installed.lock')) {
                $controller = new \App\Install\InstallController();
                if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                    $controller->configureDatabase($_POST);
                }
            }
            break;

        // 登录相关路由
        case '/login':
        case '/login.php':
            $controller = new \App\Controllers\AuthController();
            $controller->login();
            break;
    
        case '/auth/login':
            if ($method === 'POST') {
                $controller = new \App\Controllers\AuthController();
                $controller->handleLogin();
            } else {
                http_response_code(405);
                echo 'Method Not Allowed';
            }
            break;
    
        case '/auth/logout':
            $controller = new \App\Controllers\AuthController();
            $controller->logout();
            break;

        case '/reset-password':
            $controller = new \App\Controllers\AuthController();
            $controller->forgotPassword();
            break;

        case '/auth/reset-password':
            if ($method === 'POST') {
                $controller = new \App\Controllers\AuthController();
                $controller->forgotPassword();
            } else {
                http_response_code(405);
                echo 'Method Not Allowed';
            }
            break;

        // 网络诊断
        case '/admin/diag':
            $controller = new \App\Controllers\DiagController();
            $controller->index();
            break;

        case '/admin/diag/execute':
            if ($method === 'POST') {
                $controller = new \App\Controllers\DiagController();
                $controller->execute();
            } else {
                http_response_code(405);
                echo 'Method Not Allowed';
            }
            break;

        default:
            http_response_code(404);
            echo '404 Not Found';
            break;
    }
} catch (Exception $e) {
    http_response_code(500);
    echo 'Internal Server Error: ' . $e->getMessage();
} 