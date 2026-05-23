<?php
namespace App\Core;

class Database
{
    private static $instance = null;
    private $connection;
    private $config;

    private function __construct()
    {
        // 读取配置文件
        $configFile = __DIR__ . '/../../config/config.php';
        if (file_exists($configFile)) {
            $this->config = require $configFile;
        } else {
            throw new \Exception('配置文件不存在');
        }

        try {
            $dsn = "mysql:host={$this->config['db']['host']};port={$this->config['db']['port']};dbname={$this->config['db']['dbname']};charset=utf8mb4";
            $this->connection = new \PDO(
                $dsn,
                $this->config['db']['username'],
                $this->config['db']['password'],
                [
                    \PDO::ATTR_ERRMODE => \PDO::ERRMODE_EXCEPTION,
                    \PDO::ATTR_DEFAULT_FETCH_MODE => \PDO::FETCH_ASSOC,
                    \PDO::ATTR_EMULATE_PREPARES => false,
                    \PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4"
                ]
            );
        } catch (\PDOException $e) {
            throw new \Exception('数据库连接失败: ' . $e->getMessage());
        }
    }

    public static function getInstance()
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    public function getConnection()
    {
        return $this->connection;
    }

    // 防止克隆
    private function __clone()
    {
    }

    // 防止反序列化 - 修改为 public
    public function __wakeup()
    {
    }

    // 执行查询并返回结果
    public function query($sql, $params = [])
    {
        try {
            $stmt = $this->connection->prepare($sql);
            $stmt->execute($params);
            return $stmt;
        } catch (\PDOException $e) {
            throw new \Exception('查询执行失败: ' . $e->getMessage());
        }
    }

    // 获取单行数据
    public function fetchOne($sql, $params = [])
    {
        $stmt = $this->query($sql, $params);
        return $stmt->fetch();
    }

    // 获取多行数据
    public function fetchAll($sql, $params = [])
    {
        $stmt = $this->query($sql, $params);
        return $stmt->fetchAll();
    }

    // 获取最后插入的ID
    public function lastInsertId()
    {
        return $this->connection->lastInsertId();
    }
} 