<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统安装 - 数据库配置</title>
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {
            background-color: #f5f8fa;
        }
        .install-container {
            max-width: 800px;
            margin: 30px auto;
        }
        .step-indicator {
            display: flex;
            justify-content: center;
            margin-bottom: 30px;
        }
        .step {
            padding: 8px 20px;
            margin: 0 5px;
            background: #fff;
            border-radius: 20px;
            font-weight: 500;
            color: #6B7280;
        }
        .step.active {
            background: #3B82F6;
            color: #fff;
        }
        .step.completed {
            background: #10B981;
            color: #fff;
        }
        .form-floating > label {
            left: 8px;
        }
    </style>
</head>
<body>
    <div class="install-container">
        <!-- 步骤指示器 -->
        <div class="step-indicator">
        <div class="step completed">
            <i class="bi bi-check-circle"></i> 环境检查
        </div>
        <div class="step active">
            <i class="bi bi-check-circle"></i> 数据库配置
        </div>
        <div class="step">
            <i class="bi bi-3-circle-fill"></i> Redis配置
        </div>
        <div class="step">
            <i class="bi bi-4-circle"></i> 管理员设置
        </div>
        <div class="step">
            <i class="bi bi-5-circle"></i> 完成安装
        </div>
    </div>

        <div class="card">
            <div class="card-header bg-white py-3">
                <h3 class="card-title mb-0">数据库配置</h3>
            </div>
            <div class="card-body">
                <form id="dbConfigForm" class="needs-validation" novalidate>
                    <div class="row g-3">
                        <div class="col-md-8">
                            <div class="form-floating">
                                <input type="text" class="form-control" id="db_host" name="db_host" value="localhost" required>
                                <label for="db_host">数据库主机</label>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-floating">
                                <input type="text" class="form-control" id="db_port" name="db_port" value="3306" required>
                                <label for="db_port">端口</label>
                            </div>
                        </div>
                    </div>

                    <div class="form-floating mt-3">
                        <input type="text" class="form-control" id="db_name" name="db_name" value="iptv_proxy" required>
                        <label for="db_name">数据库名称</label>
                    </div>

                    <div class="form-floating mt-3">
                        <input type="text" class="form-control" id="db_user" name="db_user" required>
                        <label for="db_user">数据库用户名</label>
                    </div>

                    <div class="form-floating mt-3">
                        <input type="password" class="form-control" id="db_pass" name="db_pass" required>
                        <label for="db_pass">数据库密码</label>
                    </div>

                    <div class="mt-4">
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i> 提示：
                            <ul class="mb-0">
                                <li>请确保数据库用户具有创建数据库的权限</li>
                                <li>如果数据库已存在，将会被重置</li>
                                <li>建议使用独立的数据库用户</li>
                            </ul>
                        </div>
                    </div>

                    <div class="mt-4 text-center">
                        <a href="?step=1" class="btn btn-secondary me-2">
                            <i class="bi bi-arrow-left"></i> 上一步
                        </a>
                        <button type="button" class="btn btn-info me-2" id="testConnectionBtn" onclick="testConnection()">
                            <i class="bi bi-database-check"></i> 测试连接
                        </button>
                        <button type="button" class="btn btn-primary" id="configureDbBtn" disabled>
                            <i class="bi bi-arrow-right"></i> 下一步
                        </button>
                    </div>
                </form>
            </div>
        </div>

    <script src="/css/bootstrap.bundle.min.js"></script>
    <script src="/js/axios.min.js"></script>
    <script>
    async function testConnection() {
        const testBtn = document.getElementById('testConnectionBtn');
        const configureBtn = document.getElementById('configureDbBtn');
        
        testBtn.disabled = true;
        testBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 测试中...';

        try {
            const formData = new FormData(document.getElementById('dbConfigForm'));
            const response = await axios.post('install.php?step=2&action=test', formData);
            
            if (response.data.success) {
                if (response.data.db_exists) {
                    if (confirm('数据库已存在！继续安装将清空所有现有数据，请确保已备份重要数据。是否继续？')) {
                        configureBtn.disabled = false;
                    }
                } else {
                    configureBtn.disabled = false;
                }
                alert('数据库连接成功！');
            } else {
                alert(response.data.message);
            }
        } catch (error) {
            alert('连接测试失败: ' + (error.response?.data?.message || error.message));
        } finally {
            testBtn.disabled = false;
            testBtn.innerHTML = '<i class="bi bi-database-check"></i> 测试连接';
        }
    }

    // 为下一步按钮添加点击事件监听器
    document.getElementById('configureDbBtn').addEventListener('click', async function() {
        const configureBtn = this;
        configureBtn.disabled = true;
        configureBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 配置中...';

        try {
            const formData = new FormData(document.getElementById('dbConfigForm'));
            const response = await axios.post('install.php?step=2&action=configure', formData);
            
            if (response.data.success) {
                alert('数据库配置成功，初始化完成！');
                window.location.href = 'install.php?step=3';
            } else {
                alert(response.data.message);
            }
        } catch (error) {
            alert('配置失败: ' + (error.response?.data?.message || error.message));
        } finally {
            configureBtn.disabled = false;
            configureBtn.innerHTML = '<i class="bi bi-arrow-right"></i> 下一步';
        }
    });
    </script>
</body>
</html>