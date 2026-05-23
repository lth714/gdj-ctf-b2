<?php
namespace App\Controllers;

use App\Core\Controller;
use App\Core\Response;
use App\Models\Settings;

class SettingsController extends Controller
{
    private $settings;
    
    public function __construct()
    {
        parent::__construct();
        $this->settings = Settings::getInstance();
    }
    
    public function index()
    {
        $settings = $this->settings->get();
        require __DIR__ . '/../views/admin/settings/index.php';
    }
    
    public function save()
    {
        try {
            // 获取 JSON 数据
            $data = json_decode(file_get_contents('php://input'), true);
            if (!$data) {
                Response::error('无效的数据格式');
            }
            
            // 验证必填字段
            $requiredFields = [
                'proxy_host',
                'proxy_port',
                'proxy_timeout',
                'monitor_refresh_interval',
                'status_check_interval',
                'check_mode'
            ];
            
            foreach ($requiredFields as $field) {
                if (!isset($data[$field]) || $data[$field] === '') {
                    Response::error("缺少必填字段: {$field}");
                }
            }
            
            // 处理布尔值字段
            $booleanFields = ['enable_memory_cache', 'enable_redis_cache', 'clear_logs_on_stop','clear_connections'];
            foreach ($booleanFields as $field) {
                // 如果字段不存在，说明复选框未选中，设置为 false
                $data[$field] = isset($data[$field]) ? (bool)$data[$field] : false;
            }
                        
            // 验证端口范围
            if (!is_numeric($data['proxy_port']) || $data['proxy_port'] < 1 || $data['proxy_port'] > 65535) {
                Response::error('代理服务器端口号必须在 1-65535 之间');
            }
            
            // 验证Redis端口（如果提供）
            if (isset($data['redis_port']) && (!is_numeric($data['redis_port']) || $data['redis_port'] < 1 || $data['redis_port'] > 65535)) {
                Response::error('Redis 端口号必须在 1-65535 之间');
            }
            
            // 验证超时时间
            if (!is_numeric($data['proxy_timeout']) || $data['proxy_timeout'] < 1 || $data['proxy_timeout'] > 300) {
                Response::error('代理服务器超时时间必须在 1-300 秒之间');
            }
            
            // 验证监控刷新时间
            if (!is_numeric($data['monitor_refresh_interval']) || $data['monitor_refresh_interval'] < 1 || $data['monitor_refresh_interval'] > 3600) {
                Response::error('监控刷新时间必须在 1-3600 秒之间');
            }
            
            // 验证服务状态检查间隔
            if (!is_numeric($data['status_check_interval']) || $data['status_check_interval'] < 1 || $data['status_check_interval'] > 60) {
                Response::error('服务状态检查间隔必须在 1-60 秒之间');
            }
            
            // 验证缓存相关设置
            if (isset($data['cache_cleanup_interval'])) {
                if (!is_numeric($data['cache_cleanup_interval']) || $data['cache_cleanup_interval'] < 60 || $data['cache_cleanup_interval'] > 3600) {
                    Response::error('缓存清理间隔必须在 60-3600 秒之间');
                }
            }
            
            if (isset($data['max_memory_cache_size'])) {
                if (!is_numeric($data['max_memory_cache_size']) || $data['max_memory_cache_size'] < 128 || $data['max_memory_cache_size'] > 8192) {
                    Response::error('最大内存缓存大小必须在 128-8192 MB之间');
                }
            }
            
            // 验证检查模式相关设置
            if ($data['check_mode'] === 'daily') {
                if (empty($data['daily_check_time'])) {
                    Response::error('请设置每日检查时间');
                }
            } else if ($data['check_mode'] === 'interval') {
                if (empty($data['check_interval']) || !is_numeric($data['check_interval']) || 
                    $data['check_interval'] < 1 || $data['check_interval'] > 24) {
                    Response::error('检查间隔必须在 1-24 小时之间');
                }
            } else if ($data['check_mode'] !== 'manual') {
                Response::error('无效的检查模式');
            }
            
            // 保存设置
            if ($this->settings->save($data)) {
                Response::success(null, '设置已保存');
            } else {
                Response::error('保存设置失败');
            }
        } catch (\Exception $e) {
            Response::error('保存设置时发生错误: ' . $e->getMessage());
        }
    }
} 