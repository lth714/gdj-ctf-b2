<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - IPTV代理系统</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {
            background-color: #f5f8fa;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            max-width: 400px;
            width: 100%;
            padding: 20px;
        }
        .login-logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .login-logo i {
            font-size: 48px;
            color: #3B82F6;
        }
        .card {
            border: none;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-logo">
            <i class="bi bi-display"></i>
            <h3 class="mt-3">IPTV代理系统</h3>
        </div>
        
        <div class="card">
            <div class="card-body p-4">
                <h4 class="card-title text-center mb-4">管理员登录</h4>
                
                <?php if (isset($error)): ?>
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i><?php echo htmlspecialchars($error); ?>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
                <?php endif; ?>

                <form id="loginForm">
                    <div class="mb-3">
                        <div class="form-floating">
                            <input type="text" class="form-control" id="username" name="username" placeholder="用户名" required>
                            <label for="username">用户名</label>
                        </div>
                    </div>

                    <div class="mb-4">
                        <div class="form-floating">
                            <input type="password" class="form-control" id="password" name="password" placeholder="密码" required>
                            <label for="password">密码</label>
                        </div>
                    </div>

                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary btn-lg">
                            <i class="bi bi-box-arrow-in-right"></i> 登录
                        </button>
                    </div>
                </form>
                <div class="text-center mt-3">
                    <a href="/reset-password" class="text-muted small text-decoration-none">忘记密码?</a>
                </div>
            </div>
        </div>

        <div class="text-center mt-4 text-muted">
            <small>&copy; <?php echo date('Y'); ?> IPTV代理系统</small>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 登录中...';
    
    try {
        const formData = new FormData(e.target);
        const response = await fetch('/auth/login', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error('登录请求失败');
        }

        const result = await response.json();
        
        if (result.success) {
            window.location.href = '/';
        } else {
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger alert-dismissible fade show';
            alertDiv.innerHTML = `
                <i class="bi bi-exclamation-triangle-fill me-2"></i>${result.error || '登录失败'}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            e.target.insertBefore(alertDiv, e.target.firstChild);
        }
    } catch (error) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show';
        alertDiv.innerHTML = `
            <i class="bi bi-exclamation-triangle-fill me-2"></i>登录出错：${error.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        e.target.insertBefore(alertDiv, e.target.firstChild);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-box-arrow-in-right"></i> 登录';
    }
    });
    </script>
</body>
</html>