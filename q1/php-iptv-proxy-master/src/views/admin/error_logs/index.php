<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>错误日志 - IPTV 代理系统</title>
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="/css/all.min.css" rel="stylesheet">
    <link href="/css/bootstrap-datepicker.min.css" rel="stylesheet">
    <style>
        .error-message {
            max-width: 500px;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .error-details {
            font-size: 0.9em;
            color: #666;
        }
        .toast {
            z-index: 1050;
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
        }
        .toast .toast-body {
            font-size: 1.1em;
            padding: 12px 24px;
        }
    </style>
</head>
<body>
    <?php $currentPage = 'error_logs'; ?>
    <?php require __DIR__ . '/../../navbar.php'; ?>

    <!-- Toast容器 -->
    <div class="toast-container"></div>

    <div class="container-fluid">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>错误日志，共<?php echo number_format($errorCount); ?> 条记录</h2>
            <button type="button" class="btn btn-danger" onclick="confirmClearLogs()">
                <i class="fas fa-trash-alt me-1"></i> 清空日志
            </button>
        </div>

        <!-- 筛选表单 -->
        <div class="card mb-4">
            <div class="card-body">
                <form id="filterForm" class="row g-3">
                    <div class="col-md-3">
                        <label class="form-label">错误类型</label>
                        <select class="form-select" name="type">
                            <option value="">全部</option>
                            <option value="error">错误</option>
                            <option value="warning">警告</option>
                            <option value="info">信息</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">开始日期</label>
                        <input type="text" class="form-control datepicker" name="start_date">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">结束日期</label>
                        <input type="text" class="form-control datepicker" name="end_date">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">&nbsp;</label>
                        <button type="submit" class="btn btn-primary d-block">查询</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- 确认清空日志的模态框 -->
        <div class="modal fade" id="clearLogsModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">确认清空日志</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            此操作将清空所有错误日志记录，且无法恢复。是否确定继续？
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-danger" onclick="clearLogs()">
                            <i class="fas fa-trash-alt me-1"></i> 确认清空
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- 日志表格 -->
        <div class="card">
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover" id="logsTable">
                        <thead>
                            <tr>
                                <th>时间</th>
                                <th>级别</th>
                                <th>错误信息</th>
                                <th>文件</th>
                                <th>行号</th>
                                <th>堆栈信息</th>
                            </tr>
                        </thead>
                        <tbody>
                        </tbody>
                    </table>
                </div>

                <!-- 分页 -->
                <nav aria-label="Page navigation" class="mt-3">
                    <ul class="pagination justify-content-center" id="pagination">
                    </ul>
                </nav>
            </div>
        </div>
    </div>

    <script src="/css/jquery.min.js"></script>
    <script src="/css/bootstrap.bundle.min.js"></script>
    <script src="/css/bootstrap-datepicker.min.js"></script>
    <script src="/css/bootstrap-datepicker.zh-CN.min.js"></script>
    <script>
    let currentPage = 1;
    
    $(document).ready(function() {
        // 初始化日期选择器
        $('.datepicker').datepicker({
            format: 'yyyy-mm-dd',
            language: 'zh-CN',
            autoclose: true
        });

        // 加载日志
        loadLogs();

        // 表单提交
        $('#filterForm').on('submit', function(e) {
            e.preventDefault();
            currentPage = 1;
            loadLogs();
        });
    });

    function loadLogs() {
        const formData = new FormData($('#filterForm')[0]);
        const params = new URLSearchParams(formData);
        params.append('page', currentPage);

        fetch('/admin/error-logs/data?' + params.toString())
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateTable(data.data.logs);
                    updatePagination(data.data.total, data.data.totalPages);
                } else {
                    console.error('加载日志失败:', data.message);
                }
            })
            .catch(error => {
                console.error('加载日志失败:', error);
            });
    }

    function updateTable(logs) {
        const tbody = document.querySelector('#logsTable tbody');
        tbody.innerHTML = '';

        logs.forEach(log => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${log.created_at}</td>
                <td>
                    <span class="badge bg-${getTypeColor(log.level)}">
                        ${getTypeLabel(log.level)}
                    </span>
                </td>
                <td class="error-message">${log.message}</td>
                <td>${log.file || '-'}</td>
                <td>${log.line || '-'}</td>
                <td class="error-details">${formatTrace(log.trace)}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    function updatePagination(total, totalPages) {
        const pagination = document.getElementById('pagination');
        pagination.innerHTML = '';

        // 首页
        pagination.appendChild(createPageItem(1, currentPage === 1, '首页'));
        
        // 上一页
        pagination.appendChild(createPageItem(currentPage - 1, currentPage === 1, '上一页'));

        // 页码
        let start = Math.max(1, currentPage - 2);
        let end = Math.min(totalPages, currentPage + 2);
        
        for (let i = start; i <= end; i++) {
            pagination.appendChild(createPageItem(i, false, i, currentPage === i));
        }

        // 下一页
        pagination.appendChild(createPageItem(currentPage + 1, currentPage === totalPages, '下一页'));
        
        // 末页
        pagination.appendChild(createPageItem(totalPages, currentPage === totalPages, '末页'));
    }

    function createPageItem(page, disabled, text, active = false) {
        const li = document.createElement('li');
        li.className = `page-item ${disabled ? 'disabled' : ''} ${active ? 'active' : ''}`;
        
        const a = document.createElement('a');
        a.className = 'page-link';
        a.href = '#';
        a.textContent = text;
        
        if (!disabled) {
            a.onclick = (e) => {
                e.preventDefault();
                currentPage = page;
                loadLogs();
            };
        }

        li.appendChild(a);
        return li;
    }

    function getTypeColor(level) {
        switch (level) {
            case 'error': return 'danger';
            case 'warning': return 'warning';
            case 'info': return 'info';
            default: return 'secondary';
        }
    }

    function getTypeLabel(level) {
        switch (level) {
            case 'error': return '错误';
            case 'warning': return '警告';
            case 'info': return '信息';
            default: return level;
        }
    }

    function formatTrace(trace) {
        if (!trace) return '-';
        try {
            const traceData = JSON.parse(trace);
            return traceData.map(t => {
                const file = t.file ? `${t.file}:${t.line}` : '';
                const func = t.function ? `${t.class ? t.class + t.type : ''}${t.function}` : '';
                return `${file} ${func}`;
            }).join('<br>');
        } catch (e) {
            return trace;
        }
    }

    function confirmClearLogs() {
        const modal = new bootstrap.Modal(document.getElementById('clearLogsModal'));
        modal.show();
    }

    function clearLogs() {
        fetch('/admin/error-logs/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 关闭模态框
                bootstrap.Modal.getInstance(document.getElementById('clearLogsModal')).hide();
                
                // 创建并显示成功提示
                const toastDiv = document.createElement('div');
                toastDiv.className = 'toast align-items-center text-white bg-success border-0';
                toastDiv.setAttribute('role', 'alert');
                toastDiv.setAttribute('aria-live', 'assertive');
                toastDiv.setAttribute('aria-atomic', 'true');
                toastDiv.innerHTML = `
                    <div class="d-flex">
                        <div class="toast-body">
                            <i class="fas fa-check-circle me-2"></i>
                            日志已成功清空
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                    </div>
                `;
                
                // 添加到Toast容器
                const container = document.querySelector('.toast-container');
                container.appendChild(toastDiv);
                
                const toast = new bootstrap.Toast(toastDiv, {
                    delay: 3000
                });
                toast.show();
                
                // 监听toast隐藏事件，移除DOM元素
                toastDiv.addEventListener('hidden.bs.toast', () => {
                    toastDiv.remove();
                });
                
                // 重新加载日志列表
                loadLogs();
            } else {
                alert('清空日志失败: ' + data.message);
            }
        })
        .catch(error => {
            console.error('清空日志失败:', error);
            alert('清空日志失败，请查看控制台获取详细信息');
        });
    }
    </script>
</body>
</html> 