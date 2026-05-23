<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统安装 - Redis配置</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
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
        <div class="step completed">
            <i class="bi bi-check-circle"></i> 数据库配置
        </div>
        <div class="step active">
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
                <h3 class="card-title mb-0">Redis配置</h3>
            </div>
            <div class="card-body">
                <form id="redisConfigForm" class="needs-validation" novalidate>
                    <div class="row g-3">
                        <div class="col-md-8">
                            <div class="form-floating">
                                <input type="text" class="form-control" id="redis_host" name="redis_host" value="127.0.0.1" required>
                                <label for="redis_host">Redis主机</label>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-floating">
                                <input type="text" class="form-control" id="redis_port" name="redis_port" value="6379" required>
                                <label for="redis_port">端口</label>
                            </div>
                        </div>
                    </div>

                    <div class="form-floating mt-3">
                        <input type="password" class="form-control" id="redis_pass" name="redis_pass">
                        <label for="redis_pass">Redis密码（如果有）</label>
                    </div>

                    <div class="mt-4">
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i> 提示：
                            <ul class="mb-0">
                                <li>Redis用于缓存和会话管理</li>
                                <li>如果Redis没有设置密码，密码字段留空即可</li>
                                <li>请确保Redis服务已启动</li>
                            </ul>
                        </div>
                    </div>

                    <div class="mt-4 text-center">
                        <a href="?step=2" class="btn btn-secondary me-2">
                            <i class="bi bi-arrow-left"></i> 上一步
                        </a>
                        <button type="button" class="btn btn-info me-2" id="testRedisBtn">
                            <i class="bi bi-database-check"></i> 测试连接
                        </button>
                        <button type="button" class="btn btn-primary" id="configureRedisBtn" disabled>
                            <i class="bi bi-arrow-right"></i> 下一步
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <script>
    // 测试Redis连接
    document.getElementById('testRedisBtn').addEventListener('click', async function() {
        const testBtn = this;
        const configureBtn = document.getElementById('configureRedisBtn');
        
        testBtn.disabled = true;
        testBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 测试中...';

        try {
            const formData = new FormData(document.getElementById('redisConfigForm'));
            const response = await axios.post('install.php?step=3&action=test', formData);
            
            if (response.data.success) {
                alert('Redis连接成功！');
                configureBtn.disabled = false;
            } else {
                alert(response.data.message);
            }
        } catch (error) {
            alert('连接测试失败: ' + (error.response?.data?.message || error.message));
        } finally {
            testBtn.disabled = false;
            testBtn.innerHTML = '<i class="bi bi-database-check"></i> 测试连接';
        }
    });

    // 配置Redis
    document.getElementById('configureRedisBtn').addEventListener('click', async function() {
        const configureBtn = this;
        configureBtn.disabled = true;
        configureBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 配置中...';

        try {
            const formData = new FormData(document.getElementById('redisConfigForm'));
            const response = await axios.post('install.php?step=3&action=configure', formData);
            
            if (response.data.success) {
                alert('Redis配置成功！');
                window.location.href = 'install.php?step=4';
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