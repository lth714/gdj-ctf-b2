<!DOCTYPE html>
<html lang="zh-CN" class="h-100">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - IPTV 代理管理系统</title>
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="/css/all.min.css" rel="stylesheet">
    <style>
        .form-signin {
            width: 100%;
            max-width: 330px;
            padding: 15px;
            margin: auto;
        }
    </style>
</head>
<body class="d-flex flex-column h-100">
    <div class="content-wrapper">
        <div class="container">
            <div class="row justify-content-center align-items-center" style="min-height: 80vh;">
                <div class="col-md-4">
                    <div class="card shadow-sm">
                        <div class="card-body">
                            <h3 class="text-center mb-4">IPTV 代理管理系统</h3>
                            <?php if (isset($_SESSION['flash_message'])): ?>
                                <div class="alert alert-<?php echo $_SESSION['flash_message']['type']; ?> alert-dismissible fade show">
                                    <?php echo $_SESSION['flash_message']['message']; ?>
                                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                                </div>
                                <?php unset($_SESSION['flash_message']); ?>
                            <?php endif; ?>
                            <form method="post" action="/admin/login" class="form-signin">
                                <div class="form-floating mb-3">
                                    <input type="text" class="form-control" id="username" name="username" placeholder="用户名" required>
                                    <label for="username">用户名</label>
                                </div>
                                <div class="form-floating mb-3">
                                    <input type="password" class="form-control" id="password" name="password" placeholder="密码" required>
                                    <label for="password">密码</label>
                                </div>
                                <button class="w-100 btn btn-lg btn-primary" type="submit">登录</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <?php require __DIR__ . '/../footer.php'; ?>

    <script src="/css/bootstrap.bundle.min.js"></script>
</body>
</html> 