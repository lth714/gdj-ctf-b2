<?php
require_once __DIR__ . '/../../vendor/autoload.php';

use App\Proxy\Server;
use App\Core\Logger;

$logger = new Logger();

// 检查命令行参数
if ($argc < 2) {
    echo "用法: php proxy.php {start|stop|status}\n";
    exit(1);
}

$command = $argv[1];
$pidFile = __DIR__ . '/../../storage/proxy.pid';
$logFile = __DIR__ . '/../../storage/logs/proxy.log';

function getPid() {
    global $pidFile;
    return @file_get_contents($pidFile);
}

function isRunning($pid) {
    if (!$pid) return false;
    
    // Windows系统
    if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
        $cmd = "tasklist /FI \"PID eq $pid\" /NH";
        exec($cmd, $output);
        
        foreach ($output as $line) {
            if (strpos($line, (string)$pid) !== false) {
                return true;
            }
        }
        return false;
    }
    
    // Linux系统
    if (!@posix_kill($pid, 0)) {
        return false;
    }
    
    $cmdline = @file_get_contents("/proc/$pid/cmdline");
    if ($cmdline === false) {
        return false;
    }
    
    return strpos($cmdline, 'proxy.php') !== false;
}

function cleanupFiles() {
    global $pidFile;
    @unlink($pidFile);
}

function daemonize() {
    global $logFile;
    
    // 创建子进程
    $pid = pcntl_fork();
    if ($pid < 0) {
        exit("无法创建子进程\n");
    }
    
    // 父进程退出
    if ($pid > 0) {
        exit(0);
    }
    
    // 设置新会话
    if (posix_setsid() < 0) {
        exit("无法创建新会话\n");
    }
    
    // 再次fork，彻底脱离终端
    $pid = pcntl_fork();
    if ($pid < 0) {
        exit("无法创建第二个子进程\n");
    }
    if ($pid > 0) {
        exit(0);
    }
    
    // 设置umask
    umask(0);
    
    // 切换工作目录到项目根目录
    chdir(__DIR__ . '/../../');
    
    // 关闭标准输入输出
    fclose(STDIN);
    fclose(STDOUT);
    fclose(STDERR);
    
    // 重定向标准输出到日志文件
    $stdOut = fopen($logFile, 'a');
    $stdErr = fopen($logFile, 'a');
    
    if ($stdOut) {
        fclose($stdOut);
    }
    if ($stdErr) {
        fclose($stdErr);
    }
}

switch ($command) {
    case 'start':
        // 检查是否已经在运行
        $pid = getPid();
        if ($pid && isRunning($pid)) {
            echo "代理服务器已经在运行中\n";
            exit(1);
        }
        
        // 如果支持pcntl，则使用守护进程模式
        if (function_exists('pcntl_fork')) {
            daemonize();
        }
        
        // 启动服务器
        $server = new Server();
        
        // 记录PID
        $pid = getmypid();
        file_put_contents($pidFile, $pid);
        $logger->info("代理服务器已启动 (PID: $pid)");
        
        // 注册信号处理
        pcntl_signal(SIGTERM, function($signo) use ($server, $logger) {
            $logger->info("代理服务器正在停止");
            $server->stop();
            cleanupFiles();
            exit(0);
        });
        
        pcntl_signal(SIGINT, function($signo) use ($server, $logger) {
            $logger->info("代理服务器正在停止");
            $server->stop();
            cleanupFiles();
            exit(0);
        });
        
        // 忽略SIGHUP信号，防止终端关闭时进程退出
        pcntl_signal(SIGHUP, SIG_IGN);
        
        // 启动服务器
        if (!$server->start()) {
            $logger->error("代理服务器启动失败");
            cleanupFiles();
            exit(1);
        }
        
        // 运行服务器主循环
        if (!$server->run()) {
            $logger->error("代理服务器运行失败");
            cleanupFiles();
            exit(1);
        }
        break;
        
    case 'stop':
        $pid = getPid();
        if (!$pid || !isRunning($pid)) {
            echo "代理服务器未运行\n";
            cleanupFiles();
            exit(1);
        }
        
        // 发送停止信号
        posix_kill($pid, SIGTERM);
        
        // 等待进程停止
        $timeout = 10;
        while ($timeout > 0 && isRunning($pid)) {
            sleep(1);
            $timeout--;
        }
        
        // 如果进程仍在运行，强制终止
        if (isRunning($pid)) {
            posix_kill($pid, SIGKILL);
            sleep(1);
        }
        
        cleanupFiles();
        echo "代理服务器已停止\n";
        break;
        
    case 'status':
        $pid = getPid();
        if ($pid && isRunning($pid)) {
            echo "代理服务器正在运行 (PID: $pid)\n";
        } else {
            if ($pid) {
                $logger->info("进程 $pid 不存在，清理文件");
            }
            echo "代理服务器未运行\n";
            cleanupFiles();
        }
        break;
        
    default:
        echo "未知命令: $command\n";
        echo "用法: php proxy.php {start|stop|status}\n";
        exit(1);
} 