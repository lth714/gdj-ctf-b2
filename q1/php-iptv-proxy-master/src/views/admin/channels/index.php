<?php
function buildUrl($params) 
{
    $current = array();
    if (isset($_GET)) {
        $current = $_GET;
    }
    
    if (is_array($params)) {
        foreach ($params as $key => $value) {
            if ($value === null) {
                unset($current[$key]);
            } else {
                $current[$key] = $value;
            }
        }
    }
    
    return '?' . http_build_query($current);
}
?>
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>频道管理 - IPTV 代理系统</title>
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="/css/all.min.css" rel="stylesheet">
    <style>
    .btn-group-sm .btn {
        padding: 0.1rem 0.3rem;
        font-size: 0.75rem;
    }
    th {
        white-space: nowrap;
    }
    /* 表格单元格样式 */
    .table td {
        vertical-align: middle;
        white-space: nowrap;
    }
    
    /* URL列样式 */
    .url-cell {
        max-width: 250px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    /* 操作列样式 */
    .actions-cell {
        white-space: nowrap;
        width: 1%;  /* 让操作列宽度自适应内容 */
    }
    
    /* 确保表格横向滚动而不是换行 */
    .table-responsive {
        min-height: 300px;
    }
    </style>
</head>
<body>
    <?php $currentPage = 'channels'; ?>
    <?php require __DIR__ . '/../../navbar.php'; ?>

    <div class="container-fluid mx-auto" style="width: 98%;>
        <div class="row">
            <div class="col-md-12">
                <div class="d-flex justify-content-between align-items-center">
                    <h2>频道管理</h2>
                    <div>
                        <select class="form-select form-select-sm d-inline-block me-2" style="width: auto;" onchange="filterByGroup(this.value)">
                            <option value="">所有分组</option>
                            <option value="0" <?php echo (isset($_GET['group_id']) && $_GET['group_id'] === '0' ? 'selected' : ''); ?>>未分组</option>
                            <?php foreach ($groups as $group): ?>
                            <option value="<?php echo $group['id']; ?>" <?php echo (isset($_GET['group_id']) && $_GET['group_id'] == $group['id'] ? 'selected' : ''); ?>>
                                <?php echo htmlspecialchars($group['name']); ?> (<?php echo $group['channel_count']; ?>)
                            </option>
                            <?php endforeach; ?>
                        </select>
                        <button onclick="checkSelected()" class="btn btn-warning btn-sm me-2">检查所选</button>
                        <button onclick="checkCurrentGroup()" class="btn btn-warning btn-sm me-2">检查当前分组</button>
                        <button onclick="checkAll()" class="btn btn-warning btn-sm me-2">检查全部</button>
                        <button onclick="deleteSelected()" class="btn btn-danger btn-sm me-2">删除所选</button>
                        <button onclick="deleteAll()" class="btn btn-danger btn-sm me-2">清空列表</button>
                        <a href="/admin/channels/import" class="btn btn-success btn-sm me-2">导入频道</a>
                        <a href="/admin/channels/add" class="btn btn-primary btn-sm">添加频道</a>
                    </div>
                </div>
                <?php
                if (isset($_SESSION['flash_message'])) {
                    $message = $_SESSION['flash_message'];
                    $alertClass = $message['type'] === 'success' ? 'alert-success' : 'alert-danger';
                    echo "<div class='alert {$alertClass} mt-3'>{$message['message']}</div>";
                    unset($_SESSION['flash_message']);
                }
                ?>
                <div class="d-flex justify-content-between align-items-center mt-2">
                    <div class="d-flex align-items-center">
                        <span class="me-3">共 <?php echo $pagination['total']; ?> 条记录</span>
                        <select class="form-select form-select-sm" style="width: auto;" onchange="changePageSize(this.value)">
                            <option value="10" <?php echo (isset($_GET['per_page']) && $_GET['per_page'] == '10') ? 'selected' : ''; ?>>10条/页</option>
                            <option value="20" <?php echo (isset($_GET['per_page']) && $_GET['per_page'] == '20') ? 'selected' : ''; ?>>20条/页</option>
                            <option value="50" <?php echo (!isset($_GET['per_page']) || $_GET['per_page'] == '50') ? 'selected' : ''; ?>>50条/页</option>
                            <option value="100" <?php echo (isset($_GET['per_page']) && $_GET['per_page'] == '100') ? 'selected' : ''; ?>>100条/页</option>
                        </select>
                    </div>
                </div>
                
                <div class="table-responsive mt-4">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th style="width: 40px;">
                                    <input type="checkbox" class="form-check-input" id="selectAll" onclick="toggleAll(this)">
                                </th>
                                <th style="width: 60px;text-align: center;">ID</th>
                                <th style="width: 150px;text-align: center;">名称</th>
                                <th style="width: 100px;text-align: center;">分组</th>
                                <th style="width: 250px;text-align: center;">源地址</th>
                                <th style="width: 250px;text-align: center;">代理地址</th>
                                <th style="width: 80px;text-align: center;">状态</th>
                                <th style="width: 80px;text-align: center;">延时</th>
                                <th style="width: 80px;text-align: center;">连接数</th>
                                <th style="width: 120px;text-align: center;">上行带宽</th>
                                <th style="width: 120px;text-align: center;">下行带宽</th>
                                <th style="width: 100px;text-align: center;">检查时间</th>
                                <th style="width: 80px;text-align: center;">异常次数</th>
                                <th class="actions-cell">操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($channels as $channel): ?>
                            <tr id="channel-<?= $channel['id'] ?>">
                                <td>
                                    <input type="checkbox" class="channel-select" value="<?= $channel['id'] ?>">
                                </td>
                                <td><?= $channel['id'] ?></td>
                                <td><?= htmlspecialchars($channel['name']) ?></td>
                                <td><?= htmlspecialchars($channel['group_name'] ?? '未分组') ?></td>
                                <td class="url-cell" title="<?= htmlspecialchars($channel['source_url']) ?>">
                                    <?= htmlspecialchars($channel['source_url']) ?>
                                </td>
                                <td class="url-cell" title="<?= $channel['proxy_url'] ? htmlspecialchars($channel['proxy_url']) : '未生成代理地址' ?>">
                                    <?= $channel['proxy_url'] ? htmlspecialchars($channel['proxy_url']) : '<span class="text-muted">未生成代理地址</span>' ?>
                                </td>
                                <td class="status-icon" style="text-align: center;">
                                    <span class="badge bg-<?php 
                                        if ($channel['status'] === 'active') echo 'success';
                                        else if ($channel['status'] === 'error') echo 'danger';
                                        else echo 'secondary';
                                    ?>">
                                        <?php 
                                        if ($channel['status'] === 'active') echo '正常';
                                        else if ($channel['status'] === 'error') echo '异常';
                                        else echo '未启用';
                                        ?>
                                    </span>
                                </td>
                                <td class="latency-cell" style="text-align: center;">
                                    <?= $channel['status'] === 'active' ? $channel['latency'].'ms' : '-' ?>
                                </td>
                                <td style="text-align: center;"><?= $channel['connections'] ?? 0 ?></td>
                                <td style="text-align: center;"><?= isset($channel['upload_bandwidth']) ? number_format($channel['upload_bandwidth'], 2) : '0' ?> MB/s</td>
                                <td style="text-align: center;"><?= isset($channel['download_bandwidth']) ? number_format($channel['download_bandwidth'], 2) : '0' ?> MB/s</td>
                                <td class="checked-at-cell" style="text-align: center;"><?= $channel['checked_at'] ? date('Y-m-d H:i:s', strtotime($channel['checked_at'])) : '-' ?></td>
                                <td class="error-count-cell" style="text-align: center;">
                                    <?php if ($channel['status'] === 'error'): ?>
                                        <span class="badge bg-warning"><?= $channel['error_count'] ?></span>
                                    <?php else: ?>
                                        <span>0</span>
                                    <?php endif; ?>
                                </td>
                                <td class="actions-cell">
                                    <div class="btn-group btn-group-sm">
                                        <button type="button" class="btn btn-primary" onclick="checkChannel(<?= $channel['id'] ?>)">检查</button>
                                        <a href="/admin/channels/edit/<?= $channel['id'] ?>" class="btn btn-secondary">编辑</a>
                                        <button type="button" class="btn btn-danger" onclick="deleteChannel(<?= $channel['id'] ?>)">删除</button>
                                    </div>
                                </td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
                <?php if (isset($pagination) && isset($pagination['totalPages']) && $pagination['totalPages'] > 1): ?>
                <nav aria-label="Page navigation" class="mt-3">
                    <ul class="pagination justify-content-center">
                        <?php
                        $current = isset($pagination['current']) ? (int)$pagination['current'] : 1;
                        $total = isset($pagination['totalPages']) ? (int)$pagination['totalPages'] : 1;
                        ?>
                        <li class="page-item <?php echo ($current == 1 ? 'disabled' : ''); ?>">
                            <a class="page-link" href="<?php echo buildUrl(array('page' => 1)); ?>">首页</a>
                        </li>
                        <li class="page-item <?php echo ($current == 1 ? 'disabled' : ''); ?>">
                            <a class="page-link" href="<?php echo buildUrl(array('page' => $current - 1)); ?>">上一页</a>
                        </li>
                        <?php
                        $start = max(1, $current - 2);
                        $end = min($total, $current + 2);
                        for ($i = $start; $i <= $end; $i++):
                        ?>
                        <li class="page-item <?php echo ($i == $current ? 'active' : ''); ?>">
                            <a class="page-link" href="<?php echo buildUrl(array('page' => $i)); ?>"><?= $i ?></a>
                        </li>
                        <?php endfor; ?>
                        <li class="page-item <?php echo ($current == $total ? 'disabled' : ''); ?>">
                            <a class="page-link" href="<?php echo buildUrl(array('page' => $current + 1)); ?>">下一页</a>
                        </li>
                        <li class="page-item <?php echo ($current == $total ? 'disabled' : ''); ?>">
                            <a class="page-link" href="<?php echo buildUrl(array('page' => $total)); ?>">末页</a>
                        </li>
                    </ul>
                </nav>
                <?php endif; ?>
            </div>
        </div>
    </div>

    <div class="modal fade" id="checkProgressModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">检查进度</h5>
                </div>
                <div class="modal-body">
                    <div class="progress">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" style="width: 0%">0%</div>
                    </div>
                    <div id="checkStatus" class="mt-2"></div>
                </div>
            </div>
        </div>
    </div>
	<?php require __DIR__ . '/../../footer.php'; ?>
    <script src="/css/bootstrap.bundle.min.js"></script>
    <script>
    let checkModal;
    let currentCheckTask = null;
    let connectionUpdateInterval = null;
    let checkIntervalTime = <?= intval($settings['status_check_interval'] ?? 10) ?> * 1000;

    function buildUrl(params) {
        const current = new URLSearchParams(window.location.search);
        
        // 更新或添加新参数
        Object.entries(params).forEach(([key, value]) => {
            if (value === null || value === '') {
                current.delete(key);
            } else {
                current.set(key, value);
            }
        });
        
        return '?' + current.toString();
    }

    document.addEventListener('DOMContentLoaded', function() {
        checkModal = new bootstrap.Modal(document.getElementById('checkProgressModal'));
        
        // 开始定时更新连接数
        startConnectionUpdates();
    });

    // 更新连接统计信息
    function updateConnectionStats() {
        fetch('/admin/proxy/connection-stats')
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    // 更新每个频道的连接数
                    result.data.channel_connections.forEach(channel => {
                        const row = document.getElementById(`channel-${channel.id}`);
                        if (row) {
                            const connectionCell = row.querySelector('td:nth-child(9)');
                            if (connectionCell) {
                                connectionCell.textContent = channel.connections;
                            }
                        }
                    });
                }
            })
            .catch(error => {
                console.error('获取连接统计失败:', error);
            });
    }
    // 更新带宽统计信息
    function updateBandwidthStats() {
        fetch('/admin/proxy/bandwidth-stats')
            .then(response => response.json())
            .then(result => {
                if (result.success && result.data.channels) {
                    Object.entries(result.data.channels).forEach(([channelId, channelData]) => {
                        const row = document.getElementById(`channel-${channelId}`);
                        if (row) {
                            const uploadCell = row.querySelector('td:nth-child(10)');
                            const downloadCell = row.querySelector('td:nth-child(11)');
                            
                            if (uploadCell && downloadCell && channelData.stats) {
                                uploadCell.textContent = channelData.stats.bandwidth.upload;
                                downloadCell.textContent = channelData.stats.bandwidth.download;
                            }
                        }
                    });
                }
            })
            .catch(error => {
                console.error('获取带宽统计失败:', error);
            });
    }
    function startConnectionUpdates() {
        // 清除现有的定时器
        if (connectionUpdateInterval) {
            clearInterval(connectionUpdateInterval);
        }
    
        // 立即更新一次
        updateConnectionStats();
        updateBandwidthStats();
    
        // 设置定时更新
        connectionUpdateInterval = setInterval(function() {
            updateConnectionStats();
            updateBandwidthStats();
        }, checkIntervalTime);
    }

    // 在页面卸载时清除定时器
    window.addEventListener('beforeunload', function() {
        if (connectionUpdateInterval) {
            clearInterval(connectionUpdateInterval);
        }
    });

    function updateProgress(progress, status) {
        const progressBar = document.querySelector('#checkProgressModal .progress-bar');
        const statusDiv = document.getElementById('checkStatus');
        progressBar.style.width = progress + '%';
        progressBar.textContent = progress + '%';
        if (status) {
            statusDiv.textContent = status;
        }
    }

    async function checkChannel(id) {
        try {
            const response = await fetch(`/admin/channels/check/${id}`);
            if (!response.ok) {
                throw new Error('网络请求失败');
            }
            const result = await response.json();
            
            // 更新UI
            const row = document.getElementById(`channel-${id}`);
            if (row) {
                // 更新状态
                const statusCell = row.querySelector('.status-icon');
                if (statusCell) {
                    const badge = statusCell.querySelector('.badge');
                    if (badge) {
                        badge.className = `badge bg-${result.status === 'active' ? 'success' : 'danger'}`;
                        badge.textContent = result.status === 'active' ? '正常' : '异常';
                    }
                }
                
                // 更新延时
                const latencyCell = row.querySelector('.latency-cell');
                if (latencyCell) {
                    latencyCell.textContent = result.status === 'active' ? `${result.latency}ms` : '-';
                }
                
                // 更新检查时间
                const checkedAtCell = row.querySelector('.checked-at-cell');
                if (checkedAtCell && result.checked_at) {
                    checkedAtCell.textContent = result.checked_at;
                }
                
                // 更新错误次数
                const errorCountCell = row.querySelector('.error-count-cell');
                if (errorCountCell) {
                    if (result.status === 'error') {
                        errorCountCell.innerHTML = `<span class="badge bg-warning">${result.error_count}</span>`;
                    } else {
                        errorCountCell.innerHTML = '<span>0</span>';
                    }
                }
            }

            // 如果频道被删除，显示提示并刷新页面
            if (result.deleted) {
                alert(result.message);
                location.reload();
                return;
            }

            // 显示检查结果
            if (!result.success) {
                alert(result.message);
            }
        } catch (error) {
            console.error('检查频道失败:', error);
            alert('检查频道失败: ' + error.message);
        }
    }

    function checkSelected() {
        const selectedChannels = Array.from(document.querySelectorAll('.channel-select:checked')).map(cb => cb.value);
        if (selectedChannels.length === 0) {
            alert('请选择要检查的频道');
            return;
        }
        
        checkChannels(selectedChannels);
    }

    function checkCurrentGroup() {
        const allChannels = Array.from(document.querySelectorAll('.channel-select')).map(cb => cb.value);
        if (allChannels.length === 0) {
            alert('当前分组没有频道');
            return;
        }
        
        checkChannels(allChannels);
    }

    function checkAll() {
        if (!confirm('确定要检查所有频道吗？这可能需要较长时间。')) {
            return;
        }
        
        fetch('/admin/channels/check-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('网络请求失败');
            }
            return response.json();
        })
        .then(result => {
            if (result.success) {
                currentCheckTask = result.taskId;
                checkModal.show();
                monitorProgress();
            } else {
                alert(result.message || '启动检查任务失败');
            }
        })
        .catch(error => {
            console.error('启动检查任务失败:', error);
            alert('启动检查任务失败: ' + error.message);
        });
    }

    async function checkChannels(channelIds) {
        try {
            const response = await fetch('/admin/channels/check-multiple', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ ids: channelIds })
            });
            
            if (!response.ok) {
                throw new Error('网络请求失败');
            }

            const result = await response.json();
            if (result.success) {
                currentCheckTask = result.taskId;
                checkModal.show();
                monitorProgress();
            } else {
                alert(result.message || '启动检查任务失败');
            }
        } catch (error) {
            console.error('启动检查任务失败:', error);
            alert('启动检查任务失败: ' + error.message);
        }
    }

    function monitorProgress() {
        if (!currentCheckTask) return;
        
        const checkProgress = () => {
            fetch(`/admin/channels/check-progress/${currentCheckTask}`)
                .then(response => response.json())
                .then(result => {
                    updateProgress(result.progress, result.status);
                    
                    if (result.progress < 100) {
                        setTimeout(checkProgress, 1000);
                    } else {
                        setTimeout(() => {
                            checkModal.hide();
                            location.reload();
                        }, 1000);
                    }
                })
                .catch(error => {
                    console.error('获取进度失败:', error);
                    checkModal.hide();
                });
        };
        
        checkProgress();
    }

    function toggleAll(checkbox) {
        document.querySelectorAll('.channel-select').forEach(cb => {
            cb.checked = checkbox.checked;
        });
    }

    function filterByGroup(groupId) {
        location.href = buildUrl({ group_id: groupId, page: 1 });
    }

    function changePageSize(size) {
        location.href = buildUrl({ per_page: size, page: 1 });
    }

    function deleteChannel(id) {
        if (!confirm('确定要删除这个频道吗？')) {
            return;
        }
        
        fetch(`/admin/channels/delete/${id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('网络请求失败');
            }
            return response.json();
        })
        .then(result => {
            if (result.success) {
                const row = document.getElementById(`channel-${id}`);
                if (row) {
                    row.remove();
                }
            } else {
                alert(result.message || '删除频道失败');
            }
        })
        .catch(error => {
            console.error('删除频道失败:', error);
            alert('删除频道失败: ' + error.message);
        });
    }

    function deleteSelected() {
        const selectedChannels = Array.from(document.querySelectorAll('.channel-select:checked')).map(cb => cb.value);
        if (selectedChannels.length === 0) {
            alert('请选择要删除的频道');
            return;
        }
        
        if (!confirm(`确定要删除选中的 ${selectedChannels.length} 个频道吗？`)) {
            return;
        }
        
        fetch('/admin/channels/delete-multiple', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ids: selectedChannels })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                location.reload();
            } else {
                alert(result.message);
            }
        })
        .catch(error => {
            console.error('删除频道失败:', error);
            alert('删除频道失败');
        });
    }

    function deleteAll() {
        if (!confirm('确定要清空所有频道吗？此操作不可恢复！')) {
            return;
        }
        
        if (!confirm('再次确认：是否要删除所有频道？')) {
            return;
        }
        
        fetch('/admin/channels/delete-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('网络请求失败');
            }
            return response.json();
        })
        .then(result => {
            if (result.success) {
                location.reload();
            } else {
                alert(result.message || '清空频道失败');
            }
        })
        .catch(error => {
            console.error('清空频道失败:', error);
            alert('清空频道失败: ' + error.message);
        });
    }
    </script>
</body>
</html> 
</html> 