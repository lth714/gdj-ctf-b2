<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>重置密码 - IPTV代理系统</title>
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
        .reset-container {
            max-width: 440px;
            width: 100%;
            padding: 20px;
        }
        .reset-logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .reset-logo i {
            font-size: 48px;
            color: #3B82F6;
        }
        .card {
            border: none;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .step-indicator {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 24px;
        }
        .step-indicator .step {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #e9ecef;
            color: #6c757d;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s;
        }
        .step-indicator .step.active {
            background: #3B82F6;
            color: #fff;
        }
        .step-indicator .step.completed {
            background: #10B981;
            color: #fff;
        }
        .step-indicator .step-line {
            width: 48px;
            height: 2px;
            background: #e9ecef;
            margin: 0 4px;
            transition: all 0.3s;
        }
        .step-panel {
            display: none;
        }
        .step-panel.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="reset-container">
        <div class="reset-logo">
            <i class="bi bi-shield-lock"></i>
            <h3 class="mt-3">重置管理员密码</h3>
            <p class="text-muted small">广播电视网络监控系统 v3.2</p>
        </div>

        <div class="step-indicator">
            <div class="step active" id="stepDot1">1</div>
            <div class="step-line" id="stepLine1"></div>
            <div class="step" id="stepDot2">2</div>
            <div class="step-line" id="stepLine2"></div>
            <div class="step" id="stepDot3">3</div>
        </div>

        <div class="card">
            <div class="card-body p-4">

                <div id="alertContainer"></div>

                <!-- Step 1: 输入用户名 -->
                <div class="step-panel active" id="step1Panel">
                    <h5 class="card-title mb-3">验证身份</h5>
                    <p class="text-muted small mb-4">请输入您的管理员账号，系统将显示您的安全问题。</p>
                    <form id="step1Form">
                        <div class="mb-3">
                            <div class="form-floating">
                                <input type="text" class="form-control" id="username" name="username" placeholder="管理员账号" required autofocus>
                                <label for="username">管理员账号</label>
                            </div>
                        </div>
                        <div class="d-grid">
                            <button type="submit" class="btn btn-primary" id="step1Btn">
                                <i class="bi bi-arrow-right-circle me-1"></i>下一步
                            </button>
                        </div>
                    </form>
                    <div class="text-center mt-3">
                        <a href="/login" class="text-decoration-none small">
                            <i class="bi bi-arrow-left"></i> 返回登录
                        </a>
                    </div>
                </div>

                <!-- Step 2: 回答安全问题 -->
                <div class="step-panel" id="step2Panel">
                    <h5 class="card-title mb-3">安全验证</h5>
                    <p class="text-muted small mb-3">请回答以下安全问题以验证您的身份。</p>
                    <div class="alert alert-info" id="questionBox">
                        <i class="bi bi-question-circle-fill me-2"></i>
                        <span id="securityQuestion">...</span>
                    </div>
                    <form id="step2Form">
                        <div class="mb-3">
                            <div class="form-floating">
                                <input type="text" class="form-control" id="answer" name="answer" placeholder="您的答案" required>
                                <label for="answer">您的答案</label>
                            </div>
                        </div>
                        <div class="d-grid gap-2">
                            <button type="submit" class="btn btn-primary" id="step2Btn">
                                <i class="bi bi-check-circle me-1"></i>验证答案
                            </button>
                            <button type="button" class="btn btn-outline-secondary" id="backStep1Btn">
                                <i class="bi bi-arrow-left"></i> 上一步
                            </button>
                        </div>
                    </form>
                </div>

                <!-- Step 3: 设置新密码 -->
                <div class="step-panel" id="step3Panel">
                    <h5 class="card-title mb-3">设置新密码</h5>
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle-fill me-2"></i>安全验证通过
                    </div>
                    <form id="step3Form">
                        <div class="mb-3">
                            <div class="form-floating">
                                <input type="password" class="form-control" id="newPassword" name="new_password" placeholder="新密码" required minlength="6">
                                <label for="newPassword">新密码</label>
                            </div>
                            <div class="form-text">密码长度不少于6位</div>
                        </div>
                        <div class="mb-4">
                            <div class="form-floating">
                                <input type="password" class="form-control" id="confirmPassword" name="confirm_password" placeholder="确认新密码" required minlength="6">
                                <label for="confirmPassword">确认新密码</label>
                            </div>
                        </div>
                        <div class="d-grid gap-2">
                            <button type="submit" class="btn btn-primary" id="step3Btn">
                                <i class="bi bi-lock-fill me-1"></i>重置密码
                            </button>
                            <button type="button" class="btn btn-outline-secondary" id="backStep2Btn">
                                <i class="bi bi-arrow-left"></i> 上一步
                            </button>
                        </div>
                    </form>
                </div>

            </div>
        </div>

        <div class="text-center mt-4 text-muted">
            <small>&copy; <?php echo date('Y'); ?> 广播电视网络监控系统</small>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
    var currentStep = 1;
    var lookupDone = false;
    var verifyDone = false;
    var alertContainer = document.getElementById('alertContainer');

    function showAlert(message, type) {
        var wrapper = document.createElement('div');
        wrapper.className = 'alert alert-' + type + ' alert-dismissible fade show';
        wrapper.innerHTML =
            '<i class="bi bi-' + (type === 'danger' ? 'exclamation-triangle' : 'check-circle') + '-fill me-2"></i>' +
            message +
            '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
        alertContainer.innerHTML = '';
        alertContainer.appendChild(wrapper);
    }

    function setStep(step) {
        currentStep = step;
        document.getElementById('step1Panel').classList.toggle('active', step === 1);
        document.getElementById('step2Panel').classList.toggle('active', step === 2);
        document.getElementById('step3Panel').classList.toggle('active', step === 3);

        for (var i = 1; i <= 3; i++) {
            var dot = document.getElementById('stepDot' + i);
            if (i < step) dot.className = 'step completed';
            else if (i === step) dot.className = 'step active';
            else dot.className = 'step';
        }
        document.getElementById('stepLine1').style.background = step > 1 ? '#10B981' : '#e9ecef';
        document.getElementById('stepLine2').style.background = step > 2 ? '#10B981' : '#e9ecef';

        alertContainer.innerHTML = '';
    }

    // Step 1: 查询用户名 -> 获取安全问题
    document.getElementById('step1Form').addEventListener('submit', async function(e) {
        e.preventDefault();
        var username = document.getElementById('username').value.trim();
        if (!username) {
            showAlert('请输入管理员账号', 'danger');
            return;
        }

        var btn = document.getElementById('step1Btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 查询中...';

        try {
            var formData = new FormData();
            formData.append('action', 'lookup');
            formData.append('username', username);

            var response = await fetch('/auth/reset-password', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            var result = await response.json();

            if (result.success) {
                document.getElementById('securityQuestion').textContent = result.question;
                lookupDone = true;
                setStep(2);
                document.getElementById('answer').focus();
            } else {
                showAlert(result.error || result.message || '查询失败', 'danger');
            }
        } catch (error) {
            showAlert('请求出错：' + error.message, 'danger');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-arrow-right-circle me-1"></i>下一步';
        }
    });

    // Step 2: 验证安全问题 (漏洞点)
    document.getElementById('step2Form').addEventListener('submit', async function(e) {
        e.preventDefault();
        var answer = document.getElementById('answer').value.trim();
        if (!answer) {
            showAlert('请输入安全问题答案', 'danger');
            return;
        }

        var btn = document.getElementById('step2Btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 验证中...';

        try {
            var formData = new FormData();
            formData.append('action', 'verify');
            formData.append('answer', answer);

            var response = await fetch('/auth/reset-password', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            var result = await response.json();

            // 漏洞: 答案正确时后端仍返回 success:false, 需Burp改包
            if (result.success) {
                verifyDone = true;
                setStep(3);
                document.getElementById('newPassword').focus();
            } else {
                showAlert(result.error || result.message || '安全问题回答错误', 'danger');
            }
        } catch (error) {
            showAlert('请求出错：' + error.message, 'danger');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle me-1"></i>验证答案';
        }
    });

    // Step 3: 重置密码 (漏洞点)
    document.getElementById('step3Form').addEventListener('submit', async function(e) {
        e.preventDefault();
        var newPassword = document.getElementById('newPassword').value;
        var confirmPassword = document.getElementById('confirmPassword').value;

        if (newPassword.length < 6) {
            showAlert('密码长度不能少于6个字符', 'danger');
            return;
        }
        if (newPassword !== confirmPassword) {
            showAlert('两次输入的密码不一致', 'danger');
            return;
        }

        var btn = document.getElementById('step3Btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 提交中...';

        try {
            var formData = new FormData();
            formData.append('action', 'reset');
            formData.append('new_password', newPassword);

            var response = await fetch('/auth/reset-password', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            var result = await response.json();

            // 漏洞: 密码已修改成功, 但响应始终返回 false
            if (result.success) {
                showAlert('密码重置成功，正在跳转登录页面...', 'success');
                setTimeout(function() {
                    window.location.href = '/login';
                }, 1500);
            } else {
                showAlert(result.error || result.message || '重置失败', 'danger');
            }
        } catch (error) {
            showAlert('请求出错：' + error.message, 'danger');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-lock-fill me-1"></i>重置密码';
        }
    });

    // 返回按钮
    document.getElementById('backStep1Btn').addEventListener('click', function() { setStep(1); });
    document.getElementById('backStep2Btn').addEventListener('click', function() { setStep(2); });

    // 回车键
    document.getElementById('answer').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') document.getElementById('step2Form').dispatchEvent(new Event('submit'));
    });
    </script>
</body>
</html>
