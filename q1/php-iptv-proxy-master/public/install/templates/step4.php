<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统安装 - 管理员设置</title>
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
            <div class="step completed">
                <i class="bi bi-check-circle"></i> Redis配置
            </div>
            <div class="step active">
                <i class="bi bi-4-circle-fill"></i> 管理员设置
            </div>
            <div class="step">
                <i class="bi bi-5-circle"></i> 完成安装
            </div>
        </div>

        <div class="card">
            <div class="card-header bg-white py-3">
                <h3 class="card-title mb-0">管理员设置</h3>
            </div>
            <div class="card-body">
                <form id="adminConfigForm" class="needs-validation" novalidate>
                    <div class="form-floating mb-3">
                        <input type="text" class="form-control" id="site_name" name="site_name" value="IPTV代理系统" required>
                        <label for="site_name">站点名称</label>
                    </div>

                    <div class="form-floating mb-3">
                        <input type="text" class="form-control" id="username" name="username" required>
                        <label for="username">管理员用户名</label>
                        <div class="form-text">用于登录后台管理系统</div>
                    </div>

                    <div class="form-floating mb-3">
                        <input type="password" class="form-control" id="password" name="password" required>
                        <label for="password">管理员密码</label>
                        <div class="form-text">密码长度不少于6个字符</div>
                    </div>

                    <div class="form-floating mb-3">
                        <input type="password" class="form-control" id="confirm_password" name="confirm_password" required>
                        <label for="confirm_password">确认密码</label>
                    </div>

                    <div class="form-floating mb-3">
                        <textarea class="form-control" id="description" name="description" style="height: 100px">系统管理员</textarea>
                        <label for="description">描述信息</label>
                    </div>

                    <div class="mt-4">
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i> 提示：
                            <ul class="mb-0">
                                <li>请使用安全的密码组合</li>
                                <li>建议包含字母、数字和特殊字符</li>
                                <li>请妥善保管管理员账号信息</li>
                            </ul>
                        </div>
                    </div>

                    <div class="mt-4 text-center">
                        <a href="?step=3" class="btn btn-secondary me-2">
                            <i class="bi bi-arrow-left"></i> 上一步
                        </a>
                        <button type="submit" class="btn btn-primary">
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
    document.getElementById('adminConfigForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const submitBtn = this.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 配置中...';

        try {
            // 表单验证
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm_password').value;

            if (password.length < 6) {
                alert('密码长度不能少于6个字符');
                return;
            }

            if (password !== confirmPassword) {
                alert('两次输入的密码不一致');
                return;
            }

            const formData = new FormData(this);
            const response = await axios.post('install.php?step=4&action=configure', formData);
            
            if (response.data.success) {
                alert('管理员配置成功！');
                window.location.href = 'install.php?step=5';
            } else {
                alert(response.data.message);
            }
        } catch (error) {
            alert('配置失败: ' + (error.response?.data?.message || error.message));
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-arrow-right"></i> 下一步';
        }
    });
    </script>
</body>
</html>