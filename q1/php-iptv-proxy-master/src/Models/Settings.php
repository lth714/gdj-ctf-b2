<?php
namespace App\Models;

use App\Core\Database;
use PDO;
use PDOException;

class Settings
{
    private $db;
    private static $instance = null;
    
    // 默认设置
    private $defaults = [
        'proxy_host' => '0.0.0.0',
        'proxy_port' => 8080,
        'proxy_timeout' => 10,
        'enable_memory_cache' => 1,      // 默认启用内存缓存
        'enable_redis_cache' => 1,       // 默认启用Redis缓存
        'cache_cleanup_interval' => 300,  // 默认5分钟清理一次
        'max_memory_cache_size' => 256,   // 默认最大256MB内存缓存
        'clear_logs_on_stop' => 0,       // 默认停止时不清理日志
        'clear_connections' => 0,       // 默认停止时不清理连接
        'check_mode' => 'manual',
        'check_interval' => '1',
        'daily_check_time' => '00:00',
        'monitor_refresh_interval' => '5',
        'max_error_count' => '3',
        'status_check_interval' => '10',  // 添加默认的服务状态检查间隔
    ];
    
    private function __construct()
    {
        $this->db = Database::getInstance()->getConnection();
    }
    
    public static function getInstance()
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    /**
     * 获取所有设置
     * @return array
     */
    public function getAll()
    {
        try {
            $settings = [];
            $stmt = $this->db->query("SELECT `key`, `value` FROM settings");
            while ($row = $stmt->fetch(\PDO::FETCH_ASSOC)) {
                $settings[$row['key']] = $row['value'];
            }
            
            // 合并默认值
            return array_merge($this->defaults, $settings);
        } catch (\Exception $e) {
            error_log("获取设置失败: " . $e->getMessage());
            return $this->defaults;
        }
    }
    
    /**
     * 获取所有设置（兼容旧版本）
     * @return array
     */
    public function get()
    {
        if (func_num_args() === 0) {
            return $this->getAll();
        }
        
        $key = func_get_arg(0);
        $default = func_num_args() > 1 ? func_get_arg(1) : null;
        return $this->getSetting($key, $default);
    }
    
    /**
     * 获取单个设置项
     * @param string $key 设置键名
     * @param mixed $default 默认值
     * @return mixed
     */
    private function getSetting($key, $default = null)
    {
        try {
            $stmt = $this->db->prepare("SELECT `value` FROM settings WHERE `key` = ?");
            $stmt->execute([$key]);
            $result = $stmt->fetch(\PDO::FETCH_ASSOC);
            
            if ($result) {
                return $result['value'];
            }
            
            // 如果在默认值中存在，返回默认值
            if (array_key_exists($key, $this->defaults)) {
                return $this->defaults[$key];
            }
            
            return $default;
        } catch (\Exception $e) {
            error_log("获取设置项失败: " . $e->getMessage());
            return $default;
        }
    }
    
    /**
     * 保存设置
     * @param array $settings 设置数组
     * @return bool
     */
    public function save($settings)
    {
        try {
            $this->db->beginTransaction();
            
            foreach ($settings as $key => $value) {
                $stmt = $this->db->prepare("INSERT INTO settings (`key`, `value`, `description`) 
                    VALUES (?, ?, ?) 
                    ON DUPLICATE KEY UPDATE `value` = ?");
                    
                // 根据设置项生成描述
                $description = $this->getSettingDescription($key);
                
                $stmt->execute([$key, $value, $description, $value]);
            }
            
            $this->db->commit();
            return true;
        } catch (\Exception $e) {
            $this->db->rollBack();
            error_log("保存设置失败: " . $e->getMessage());
            return false;
        }
    }

    /**
     * 获取设置项的描述
     * @param string $key 设置键名
     * @return string
     */
    private function getSettingDescription($key)
    {
        $descriptions = [
            'enable_memory_cache' => '是否启用内存缓存',
            'enable_redis_cache' => '是否启用Redis缓存',
            'cache_cleanup_interval' => '缓存清理间隔（秒）',
            'max_memory_cache_size' => '最大内存缓存大小（MB）',
            'proxy_host' => '代理服务器监听地址',
            'proxy_port' => '代理服务器监听端口',
            'proxy_timeout' => '代理连接超时时间',
            'proxy_buffer_size' => '缓冲区大小（KB）',
            'clear_logs_on_stop' => '停止时是否清理日志',
            'clear_connections' => '停止时是否清理连接记录',
            'check_mode' => '频道检查模式',
            'check_interval' => '频道检查间隔',
            'daily_check_time' => '每日检查时间',
            'monitor_refresh_interval' => '监控页面刷新间隔',
            'max_error_count' => '最大错误次数',
            'status_check_interval' => '服务状态检查间隔'
        ];
        
        return $descriptions[$key] ?? '';
    }
    
    // 防止对象被复制
    public function __clone()
    {
        throw new \RuntimeException('Clone is not allowed.');
    }
    
    // 防止反序列化创建对象
    public function __wakeup()
    {
        throw new \RuntimeException('Unserialize is not allowed.');
    }
} 