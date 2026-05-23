<?php
namespace App\Core;

class Router
{
    private static $routes = [
        // 首页
        '/' => ['HomeController', 'index'],
        
        // 频道管理
        '/admin/channels' => ['ChannelController', 'index'],
        '/admin/channels/add' => ['ChannelController', 'add'],
        '/admin/channels/create' => ['ChannelController', 'create'],
        '/admin/channels/edit/{id}' => ['ChannelController', 'edit'],
        '/admin/channels/update/{id}' => ['ChannelController', 'update'],
        '/admin/channels/delete/{id}' => ['ChannelController', 'deleteChannel'],
        '/admin/channels/delete-multiple' => ['ChannelController', 'deleteMultiple'],
        '/admin/channels/delete-all' => ['ChannelController', 'deleteAll'],
        '/admin/channels/check/{id}' => ['ChannelController', 'checkChannel'],
        '/admin/channels/check-all' => ['ChannelController', 'checkAll'],
        '/admin/channels/check-progress/{taskId}' => ['ChannelController', 'checkProgress'],
        '/admin/channels/import' => ['ChannelController', 'showImport'],
        '/admin/channels/do-import' => ['ChannelController', 'import'],
        
        // 系统监控
        '/admin/monitor' => ['MonitorController', 'index'],
        '/admin/monitor/stats' => ['MonitorController', 'getStats'],
        '/admin/monitor/logs' => ['MonitorController', 'logs'],
        '/admin/monitor/logs/data' => ['MonitorController', 'getLogs'],
        
        // 日志管理
        '/admin/logs' => ['LogController', 'index'],
        '/admin/logs/data' => ['LogController', 'getLogs'],
        
        // 系统设置
        '/admin/settings' => ['SettingsController', 'index'],
        '/admin/settings/save' => ['SettingsController', 'save'],
        
        // 代理服务
        '/admin/proxy/status' => ['ProxyController', 'status'],
        '/admin/proxy/start' => ['ProxyController', 'start'],
        '/admin/proxy/stop' => ['ProxyController', 'stop'],
        '/admin/proxy/connection-stats' => ['ProxyController', 'getConnectionStats']
    ];

    public static function dispatch($uri)
    {
        // 移除查询字符串
        $uri = parse_url($uri, PHP_URL_PATH);
        
        // 查找匹配的路由
        foreach (self::$routes as $route => $handler) {
            $pattern = self::convertRouteToRegex($route);
            if (preg_match($pattern, $uri, $matches)) {
                $controllerName = "\\App\\Controllers\\" . $handler[0];
                $methodName = $handler[1];
                
                // 创建控制器实例
                $controller = new $controllerName();
                
                // 提取路由参数
                array_shift($matches); // 移除完整匹配
                
                // 调用控制器方法
                return call_user_func_array([$controller, $methodName], $matches);
            }
        }
        
        // 未找到匹配的路由
        header("HTTP/1.0 404 Not Found");
        echo "404 Not Found";
    }

    private static function convertRouteToRegex($route)
    {
        return "#^" . preg_replace('/\{([a-zA-Z0-9_]+)\}/', '([^/]+)', $route) . "$#";
    }
} 