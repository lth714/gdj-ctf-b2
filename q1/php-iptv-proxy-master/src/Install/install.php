<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

// 定义基础路径
define('BASE_PATH', dirname(__DIR__));

// 检查PHP版本
if (version_compare(PHP_VERSION, '7.4.0', '<')) {
    die('需要PHP 7.4.0或更高版本');
}

// 检查必要的PHP扩展
$required_extensions = ['pdo', 'pdo_mysql', 'redis', 'curl', 'json', 'mbstring'];
foreach ($required_extensions as $ext) {
    if (!extension_loaded($ext)) {
        die("缺少必要的PHP扩展: {$ext}");
    }
}

// 创建必要的目录
$directories = [
    BASE_PATH . '/config',
    BASE_PATH . '/public/uploads',
    BASE_PATH . '/storage/logs',
    BASE_PATH . '/storage/cache'
];

foreach ($directories as $dir) {
    if (!file_exists($dir)) {
        mkdir($dir, 0755, true);
    }
}

// 检查是否已安装
if (file_exists(BASE_PATH . '/storage/installed.lock')) {
    die('系统已安装，如需重新安装请删除 storage/installed.lock 文件');
}

class Installer
{
    private $requirements = [
        'php' => '7.4.0',
        'extensions' => [
            'pdo',
            'pdo_mysql',
            'redis',
            'curl',
            'json',
            'mbstring'
        ]
    ];

    public function checkRequirements()
    {
        $results = [
            'php' => [
                'required' => $this->requirements['php'],
                'current' => PHP_VERSION,
                'status' => version_compare(PHP_VERSION, $this->requirements['php'], '>=')
            ],
            'extensions' => []
        ];

        foreach ($this->requirements['extensions'] as $ext) {
            $results['extensions'][$ext] = [
                'status' => extension_loaded($ext),
                'current' => extension_loaded($ext) ? phpversion($ext) : '未安装'
            ];
        }

        return $results;
    }

    public function checkWritable()
    {
        $paths = [
            BASE_PATH . '/config',
            BASE_PATH . '/public/uploads',
            BASE_PATH . '/storage/logs',
            BASE_PATH . '/storage/cache'
        ];

        $results = [];
        foreach ($paths as $path) {
            if (!file_exists($path)) {
                @mkdir($path, 0755, true);
            }
            $results[$path] = [
                'path' => $path,
                'writable' => is_writable($path)
            ];
        }

        return $results;
    }

    public function install($data)
    {
        try {
            // 1. 测试数据库连接
            $dsn = "mysql:host={$data['db_host']};port={$data['db_port']}";
            $pdo = new PDO($dsn, $data['db_user'], $data['db_pass']);
            
            // 2. 创建数据库
            $pdo->exec("CREATE DATABASE IF NOT EXISTS `{$data['db_name']}` 
                       CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
            
            // 3. 导入数据库结构
            $pdo->exec("USE `{$data['db_name']}`");
            $sql = file_get_contents(__DIR__ . '/database.sql');
            $pdo->exec($sql);
            
            // 4. 创建管理员账号
            $stmt = $pdo->prepare("INSERT INTO admins (username, password) VALUES (?, ?)");
            $stmt->execute([$data['admin_user'], password_hash($data['admin_pass'], PASSWORD_DEFAULT)]);
            
            // 5. 生成配置文件
            $config = [
                'db' => [
                    'host' => $data['db_host'],
                    'port' => $data['db_port'],
                    'dbname' => $data['db_name'],
                    'username' => $data['db_user'],
                    'password' => $data['db_pass']
                ],
                'redis' => [
                    'host' => $data['redis_host'],
                    'port' => $data['redis_port'],
                    'password' => $data['redis_pass'] ?: null
                ],
                'stream' => [
                    'chunk_size' => 1048576,
                    'cache_time' => 300
                ]
            ];
            
            file_put_contents(
                __DIR__ . '/../config/config.php',
                "<?php\nreturn " . var_export($config, true) . ";\n"
            );
            
            return ['success' => true];
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }

    public function cleanup()
    {
        // 删除安装文件
        $files = [
            __DIR__ . '/install.php',
            __DIR__ . '/install.sh',
            __DIR__ . '/database.sql',
            __DIR__ . '/nginx.conf',
            __DIR__ . '/templates/install.php'
        ];

        foreach ($files as $file) {
            if (file_exists($file)) {
                @unlink($file);
            }
        }

        // 删除安装目录
        @rmdir(__DIR__ . '/templates');
        @rmdir(__DIR__);

        return true;
    }

    public function checkLock()
    {
        return file_exists(__DIR__ . '/../storage/installed.lock');
    }

    public function createLock()
    {
        return file_put_contents(
            __DIR__ . '/../storage/installed.lock',
            date('Y-m-d H:i:s')
        );
    }
}

// 处理安装请求
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $installer = new Installer();
    $result = $installer->install($_POST);
    header('Content-Type: application/json');
    echo json_encode($result);
    exit;
}

// 显示安装页面
$installer = new Installer();
$requirements = $installer->checkRequirements();
$writableChecks = $installer->checkWritable();
require __DIR__ . '/templates/install.php'; 