<?php
namespace App\Core;

class Logger
{
    private $logFile;
    private $dateFormat = 'Y-m-d H:i:s';
    
    public function __construct()
    {
        $this->logFile = dirname(dirname(__DIR__)) . '/storage/logs/app.log';
        $this->ensureLogDirectoryExists();
    }
    
    private function ensureLogDirectoryExists()
    {
        $logDir = dirname($this->logFile);
        if (!file_exists($logDir)) {
            mkdir($logDir, 0777, true);
        }
    }
    
    public function info($message)
    {
        $this->log('INFO', $message);
    }
    
    public function error($message)
    {
        $this->log('ERROR', $message);
    }
    
    public function warning($message)
    {
        $this->log('WARNING', $message);
    }
    
    public function debug($message)
    {
        $this->log('DEBUG', $message);
    }
    
    private function log($level, $message)
    {
        $date = date($this->dateFormat);
        $logMessage = "[$date] [$level] $message" . PHP_EOL;
        
        // 确保日志目录存在
        $this->ensureLogDirectoryExists();
        
        // 写入日志
        file_put_contents($this->logFile, $logMessage, FILE_APPEND | LOCK_EX);
    }
    
    public function getRecentLogs($limit = 100)
    {
        if (!file_exists($this->logFile)) {
            return [];
        }
        
        $logs = [];
        $lines = file($this->logFile);
        $lines = array_reverse($lines); // 最新的日志在前
        
        for ($i = 0; $i < min($limit, count($lines)); $i++) {
            $line = trim($lines[$i]);
            if (empty($line)) {
                continue;
            }
            
            // 解析日志行
            if (preg_match('/\[(.*?)\] \[(.*?)\] (.*)/', $line, $matches)) {
                $logs[] = [
                    'timestamp' => $matches[1],
                    'level' => $matches[2],
                    'message' => $matches[3]
                ];
            }
        }
        
        return $logs;
    }
    
    public function clear()
    {
        if (file_exists($this->logFile)) {
            unlink($this->logFile);
        }
    }
} 