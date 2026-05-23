<?php
// 定义基础路径
define('BASE_PATH', dirname(__DIR__));

// 错误报告设置
error_reporting(E_ALL);
ini_set('display_errors', 1);

// 设置时区
date_default_timezone_set('Asia/Shanghai');

// 加载安装程序类
require BASE_PATH . '/src/Install/Installer.php';
require BASE_PATH . '/src/Install/InstallController.php';

// 创建必要的目录
$directories = [
    BASE_PATH . '/config',
    BASE_PATH . '/storage/logs',
    BASE_PATH . '/storage/cache',
    BASE_PATH . '/storage/uploads',
    __DIR__ . '/install/templates'  
];

foreach ($directories as $dir) {
    if (!file_exists($dir)) {
        if (!@mkdir($dir, 0755, true)) {
            die("无法创建目录: $dir");
        }
    }
}

// 启动安装程序
session_start();
$installer = new InstallController();

// 获取当前步骤
$step = isset($_GET['step']) ? (int)$_GET['step'] : 1;

// 运行安装程序
$installer->run();