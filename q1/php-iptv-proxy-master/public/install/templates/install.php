<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPTV代理系统安装</title>
    <link href="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1 class="mb-4">IPTV代理系统安装</h1>
        
        <!-- 环境检测 -->
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">环境检测</h5>
            </div>
            <div class="card-body">
                <h6>PHP版本</h6>
                <div class="mb-3">
                    <div class="d-flex justify-content-between">
                        <span>当前版本：<?= $requirements['php']['current'] ?></span>
                        <span>要求版本：<?= $requirements['php']['required'] ?></span>
                        <?php if ($requirements['php']['status']): ?>
                            <span class="text-success">✓ 符合要求</span>
                        <?php else: ?>
                            <span class="text-danger">✗ 版本过低</span>
                        <?php endif; ?>
                    </div>
                </div>

                <h6>PHP扩展</h6>
                <?php foreach ($requirements['extensions'] as $ext => $info): ?>
                <div class="mb-2">
                    <div class="d-flex justify-content-between">
                        <span><?= $ext ?></span>
                        <span><?= $info['current'] ?></span>
                        <?php if ($info['status']): ?>
                            <span class="text-success">✓ 已安装</span>
                        <?php else: ?>
                            <span class="text-danger">✗ 未安装</span>
                        <?php endif; ?>
                    </div>
                </div>
                <?php endforeach; ?>
            </div>
        </div>

        <!-- 目录权限检测 -->
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">目录权限检测</h5>
            </div>
            <div class="card-body">
                <?php foreach ($writableChecks as $path => $check): ?>
                <div class="mb-2">
                    <div class="d-flex justify-content-between">
                        <span><?= $check['path'] ?></span>
                        <?php if ($check['writable']): ?>
                            <span class="text-success">✓ 可写</span>
                        <?php else: ?>
                            <span class="text-danger">✗ 不可写</span>
                        <?php endif; ?>
                    </div>
                </div>
                <?php endforeach; ?>
            </div>
        </div>

        <!-- 安装表单 -->
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">系统配置</h5>
            </div>
            <div class="card-body">
                <form id="installForm">
                    <h6 class="mb-3">数据库配置</h6>
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">数据库主机</label>
                            <input type="text" class="form-control" name="db_host" value="localhost" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">数据库端口</label>
                            <input type="text" class="form-control" name="db_port" value="3306" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">数据库名称</label>
                            <input type="text" class="form-control" name="db_name" value="iptv_proxy" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">数据库用户名</label>
                            <input type="text" class="form-control" name="db_user" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">数据库密码</label>
                            <input type="password" class="form-control" name="db_pass" required>
                        </div>
                    </div>

                    <h6 class="mb-3 mt-4">Redis配置</h6>
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">Redis主机</label>
                            <input type="text" class="form-control" name="redis_host" value="127.0.0.1" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Redis端口</label>
                            <input type="text" class="form-control" name="redis_port" value="6379" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Redis密码</label>
                            <input type="password" class="form-control" name="redis_pass">
                        </div>
                    </div>

                    <h6 class="mb-3 mt-4">管理员账号</h6>
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">用户名</label>
                            <input type="text" class="form-control" name="admin_user" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">密码</label>
                            <input type="password" class="form-control" name="admin_pass" required>
                        </div>
                    </div>

                    <div class="mt-4">
                        <button type="submit" class="btn btn-primary" id="installBtn">开始安装</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('installForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('installBtn');
            btn.disabled = true;
            btn.textContent = '安装中...';

            try {
                const formData = new FormData(e.target);
                const response = await fetch('install.php', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                
                if (result.success) {
                    alert('安装成功！即将跳转到登录页面...');
                    // 延迟1秒后跳转，让用户看到提示
                    setTimeout(() => {
                        window.location.href = result.redirect;
                    }, 1000);
                } else {
                    alert('安装失败：' + result.error);
                    btn.disabled = false;
                    btn.textContent = '开始安装';
                }
            } catch (error) {
                alert('安装出错：' + error.message);
                btn.disabled = false;
                btn.textContent = '开始安装';
            }
        });
    </script>
</body>
</html> 