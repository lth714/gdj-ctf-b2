<?php $currentPage = 'index'; ?>
<!DOCTYPE html>
<html lang="zh-CN" class="h-100">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>首页 - IPTV 代理管理系统</title>
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="/css/all.min.css" rel="stylesheet">
    <link href="/css/chart.min.css" rel="stylesheet">
</head>
<body class="d-flex flex-column h-100">
    <?php $currentPage = 'index'; ?>
    <?php require __DIR__ . '/../navbar.php'; ?>

    <div class="content-wrapper">
        <div class="container-fluid py-3">
            <!-- 系统状态卡片 -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card h-100">
                        <div class="card-body">
                            <h6 class="card-title text-muted mb-3">
                                <i class="fas fa-server me-2"></i>代理服务
                            </h6>
                            <div class="d-flex align-items-center">
                                <div class="flex-grow-1">
                                    <h3 class="mb-0" id="proxyStatus">
                                        <span class="badge bg-secondary">检查中...</span>
                                    </h3>
                                </div>
                                <button class="btn btn-primary" id="toggleProxy" disabled>
                                    <i class="fas fa-power-off me-1"></i>启动
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card h-100">
                        <div class="card-body">
                            <h6 class="card-title text-muted mb-3">
                                <i class="fas fa-tv me-2"></i>频道总数
                            </h6>
                            <div class="d-flex align-items-center">
                                <div class="flex-grow-1">
                                    <h3 class="mb-0" id="totalChannels">-</h3>
                                </div>
                                <a href="/admin/channels" class="btn btn-outline-primary">
                                    <i class="fas fa-list me-1"></i>管理
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card h-100">
                        <div class="card-body">
                            <h6 class="card-title text-muted mb-3">
                                <i class="fas fa-check-circle me-2"></i>活跃频道
                            </h6>
                            <div class="d-flex align-items-center">
                                <h3 class="mb-0" id="activeChannels">-</h3>
                                <small class="text-muted ms-2">(最近5分钟)</small>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card h-100">
                        <div class="card-body">
                            <h6 class="card-title text-muted mb-3">
                                <i class="fas fa-exclamation-circle me-2"></i>错误频道
                            </h6>
                            <div class="d-flex align-items-center">
                                <h3 class="mb-0" id="errorChannels">-</h3>
                                <a href="/admin/channels" class="btn btn-outline-danger ms-auto">
                                    <i class="fas fa-wrench me-1"></i>处理
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 图表和统计 -->
            <div class="row">
                <!-- 性能监控 -->
                <div class="col-md-8 mb-4">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title mb-3">性能监控</h5>
                            <canvas id="performanceChart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- 分组统计 -->
                <div class="col-md-4 mb-4">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title mb-3">分组统计</h5>
                            <div id="groupStats" style="max-height: 300px; overflow-y: auto;">
                                <div class="text-center text-muted py-3">
                                    <i class="fas fa-spinner fa-spin me-2"></i>加载中...
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <?php require __DIR__ . '/../footer.php'; ?>

    <script src="/css/bootstrap.bundle.min.js"></script>
    <script src="/css/chart.min.js"></script>
    <script>
    let proxyStatus = false;
    
    // 显示提示信息
    function showAlert(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // 插入到页面顶部
        document.querySelector('.container-fluid').insertBefore(alertDiv, document.querySelector('.container-fluid').firstChild);
        
        // 5秒后自动消失
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
    
    // 检查代理状态
    async function checkProxyStatus() {
        const button = document.getElementById('proxyControl');
        const spinner = button.querySelector('.fa-spinner');
        const statusDiv = document.getElementById('proxyStatus');
        
        try {
            const response = await fetch('/admin/proxy/status');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const text = await response.text();
            console.log('Status response:', text); // 调试输出
            
            try {
                const result = JSON.parse(text);
                console.log('Parsed status:', result); // 调试输出
                
                if (result.success && result.data) {
                    // 更新全局状态变量
                    proxyStatus = result.data.running;
                    console.log('Updated proxyStatus:', proxyStatus); // 调试输出
                    
                    // 更新界面显示
                    if (proxyStatus) {
                        button.className = 'btn btn-danger';
                        button.querySelector('span').textContent = '停止服务';
                        statusDiv.innerHTML = `
                            <span class="text-success">
                                <i class="fas fa-circle"></i> 运行中
                            </span>
                            <div class="mt-2 small">
                                <div><i class="fas fa-clock"></i> 运行时间: ${formatUptime(result.data.uptime)}</div>
                                <div><i class="fas fa-memory"></i> 内存使用: ${formatBytes(result.data.memory)}</div>
                                <div><i class="fas fa-network-wired"></i> 当前连接数: ${result.data.connections}</div>
                                <div><i class="fas fa-plug"></i> 监听端口: ${result.data.port}</div>
                            </div>
                        `;
                    } else {
                        button.className = 'btn btn-success';
                        button.querySelector('span').textContent = '启动服务';
                        statusDiv.innerHTML = `
                            <span class="text-danger">
                                <i class="fas fa-circle"></i> 已停止
                            </span>
                        `;
                    }
                } else {
                    throw new Error('Invalid status response');
                }
            } catch (parseError) {
                console.error('JSON parse error:', parseError);
                console.error('Response text:', text);
                updateProxyStatus(false);
            }
        } catch (error) {
            console.error('Fetch error:', error);
            // 如果检查失败，不要立即更新状态，而是保持当前状态
            statusDiv.innerHTML = `
                <span class="text-warning">
                    <i class="fas fa-exclamation-triangle"></i> 状态检查失败
                </span>
            `;
        } finally {
            button.disabled = false;
            spinner.classList.add('d-none');
        }
    }
    
    // 切换代理服务器状态
    async function toggleProxy() {
        const button = document.getElementById('proxyControl');
        const spinner = button.querySelector('.fa-spinner');
        
        // 禁用按钮，显示加载动画
        button.disabled = true;
        spinner.classList.remove('d-none');
        
        try {
            const action = proxyStatus ? 'stop' : 'start';
            console.log('Executing action:', action);
            
            const response = await fetch('/admin/proxy/' + action, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('Action response:', result);
            
            if (result.success) {
                // 等待更长时间后再检查状态
                await new Promise(resolve => setTimeout(resolve, 2000));
                await checkProxyStatus();
                showAlert(result.message, 'success');
            } else {
                throw new Error(result.message || '操作失败');
            }
        } catch (error) {
            console.error('Error:', error);
            showAlert(error.message || '操作失败', 'error');
            // 发生错误时重新检查状态
            await checkProxyStatus();
        }
    }
    
    // 格式化运行时间
    function formatUptime(seconds) {
        if (!seconds) return '未知';
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const parts = [];
        if (days > 0) parts.push(`${days}天`);
        if (hours > 0) parts.push(`${hours}小时`);
        if (minutes > 0) parts.push(`${minutes}分钟`);
        return parts.join(' ') || '刚刚启动';
    }
    
    // 格式化字节数
    function formatBytes(bytes) {
        if (!bytes) return '未知';
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
    }
    
    // 页面加载时获取状态
    document.addEventListener('DOMContentLoaded', () => {
        console.log('Page loaded, checking initial status');
        checkProxyStatus();
        
        // 每5秒检查一次状态
        setInterval(checkProxyStatus, 5000);
    });
    </script>
</body>
</html> 