<?php
namespace App\Core;

use App\Models\Settings;

class Config
{
    private static $instance = null;
    private $config = [];
    private $configFile;
    private $settings;
    
    private function __construct()
    {
        $this->configFile = dirname(dirname(__DIR__)) . '/config/config.php';
        $this->settings = Settings::getInstance();
        $this->load();
    }
    
    public static function getInstance()
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function load()
    {
        // 加载文件配置
        if (file_exists($this->configFile)) {
            $this->config = require $this->configFile;
        }
        
        // 加载数据库配置，优先级高于文件配置
        $dbSettings = $this->settings->get();
        if ($dbSettings) {
            $this->config = array_merge($this->config, $dbSettings);
        }
    }
    
    public function get($key, $default = null)
    {
        return $this->config[$key] ?? $default;
    }
    
    public function set($key, $value)
    {
        $this->config[$key] = $value;
        // 保存到数据库
        return $this->settings->set($key, $value);
    }
    
    public function save()
    {
        $content = "<?php\nreturn " . var_export($this->config, true) . ";\n";
        return file_put_contents($this->configFile, $content, LOCK_EX);
    }
    
    public function all()
    {
        return $this->config;
    }
    
    public function reload()
    {
        $this->load();
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