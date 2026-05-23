<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>错误日志 - IPTV 代理系统</title>
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="/css/all.min.css" rel="stylesheet">
    <link href="/css/bootstrap-datepicker.min.css" rel="stylesheet">
</head>
<body>
    <?php $currentPage = 'error_logs'; ?>
    <?php require __DIR__ . '/../../navbar.php'; ?>

    <div class="container-fluid">
        <h2 class="mb-4">错误日志</h2>

        <!-- 筛选表单 -->
        <div class="card mb-4">
            <div class="card-body">
                <form id="filterForm" class="row g-3">
                    <div class="col-md-3">
                        <label class="form-label">错误类型</label>
                        <select class="form-select" name="type">
                            <option value="">全部</option>
                            <option value="connection">连接错误</option>
                            <option value="timeout">超时</option>
                            <option value="http">HTTP错误</option>
                            <option value="other">其他错误</option>
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

        <!-- 日志表格 -->
        <div class="card">
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover" id="logsTable">
                        <thead>
                            <tr>
                                <th>时间</th>
                                <th>频道</th>
                                <th>类型</th>
                                <th>错误信息</th>
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

        fetch('/admin/monitor/logs?' + params.toString())
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateTable(data.data.logs);
                    updatePagination(data.data.total, data.data.totalPages);
                }
            });
    }

    function updateTable(logs) {
        const tbody = document.querySelector('#logsTable tbody');
        tbody.innerHTML = '';

        logs.forEach(log => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${log.created_at}</td>
                <td>${log.channel_name || '-'}</td>
                <td>
                    <span class="badge bg-${getTypeColor(log.type)}">
                        ${getTypeLabel(log.type)}
                    </span>
                </td>
                <td>${log.message}</td>
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

    function getTypeColor(type) {
        switch (type) {
            case 'connection': return 'danger';
            case 'timeout': return 'warning';
            case 'http': return 'info';
            default: return 'secondary';
        }
    }

    function getTypeLabel(type) {
        switch (type) {
            case 'connection': return '连接错误';
            case 'timeout': return '超时';
            case 'http': return 'HTTP错误';
            default: return '其他错误';
        }
    }
    </script>
</body>
</html>