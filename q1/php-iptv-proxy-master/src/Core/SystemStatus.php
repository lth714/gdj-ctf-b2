<?php
namespace App\Core;

class SystemStatus
{
    public function getLoadAverage()
    {
        if (function_exists('sys_getloadavg')) {
            $load = sys_getloadavg();
            return [
                '1min' => round($load[0], 2),
                '5min' => round($load[1], 2),
                '15min' => round($load[2], 2)
            ];
        }
        return ['1min' => 0, '5min' => 0, '15min' => 0];
    }

    public function getCpuUsage()
    {
        $cpu = 0;
        if (PHP_OS === 'Linux') {
            $load = @file_get_contents('/proc/loadavg');
            if ($load !== false) {
                $load = explode(' ', $load);
                $cpu = round((float)$load[0] * 100, 2);
            }
        }
        return $cpu;
    }

    public function getMemoryUsage()
    {
        if (PHP_OS === 'Linux') {
            $free = shell_exec('free');
            $free = (string)trim($free);
            $free_arr = explode("\n", $free);
            $mem = explode(" ", $free_arr[1]);
            $mem = array_filter($mem);
            $mem = array_merge($mem);
            $memory_usage = $mem[2]/$mem[1]*100;

            $total_mb = round($mem[1] / 1024, 2);
            $used_mb = round($mem[2] / 1024, 2);
            $free_mb = round($mem[3] / 1024, 2);

            return [
                'total' => $total_mb,
                'used' => $used_mb,
                'free' => $free_mb,
                'percentage' => round($memory_usage, 2)
            ];
        }
        return [
            'total' => 0,
            'used' => 0,
            'free' => 0,
            'percentage' => 0
        ];
    }

    public function getNetworkUsage()
    {
        $rx = 0;
        $tx = 0;
        if (PHP_OS === 'Linux') {
            $command = "cat /proc/net/dev | grep -E '^[^lo]'";
            $output = shell_exec($command);
            if ($output) {
                $lines = explode("\n", trim($output));
                foreach ($lines as $line) {
                    $data = preg_split('/\s+/', trim($line));
                    if (isset($data[1], $data[9])) {
                        $rx += (int)$data[1];
                        $tx += (int)$data[9];
                    }
                }
            }
        }

        $rx_mb = round($rx / (1024 * 1024), 2);
        $tx_mb = round($tx / (1024 * 1024), 2);

        return [
            'rx' => $rx_mb,
            'tx' => $tx_mb,
            'total' => $rx_mb + $tx_mb
        ];
    }

    public function getDiskUsage()
    {
        $disks = [];
        if (PHP_OS === 'Linux') {
            $df = shell_exec('df -h');
            $lines = explode("\n", trim($df));
            array_shift($lines); // 移除标题行
            foreach ($lines as $line) {
                $data = preg_split('/\s+/', trim($line));
                if (isset($data[5]) && strpos($data[5], '/') === 0) {
                    $disks[] = [
                        'device' => $data[0],
                        'total' => $data[1],
                        'used' => $data[2],
                        'free' => $data[3],
                        'percentage' => rtrim($data[4], '%'),
                        'mount' => $data[5]
                    ];
                }
            }
        }
        return $disks;
    }

    public function getTopProcesses($type = 'cpu', $limit = 5)
    {
        $processes = [];
        if (PHP_OS === 'Linux') {
            switch ($type) {
                case 'cpu':
                    $command = "ps aux --sort=-%cpu | head -n " . ($limit + 1);
                    break;
                case 'memory':
                    $command = "ps aux --sort=-%mem | head -n " . ($limit + 1);
                    break;
                case 'io':
                    $command = "iotop -b -n 1 -o | head -n " . ($limit + 1);
                    break;
                default:
                    return [];
            }
            
            $output = shell_exec($command);
            if ($output) {
                $lines = explode("\n", trim($output));
                array_shift($lines); // 移除标题行
                foreach ($lines as $line) {
                    $data = preg_split('/\s+/', trim($line));
                    if (isset($data[10])) {
                        $processes[] = [
                            'user' => $data[0],
                            'pid' => $data[1],
                            'cpu' => $data[2],
                            'memory' => $data[3],
                            'command' => implode(' ', array_slice($data, 10))
                        ];
                    }
                }
            }
        }
        return $processes;
    }
} 