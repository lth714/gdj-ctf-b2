<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统安装 - 完成安装</title>
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
        .success-icon {
            font-size: 64px;
            color: #10B981;
            margin-bottom: 20px;
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
            <div class="step completed">
                <i class="bi bi-check-circle"></i> 管理员设置
            </div>
            <div class="step active">
                <i class="bi bi-5-circle-fill"></i> 完成安装
            </div>
        </div>

        <div class="card">
            <div class="card-body text-center py-5">
                <div class="success-icon">
                    <i class="bi bi-check-circle-fill"></i>
                </div>
                <h3 class="mb-4">恭喜您，系统安装完成！</h3>
                <div class="alert alert-success d-inline-block">
                    <p class="mb-0">系统已经准备就绪，可以开始使用了。</p>
                </div>
                <div class="mt-4">
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle"></i> 提示：
                        <ul class="mb-0 text-start">
                            <li>请妥善保管管理员账号信息</li>
                            <li>建议定期备份数据库</li>
                            <li>如有问题请查看使用文档</li>
                        </ul>
                    </div>
                </div>
                <div class="mt-4" id="countdown">
                    <p>页面将在 <span id="timer">5</span> 秒后自动跳转到首页...</p>
                </div>
                <div class="mt-4">
                    <a href="/" class="btn btn-primary">
                        <i class="bi bi-house-door"></i> 立即进入首页
                    </a>
                </div>
            </div>
        </div>
    </div>

    <script src="/css/bootstrap.bundle.min.js"></script>
    <script src="/js/axios.min.js"></script>
    <script>
    // 完成安装
    async function finishInstallation() {
        try {
            const response = await axios.post('install.php?step=5&action=finish');
            if (!response.data.success) {
                alert(response.data.message);
                return;
            }
            
            // 开始倒计时
            startCountdown();
        } catch (error) {
            alert('安装完成处理失败: ' + (error.response?.data?.message || error.message));
        }
    }

    // 倒计时函数
    function startCountdown() {
        let seconds = 5;
        const timerElement = document.getElementById('timer');
        
        const countdown = setInterval(() => {
            seconds--;
            timerElement.textContent = seconds;
            
            if (seconds <= 0) {
                clearInterval(countdown);
                window.location.href = '/';
            }
        }, 1000);
    }

    // 页面加载完成后自动执行完成安装
    document.addEventListener('DOMContentLoaded', finishInstallation);
    </script>
</body>
</html>