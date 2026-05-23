<?php
namespace App\Core;

class Redis
{
    private $redis;
    
    public function __construct()
    {
        $this->redis = new \Redis();
        $config = Config::getInstance();
        
        try {
            $this->redis->connect(
                $config->get('redis.host', '127.0.0.1'),
                $config->get('redis.port', 6379)
            );
            
            if ($password = $config->get('redis.password')) {
                $this->redis->auth($password);
            }
        } catch (\Exception $e) {
            throw new \Exception('Redis连接失败: ' . $e->getMessage());
        }
    }
    // 添加 get 方法
    public function get($key)
    {
        return $this->redis->get($key);
    }
    
    // 添加 set 方法
    public function set($key, $value)
    {
        return $this->redis->set($key, $value);
    }
    
    // 添加 keys 方法（如果需要）
    public function keys($pattern)
    {
        return $this->redis->keys($pattern);
    }

    
    public function hGetAll($key)
    {
        return $this->redis->hGetAll($key);
    }
    
    public function hSet($key, $field, $value)
    {
        return $this->redis->hSet($key, $field, $value);
    }
    
    public function hMSet($key, $data)
    {
        return $this->redis->hMSet($key, $data);
    }
    
    public function exists($key)
    {
        return $this->redis->exists($key);
    }
    
    public function expire($key, $seconds)
    {
        return $this->redis->expire($key, $seconds);
    }
    
    public function del($key)
    {
        return $this->redis->del($key);
    }
    
    // 添加 setex 方法
    public function setex($key, $seconds, $value)
    {
        return $this->redis->setex($key, $seconds, $value);
    }

    /**
     * 将哈希表中指定字段的整数值增加指定的增量值
     * @param string $key 键名
     * @param string $field 字段名
     * @param int $increment 增量值
     * @return int 增加后的值
     */
    public function hIncrBy($key, $field, $increment)
    {
        return $this->redis->hIncrBy($key, $field, $increment);
    }

    /**
     * 获取哈希表中指定字段的值
     * @param string $key 键名
     * @param string $field 字段名
     * @return string|false 字段值，如果字段不存在则返回false
     */
    public function hGet($key, $field)
    {
        return $this->redis->hGet($key, $field);
    }
} 