<?php $currentPage = 'settings'; ?>
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统设置 - IPTV 代理系统</title>
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="/css/all.min.css" rel="stylesheet">
</head>
<body>
    <?php require __DIR__ . '/../../navbar.php'; ?>

    <div class="container-fluid mx-auto" style="width: 98%;">
        <div class="row">
            <div class="col-md-12">
                <h2>系统设置</h2>
                <?php if (isset($_SESSION['flash_message'])): ?>
                    <div class="alert alert-<?= $_SESSION['flash_message']['type'] ?> mt-3">
                        <?= $_SESSION['flash_message']['message'] ?>
                    </div>
                    <?php unset($_SESSION['flash_message']); ?>
                <?php endif; ?>

                <form id="settingsForm" method="post" action="/admin/settings/save" class="mt-4">
                    <!-- 标签导航 -->
                    <ul class="nav nav-tabs mb-3" id="settingsTabs" role="tablist">
                        <li class="nav-item">
                            <a class="nav-link active" id="basic-tab" data-bs-toggle="tab" href="#basic" role="tab">基本设置</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" id="proxy-tab" data-bs-toggle="tab" href="#proxy" role="tab">代理服务器</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" id="cache-tab" data-bs-toggle="tab" href="#cache" role="tab">缓存设置</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" id="redis-tab" data-bs-toggle="tab" href="#redis" role="tab">Redis设置</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" id="monitor-tab" data-bs-toggle="tab" href="#monitor" role="tab">监控设置</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" id="check-tab" data-bs-toggle="tab" href="#check" role="tab">频道检查</a>
                        </li>
                    </ul>

                    <!-- 标签内容 -->
                    <div class="tab-content" id="settingsTabContent">
                        <!-- 基本设置 -->
                        <div class="tab-pane fade show active" id="basic" role="tabpanel">
                            <div class="card">
                                <div class="card-body">
                                    <div class="mb-3">
                                        <label class="form-label">站点名称</label>
                                        <input type="text" class="form-control" name="site_name" value="<?= htmlspecialchars($settings['site_name'] ?? '') ?>">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">最大错误次数</label>
                                        <input type="number" class="form-control" name="max_error_count" value="<?= intval($settings['max_error_count'] ?? 3) ?>">
                                        <small class="text-muted">频道检测失败达到此次数后将被自动删除</small>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 代理服务器设置 -->
                        <div class="tab-pane fade" id="proxy" role="tabpanel">
                            <div class="card">
                                <div class="card-body">
                                    <div class="mb-3">
                                        <label class="form-label">监听地址</label>
                                        <input type="text" class="form-control" name="proxy_host" value="<?= htmlspecialchars($settings['proxy_host'] ?? '0.0.0.0') ?>">
                                        <small class="text-muted">默认 0.0.0.0 表示监听所有网卡</small>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">监听端口</label>
                                        <input type="number" class="form-control" name="proxy_port" value="<?= intval($settings['proxy_port'] ?? 8081) ?>">
                                        <small class="text-muted">建议使用大于 1024 的端口</small>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">连接超时时间（秒）</label>
                                        <input type="number" class="form-control" name="proxy_timeout" value="<?= intval($settings['proxy_timeout'] ?? 10) ?>">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">缓冲区大小（MB）</label>
                                        <input type="number" class="form-control" name="proxy_buffer_size" value="<?= intval($settings['proxy_buffer_size'] ?? 8) ?>">
                                        <small class="text-muted">实际字节数为此值乘以1024的平方，例如：8表示8MB</small>
                                    </div>
                                    <div class="form-group">
                                        <label>
                                            <input type="checkbox" name="clear_logs_on_stop" value="1" <?php echo isset($settings['clear_logs_on_stop']) && $settings['clear_logs_on_stop'] ? 'checked' : ''; ?>>
                                            停止时清空日志
                                        </label>
                                        <p class="help-block">选中后，停止代理服务时会自动清空错误日志和应用日志</p>
                                    </div>

                                    <div class="form-group">
                                        <label>
                                            <input type="checkbox" name="clear_connections" value="1"  <?php echo isset($settings['clear_connections']) && $settings['clear_connections'] ? 'checked' : ''; ?>>
                                            止服务时清空连接记录
                                        </label>
                                        <p class="help-block">选中后，停止代理服务器时将清空所有连接记录</p>
                                    </div>

                                </div>
                            </div>
                        </div>

                        <!-- 缓存设置 -->
                        <div class="tab-pane fade" id="cache" role="tabpanel">
                            <div class="card">
                                <div class="card-body">
                                    <div class="form-group">
                                        <label>缓存模式</label>
                                        <div class="custom-control custom-checkbox">
                                            <input type="checkbox" class="custom-control-input" id="enable_memory_cache" name="enable_memory_cache" value="1" <?php echo isset($settings['enable_memory_cache']) && $settings['enable_memory_cache'] == '1' ? 'checked' : ''; ?>>
                                            <label class="custom-control-label" for="enable_memory_cache">启用内存缓存（更快的响应速度，占用内存）</label>
                                        </div>
                                        <div class="custom-control custom-checkbox">
                                            <input type="checkbox" class="custom-control-input" id="enable_redis_cache" name="enable_redis_cache" value="1" <?php echo isset($settings['enable_redis_cache']) && $settings['enable_redis_cache'] == '1' ? 'checked' : ''; ?>>
                                            <label class="custom-control-label" for="enable_redis_cache">启用Redis缓存（持久化存储，支持分布式）</label>
                                        </div>
                                        <small class="form-text text-muted">
                                            - 同时启用两种缓存可以在高并发环境下获得最佳性能<br>
                                            - 仅启用Redis缓存适合内存受限但需要缓存的场景<br>
                                            - 仅启用内存缓存适合单机高性能场景<br>
                                            - 全部禁用适合带宽充足但资源受限的场景
                                        </small>
                                    </div>

                                    <!-- 添加内存缓存时间设置 -->
                                    <div class="form-group mt-3">
                                        <label for="memory_cache_ttl">内存缓存时间（秒）</label>
                                        <input type="number" class="form-control" id="memory_cache_ttl" name="memory_cache_ttl" 
                                            value="<?php echo $settings['memory_cache_ttl'] ?? '60'; ?>" min="10" max="300">
                                        <small class="form-text text-muted">设置内存缓存的过期时间，范围：10-300秒</small>
                                    </div>

                                    <!-- 添加Redis缓存时间设置 -->
                                    <div class="form-group mt-3">
                                        <label for="redis_cache_ttl">Redis缓存时间（秒）</label>
                                        <input type="number" class="form-control" id="redis_cache_ttl" name="redis_cache_ttl" 
                                            value="<?php echo $settings['redis_cache_ttl'] ?? '300'; ?>" min="10" max="3600">
                                        <small class="form-text text-muted">设置Redis缓存的过期时间，范围：10-3600秒</small>
                                    </div>
                                    
                                    <div class="form-group mt-3">
                                        <label for="cache_cleanup_interval">缓存清理间隔（秒）</label>
                                        <input type="number" class="form-control" id="cache_cleanup_interval" name="cache_cleanup_interval" value="<?php echo $settings['cache_cleanup_interval'] ?? '300'; ?>" min="10" max="3600">
                                        <small class="form-text text-muted">设置自动清理过期缓存的时间间隔，建议设置在60-3600秒之间</small>
                                    </div>
                                    
                                    <div class="form-group mt-3">
                                        <label for="max_memory_cache_size">最大内存缓存大小（MB）</label>
                                        <input type="number" class="form-control" id="max_memory_cache_size" name="max_memory_cache_size" value="<?php echo $settings['max_memory_cache_size'] ?? '256'; ?>" min="128" max="4096">
                                        <small class="form-text text-muted">设置内存缓存的最大使用空间，超出后将自动清理最旧的缓存</small>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Redis设置 -->
                        <div class="tab-pane fade" id="redis" role="tabpanel">
                            <div class="card">
                                <div class="card-body">
                                    <div class="mb-3">
                                        <label class="form-label">Redis 主机</label>
                                        <input type="text" name="redis_host" class="form-control" value="<?= $settings['redis_host'] ?? '127.0.0.1' ?>">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Redis 端口</label>
                                        <input type="number" name="redis_port" class="form-control" value="<?= $settings['redis_port'] ?? 6379 ?>">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Redis 密码</label>
                                        <input type="password" name="redis_password" class="form-control" value="<?= $settings['redis_password'] ?? '' ?>">
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 监控设置 -->
                        <div class="tab-pane fade" id="monitor" role="tabpanel">
                            <div class="card">
                                <div class="card-body">
                                    <div class="mb-3">
                                        <label class="form-label">实时监控刷新时间（秒）</label>
                                        <input type="number" name="monitor_refresh_interval" class="form-control" value="<?= $settings['monitor_refresh_interval'] ?? 5 ?>">
                                        <div class="form-text">设置监控页面自动刷新的时间间隔</div>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">服务状态检查间隔（秒）</label>
                                        <input type="number" name="status_check_interval" class="form-control" value="<?= $settings['status_check_interval'] ?? 10 ?>">
                                        <div class="form-text">设置检查代理服务运行状态的时间间隔</div>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">状态更新Redis键名</label>
                                        <input type="text" name="monitor_cache_stats" class="form-control" value="<?= $settings['monitor_cache_stats'] ?? 'monitor:cache_stats' ?>">
                                        <div class="form-text">因多个服务需要更新状态，所以需要一个Redis键来存储状态信息</div>
                                    </div>
                                    
                                </div>

                            </div>
                        </div>

                        <!-- 频道检查设置 -->
                        <div class="tab-pane fade" id="check" role="tabpanel">
                            <div class="card">
                                <div class="card-body">
                                    <div class="mb-3">
                                        <div class="form-check mb-2">
                                            <input class="form-check-input" type="radio" name="check_mode" id="daily_check" 
                                                   value="daily" <?= ($settings['check_mode'] ?? 'daily') === 'daily' ? 'checked' : '' ?>>
                                            <label class="form-check-label" for="daily_check">
                                                每天定时检查
                                            </label>
                                        </div>
                                        <div class="ms-4 mb-3" id="daily_time_container">
                                            <label class="form-label">检查时间</label>
                                            <input type="time" name="daily_check_time" class="form-control" 
                                                   value="<?= $settings['daily_check_time'] ?? '03:00' ?>">
                                        </div>

                                        <div class="form-check">
                                            <input class="form-check-input" type="radio" name="check_mode" id="interval_check" 
                                                   value="interval" <?= ($settings['check_mode'] ?? 'daily') === 'interval' ? 'checked' : '' ?>>
                                            <label class="form-check-label" for="interval_check">
                                                间隔检查
                                            </label>
                                        </div>
                                        <div class="ms-4" id="interval_time_container">
                                            <label class="form-label">检查间隔（小时）</label>
                                            <input type="number" name="check_interval" class="form-control" 
                                                   value="<?= $settings['check_interval'] ?? 6 ?>">
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="text-end mt-3">
                        <button type="submit" class="btn btn-primary">保存设置</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    <?php require __DIR__ . '/../../footer.php'; ?>
    <script src="/css/bootstrap.bundle.min.js"></script>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const dailyCheck = document.getElementById('daily_check');
        const intervalCheck = document.getElementById('interval_check');
        const dailyTimeContainer = document.getElementById('daily_time_container');
        const intervalTimeContainer = document.getElementById('interval_time_container');

        function updateVisibility() {
            dailyTimeContainer.style.display = dailyCheck.checked ? 'block' : 'none';
            intervalTimeContainer.style.display = intervalCheck.checked ? 'block' : 'none';
        }

        dailyCheck.addEventListener('change', updateVisibility);
        intervalCheck.addEventListener('change', updateVisibility);

        // 初始化显示状态
        updateVisibility();

        // 如果URL中有hash，激活对应的标签
        let hash = window.location.hash;
        if (hash) {
            const tab = document.querySelector(`a[href="${hash}"]`);
            if (tab) {
                new bootstrap.Tab(tab).show();
            }
        }

        // 当标签切换时，更新URL hash
        const tabs = document.querySelectorAll('a[data-bs-toggle="tab"]');
        tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', function (e) {
                window.location.hash = e.target.getAttribute('href');
            });
        });
    });

    // AJAX 提交表单
    document.getElementById('settingsForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const data = {};
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        fetch('/admin/settings/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('设置已保存');
                // 保持在当前标签页
                const currentHash = window.location.hash;
                location.href = location.pathname + currentHash;
            } else {
                alert(data.message || '保存失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('保存失败');
        });
    });
    </script>
</body>
</html> 