<?php
namespace App\Controllers;

use App\Core\SystemStatus;
use App\Models\Channel;

class IndexController
{
    private $systemStatus;
    private $channelModel;

    public function __construct()
    {
        $this->systemStatus = new SystemStatus();
        $this->channelModel = new Channel();
    }

    public function index()
    {
        // 获取频道统计信息
        $channelStats = $this->channelModel->getChannelStats();

        // 获取系统状态信息
        $systemStatus = [
            'cpu' => $this->systemStatus->getCpuUsage(),
            'memory' => $this->systemStatus->getMemoryUsage(),
            'disk' => $this->getDiskUsageSummary(),
            'load' => $this->systemStatus->getLoadAverage()
        ];

        require __DIR__ . '/../views/index.php';
    }

    private function getDiskUsageSummary()
    {
        $disks = $this->systemStatus->getDiskUsage();
        if (!empty($disks)) {
            // 返回根目录的使用情况
            foreach ($disks as $disk) {
                if ($disk['mount'] === '/') {
                    return [
                        'total' => $disk['total'],
                        'used' => $disk['used'],
                        'free' => $disk['free'],
                        'percentage' => $disk['percentage']
                    ];
                }
            }
        }
        return ['total' => '0', 'used' => '0', 'free' => '0', 'percentage' => 0];
    }
} 