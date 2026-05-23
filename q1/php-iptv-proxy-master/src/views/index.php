<?php
$currentPage = 'home';
?>
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPTV 代理系统</title>
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="/css/all.min.css" rel="stylesheet">
    <style>
        /* 统计卡片样式 */
        .stats-card {
            height: 100%;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            border: none;
            position: relative;
            overflow: hidden;
        }
        .stats-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }
        .stats-card .card-body {
            padding: 1.5rem;
            position: relative;
            z-index: 1;
        }
        .stats-card .card-title {
            font-size: 1rem;
            margin-bottom: 0.75rem;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.9);
        }
        .stats-card .card-text {
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 0;
            color: #ffffff;
        }
		.stats-card .card-text2 {
            font-size: 1.2rem;
            font-weight: 400;
            margin-bottom: 0;
            color: #ffffff;
        }
        .stats-card .stats-icon {
            position: absolute;
            right: 1rem;
            bottom: 1rem;
            font-size: 3rem;
            opacity: 0.2;
            color: #ffffff;
        }
        /* 不同统计卡片的背景色 */
        .stats-total-channels {
            background: linear-gradient(45deg, #4e73df, #224abe);
        }
        .stats-active-channels {
            background: linear-gradient(45deg, #1cc88a, #13855c);
        }
        .stats-error-channels {
            background: linear-gradient(45deg, #e74a3b, #be2617);
        }
        .stats-connections {
            background: linear-gradient(45deg, #f6c23e, #dda20a);
        }
        .stats-bandwidth {
            background: linear-gradient(45deg, #36b9cc, #258391);
        }

        /* 代理开关样式 - 恢复原始样式 */
        .proxy-switch {
            transition: all 0.3s ease;
        }
        .proxy-switch:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .proxy-switch .proxy-status {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .proxy-switch .fa-power-off {
            transition: all 0.3s ease;
            margin-bottom: 0.5rem;
        }
        .proxy-switch.active {
            background-color: #09a22e;
            border-color: #c3e6cb;
        }
        .proxy-switch.active .fa-power-off {
            color: #28a745;
        }
        .proxy-switch.inactive {
            background-color: #f87e89;
            border-color: #f5c6cb;
        }
        .proxy-switch.inactive .fa-power-off {
            color: #ea1025;
        }
        .proxy-switch.checking {
            background-color: #fad662;
            border-color: #ffeeba;
        }
        .proxy-switch.checking .fa-power-off {
            color: #ffc107;
        }

        /* 快捷操作卡片样式 */
        .shortcut-card {
            border-radius: 15px;
            border: none;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .shortcut-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }
        .shortcut-card .card-body {
            padding: 2rem;
            position: relative;
            z-index: 1;
        }
        .shortcut-card .card-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #2c3e50;
        }
        .shortcut-card .card-text {
            color: #6c757d;
            margin-bottom: 1.5rem;
        }
        .shortcut-card .shortcut-icon {
            position: absolute;
            right: 2rem;
            bottom: 2rem;
            font-size: 4rem;
            opacity: 0.1;
        }
        .shortcut-card .btn {
            padding: 0.6rem 1.5rem;
            font-weight: 500;
            border-radius: 10px;
            border: none;
        }
        /* 不同快捷操作卡片的样式 */
        .shortcut-channels {
            background: linear-gradient(145deg, #ffffff, #f8f9fc);
        }
        .shortcut-channels .shortcut-icon {
            color: #4e73df;
        }
        .shortcut-import {
            background: linear-gradient(145deg, #ffffff, #f8f9fc);
        }
        .shortcut-import .shortcut-icon {
            color: #1cc88a;
        }
        .shortcut-monitor {
            background: linear-gradient(145deg, #ffffff, #f8f9fc);
        }
        .shortcut-monitor .shortcut-icon {
            color: #36b9cc;
        }

        /* 系统状态样式 */
        .system-status {
            font-size: 0.85rem;
        }
        .system-status .progress {
            height: 8px;
        }
        .system-status span {
            color: #2c3e50;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <?php require __DIR__ . '/navbar.php'; ?>

    <div class="container-fluid mt-4">
        <div class="row">
            <div class="col-md-12">
                <!-- 频道统计和系统状态 -->
                <div class="row mb-4">
                    <div class="col-md-2">
                        <div class="card stats-card stats-total-channels">
                            <div class="card-body">
                                <h5 class="card-title">总频道数</h5>
                                <p class="card-text"><?= $channelStats['total_channels'] ?></p>
                                <i class="fas fa-tv stats-icon"></i>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <div class="card stats-card stats-active-channels">
                            <div class="card-body">
                                <h5 class="card-title">活跃频道</h5>
                                <p class="card-text"><?= $channelStats['active_channels'] ?></p>
                                <i class="fas fa-signal stats-icon"></i>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <div class="card stats-card stats-error-channels">
                            <div class="card-body">
                                <h5 class="card-title">错误频道</h5>
                                <p class="card-text"><?= $channelStats['error_channels'] ?></p>
                                <i class="fas fa-exclamation-triangle stats-icon"></i>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <div class="card stats-card stats-connections">
                            <div class="card-body">
                                <h5 class="card-title">总连接数</h5>
                                <p class="card-text" data-stat="connections">-</p>
                                <i class="fas fa-users stats-icon"></i>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <div class="card stats-card stats-bandwidth">
                            <div class="card-body">
                                <h5 class="card-title">总带宽</h5>
                                <p class="card-text2" id="upload_bandwidth">上行 - MB/s</p>
								<p class="card-text2" id="download_bandwidth">下行 - MB/s</p>
                                <i class="fas fa-network-wired stats-icon"></i>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <div class="card stats-card proxy-switch" id="proxySwitch" style="cursor: pointer;" onclick="toggleProxy()">
                            <div class="card-body text-center">
                                <h5 class="card-title">代理服务</h5>
                                <div class="proxy-status">
                                    <i class="fas fa-power-off fa-2x"></i>
                                    <p class="card-text mt-2" id="proxyStatusText">检查中...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 系统状态 -->
                <div class="row mb-4">
                    <div class="col-md-12">
                        <div class="card system-status">
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-3">
                                        <div class="mb-2">
                                            <span>CPU使用率: <?= $systemStatus['cpu'] ?>%</span>
                                            <div class="progress">
                                                <div class="progress-bar" role="progressbar" style="width: <?= $systemStatus['cpu'] ?>%" aria-valuenow="<?= $systemStatus['cpu'] ?>" aria-valuemin="0" aria-valuemax="100"></div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="mb-2">
                                            <span>内存使用: <?= $systemStatus['memory']['percentage'] ?>%</span>
                                            <div class="progress">
                                                <div class="progress-bar" role="progressbar" style="width: <?= $systemStatus['memory']['percentage'] ?>%" aria-valuenow="<?= $systemStatus['memory']['percentage'] ?>" aria-valuemin="0" aria-valuemax="100"></div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="mb-2">
                                            <span>磁盘使用: <?= $systemStatus['disk']['percentage'] ?>%</span>
                                            <div class="progress">
                                                <div class="progress-bar" role="progressbar" style="width: <?= $systemStatus['disk']['percentage'] ?>%" aria-valuenow="<?= $systemStatus['disk']['percentage'] ?>" aria-valuemin="0" aria-valuemax="100"></div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="mb-2">
                                            <span>负载: <?= $systemStatus['load']['1min'] ?> / <?= $systemStatus['load']['5min'] ?> / <?= $systemStatus['load']['15min'] ?></span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 快捷操作卡片 -->
                <div class="row mb-4">
                    <div class="col-md-4">
                        <div class="card shortcut-card shortcut-channels">
                            <div class="card-body">
                                <h5 class="card-title">频道管理</h5>
                                <p class="card-text">添加、编辑、删除频道，管理频道分组。</p>
                                <a href="/admin/channels" class="btn btn-primary">进入管理</a>
                                <i class="fas fa-tv shortcut-icon"></i>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card shortcut-card shortcut-import">
                            <div class="card-body">
                                <h5 class="card-title">导入频道</h5>
                                <p class="card-text">从 M3U/M3U8 文件批量导入频道。</p>
                                <a href="/admin/import" class="btn btn-success">开始导入</a>
                                <i class="fas fa-file-import shortcut-icon"></i>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card shortcut-card shortcut-monitor">
                            <div class="card-body">
                                <h5 class="card-title">实时监控</h5>
                                <p class="card-text">监控频道状态、带宽和连接数。</p>
                                <a href="/admin/monitor" class="btn btn-info">查看监控</a>
                                <i class="fas fa-chart-line shortcut-icon"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
	<?php require __DIR__ . '/footer.php'; ?>
    <script src="/css/bootstrap.bundle.min.js"></script>
    <script>
        // 添加全局状态变量
        let isProxyRunning = false;
        let statusCheckInterval = null;
        let stoppedConfirmCount = 0;
        let checkIntervalTime = <?= intval($settings['status_check_interval'] ?? 10) ?> * 1000;
        
        // 检查代理状态和连接数
        function checkProxyStatus() {
            const proxySwitch = document.getElementById('proxySwitch');
            const statusText = document.getElementById('proxyStatusText');
            
            proxySwitch.className = 'card stats-card proxy-switch checking';
            statusText.textContent = '检查中...';
            
            fetch('/admin/proxy/status')
                .then(response => response.json())
                .then(result => {
                    if (result.success && result.data && result.data.running) {
                        isProxyRunning = true;
                        stoppedConfirmCount = 0;
                        proxySwitch.className = 'card stats-card proxy-switch active';
                        statusText.textContent = '运行中';
                        
                        // 如果代理在运行，获取连接统计
                        updateConnectionStats();
                    } else {
                        isProxyRunning = false;
                        proxySwitch.className = 'card stats-card proxy-switch inactive';
                        statusText.textContent = '已停止';
                        
                        // 清除连接数显示
                        document.querySelector('.card-text[data-stat="connections"]').textContent = '-';
                        
                        stoppedConfirmCount++;
                    }
                })
                .catch(error => {
                    console.error('检查代理状态时发生错误:', error);
                    proxySwitch.className = 'card stats-card proxy-switch inactive';
                    statusText.textContent = '检查失败';
                });
        }
        
        // 更新连接统计
        function updateConnectionStats() {
            fetch('/admin/proxy/connection-stats')
                .then(response => response.json())
                .then(result => {
                    if (result.success && result.data) {
                        // 更新总连接数
                        document.querySelector('.card-text[data-stat="connections"]').textContent = 
                            result.data.connections || '0';
                    }
                })
                .catch(error => {
                    console.error('获取连接统计失败:', error);
                });
        }
        
        // 切换代理状态
        function toggleProxy() {
            if (isProxyRunning) {
                stopProxy();
            } else {
                startProxy();
            }
        }

        // 启动代理服务
        function startProxy() {
            const proxySwitch = document.getElementById('proxySwitch');
            const statusText = document.getElementById('proxyStatusText');
            
            proxySwitch.className = 'card stats-card proxy-switch checking';
            statusText.textContent = '处理中...';
            
            fetch('/admin/proxy/start', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    // 重置停止确认计数
                    stoppedConfirmCount = 0;
                    
                    // 清除现有的定时检查
                    if (statusCheckInterval) {
                        clearInterval(statusCheckInterval);
                        statusCheckInterval = null;
                    }
                    
                    // 等待更长时间后开始检查状态
                    setTimeout(() => {
                        // 立即执行一次更新
                        checkProxyStatus();
                        updateBandwidth();
                        
                        // 开始定时检查状态和带宽
                        statusCheckInterval = setInterval(function() {
                            checkProxyStatus();
                            updateBandwidth();
                        }, checkIntervalTime);
                    }, 2000);
                } else {
                    throw new Error(result.message || '启动失败');
                }
            })
            .catch(error => {
                console.error('启动代理服务时发生错误:', error);
                checkProxyStatus();
                updateBandwidth();
                alert(error.message || '启动失败，请重试');
            });
        }
        
        // 停止代理服务
        function stopProxy() {
            const proxySwitch = document.getElementById('proxySwitch');
            const statusText = document.getElementById('proxyStatusText');
            
            proxySwitch.className = 'card stats-card proxy-switch checking';
            statusText.textContent = '处理中...';
            
            fetch('/admin/proxy/stop', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    // 重置停止确认计数
                    stoppedConfirmCount = 0;
                    
                    // 清除现有的定时检查
                    if (statusCheckInterval) {
                        clearInterval(statusCheckInterval);
                        statusCheckInterval = null;
                    }
                    
                    // 等待更长时间后开始检查状态
                    setTimeout(() => {
                        // 立即执行一次更新
                        checkProxyStatus();
                        updateBandwidth();
                        
                        // 开始定时检查状态和带宽
                        statusCheckInterval = setInterval(function() {
                            checkProxyStatus();
                            updateBandwidth();
                        }, checkIntervalTime);
                    }, 2000);
                } else {
                    throw new Error(result.message || '停止失败');
                }
            })
            .catch(error => {
                console.error('停止代理服务时发生错误:', error);
                checkProxyStatus();
                updateBandwidth();
                alert(error.message || '停止失败，请重试');
            });
        }
        
        // 添加带宽更新函数
        function updateBandwidth() {
            fetch('/admin/proxy/bandwidth-stats')
                .then(response => response.json())
                .then(response => {
                    if (response.success && response.data.total) {
                        const total = response.data.total;
                        document.getElementById('upload_bandwidth').textContent = '上行 ' + total.bandwidth.upload;
                        document.getElementById('download_bandwidth').textContent = '下行 ' + total.bandwidth.download;
                    
                        // 如果有活跃流量，添加高亮效果
                        const bandwidthCard = document.querySelector('.stats-bandwidth');
                        if (total.channels_with_traffic > 0) {
                            bandwidthCard.classList.add('active');
                        } else {
                            bandwidthCard.classList.remove('active');
                        }
                    }
                })
                .catch(error => {
                    console.error('获取带宽数据失败:', error);
                    document.getElementById('upload_bandwidth').textContent = '上行 - MB/s';
                    document.getElementById('download_bandwidth').textContent = '下行 - MB/s';
                    document.querySelector('.stats-bandwidth').classList.remove('active');
                });
        }

        // 页面加载时检查状态
        document.addEventListener('DOMContentLoaded', function() {
            checkProxyStatus();
            // 更新带宽显示
            updateBandwidth();
            // 开始定时检查
            if (!statusCheckInterval) {
                statusCheckInterval = setInterval(function() {
                    checkProxyStatus();
                    updateBandwidth();  // 同时更新带宽
                }, checkIntervalTime);
            }
        });
    </script>
</body>
</html> 