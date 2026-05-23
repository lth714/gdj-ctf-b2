<?php
namespace App\Core;

class Controller
{
    protected $logger;
    protected $config;
    
    public function __construct()
    {
        $this->logger = new Logger();
        $this->config = Config::getInstance();
    }
    
    protected function requireLogin()
    {
        if (!isset($_SESSION['user_id'])) {
            Response::error('请先登录', 401);
        }
    }
    
    protected function requireAdmin()
    {
        $this->requireLogin();
        if (!isset($_SESSION['is_admin']) || !$_SESSION['is_admin']) {
            Response::error('需要管理员权限', 403);
        }
    }
    
    protected function getPostData()
    {
        $data = file_get_contents('php://input');
        return json_decode($data, true);
    }
    
    protected function validateRequired($data, $fields)
    {
        foreach ($fields as $field) {
            if (!isset($data[$field]) || empty($data[$field])) {
                Response::error("缺少必填字段: $field");
            }
        }
    }
} 