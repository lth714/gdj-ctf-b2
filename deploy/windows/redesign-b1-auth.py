"""全面改造B1 — 复杂密码 + 三步密码重置(安全问题漏洞点) + 更新源码"""
import paramiko

HOST = '192.168.120.10'
USER = 'gdadmin'
PWD = 'Gdadmin@123'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PWD, timeout=30)
print('[+] Connected')

def run(cmd, timeout=30, sudo=False):
    if sudo:
        cmd = f"echo '{PWD}' | sudo -S {cmd}"
    print(f'  >>> {cmd[:200]}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f'      {out.strip()[:800]}')
    if err.strip() and ec != 0: print(f'      [stderr] {err.strip()[:300]}')
    return out, err, ec

# ============================================================
# Part 1: Database changes
# ============================================================
print('\n[1] 修改数据库 — 添加安全问答字段...')

# Add columns and update admin with complex password + security Q&A
sql = """
ALTER TABLE iptv_proxy.admins
  ADD COLUMN IF NOT EXISTS security_question VARCHAR(255) DEFAULT NULL AFTER password,
  ADD COLUMN IF NOT EXISTS security_answer VARCHAR(255) DEFAULT NULL AFTER security_question;
"""
# MySQL 8.0 doesn't have ADD COLUMN IF NOT EXISTS, need workaround
# Just try adding and ignore duplicate error
run(f"mysql -u root -e \"ALTER TABLE iptv_proxy.admins ADD COLUMN security_question VARCHAR(255) DEFAULT NULL AFTER password;\" 2>&1", sudo=True)
run(f"mysql -u root -e \"ALTER TABLE iptv_proxy.admins ADD COLUMN security_answer VARCHAR(255) DEFAULT NULL AFTER security_question;\" 2>&1", sudo=True)

# Verify columns
run('mysql -u root -e "DESCRIBE iptv_proxy.admins;" 2>&1', sudo=True)

# ============================================================
# Part 2: Update admin with complex password + security Q&A
# ============================================================
print('\n[2] 设置复杂密码和安全问答...')

# Generate complex password hash via PHP
out, _, _ = run("php -r \"echo password_hash('iPtV@Pr0xy#Adm!n2024', PASSWORD_DEFAULT);\" 2>&1")
complex_hash = out.strip()
print(f'  新密码hash: {complex_hash}')

# Security question answer hash (store hashed, like password)
# Actually store plaintext for the check — bcrypt can't compare "close enough" answers
# For CTF, store as-is so we can do simple comparison
out2, _, _ = run("php -r \"echo password_hash('gdj', PASSWORD_DEFAULT);\" 2>&1")
answer_hash = out2.strip()

# Write SQL via SFTP to avoid shell escaping issues
sql_update = f"""UPDATE iptv_proxy.admins SET
  password = '{complex_hash}',
  security_question = '单位英文缩写是？',
  security_answer = '{answer_hash}'
WHERE username = 'admin';"""

sftp = ssh.open_sftp()
fh = sftp.open('/home/gdadmin/update_admin.sql', 'w')
fh.write(sql_update)
fh.close()
sftp.close()

run('bash -c "mysql -u root < /home/gdadmin/update_admin.sql" 2>&1', sudo=True)

# Verify
run('mysql -u root -e "SELECT id, username, security_question, security_answer FROM iptv_proxy.admins WHERE username=\'admin\';" 2>&1', sudo=True)

# ============================================================
# Part 3: Upload modified source files
# ============================================================
print('\n[3] 上传修改后的源码...')

# 3a. AuthController.php
auth_controller = """<?php

namespace App\\Controllers;

use PDO;
use PDOException;

class AuthController
{
    private $basePath;

    public function __construct()
    {
        $this->basePath = dirname(__DIR__, 2);
    }

    public function login()
    {
        $currentPage = 'login';
        require $this->basePath . '/src/views/login.php';
    }

    public function doLogin()
    {
        header('Content-Type: application/json');

        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            http_response_code(405);
            echo json_encode(['success' => false, 'error' => 'Method Not Allowed']);
            return;
        }

        $username = trim($_POST['username'] ?? '');
        $password = $_POST['password'] ?? '';

        if (empty($username) || empty($password)) {
            echo json_encode(['success' => false, 'error' => '用户名或密码错误']);
            return;
        }

        try {
            $config = require $this->basePath . '/config/config.php';
            $db = $config['db'];
            $pdo = new PDO(
                "mysql:host={$db['host']};port={$db['port']};dbname={$db['dbname']};charset={$db['charset']}",
                $db['username'],
                $db['password']
            );
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

            $stmt = $pdo->prepare("SELECT * FROM admins WHERE username = :username LIMIT 1");
            $stmt->execute(['username' => $username]);
            $admin = $stmt->fetch(PDO::FETCH_ASSOC);

            if ($admin && password_verify($password, $admin['password'])) {
                $_SESSION['admin_logged_in'] = true;
                $_SESSION['admin_username'] = $admin['username'];
                $_SESSION['admin_id'] = $admin['id'];

                echo json_encode(['success' => true, 'message' => '登录成功']);
            } else {
                echo json_encode(['success' => false, 'error' => '用户名或密码错误']);
            }
        } catch (PDOException $e) {
            http_response_code(500);
            echo json_encode(['success' => false, 'error' => '系统错误']);
        }
    }

    public function logout()
    {
        session_destroy();
        header('Location: /login');
        exit;
    }

    // ========== 密码重置 (三步流程) ==========

    /**
     * 密码重置页面入口
     * GET: 显示页面
     * POST action=lookup: 查询用户名 → 返回安全问题
     */
    public function forgotPassword()
    {
        if ($_SERVER['REQUEST_METHOD'] === 'GET') {
            $currentPage = 'reset';
            require $this->basePath . '/src/views/reset-password.php';
            return;
        }

        // POST: 查询用户名
        header('Content-Type: application/json');

        $action = $_POST['action'] ?? '';

        if ($action === 'lookup') {
            $this->lookupUsername();
        } elseif ($action === 'verify') {
            $this->verifySecurityAnswer();
        } elseif ($action === 'reset') {
            $this->handleResetPassword();
        } else {
            echo json_encode(['success' => false, 'message' => '无效请求']);
        }
    }

    /**
     * 第一步: 查询用户名 → 返回安全问题
     */
    private function lookupUsername()
    {
        $username = trim($_POST['username'] ?? '');

        if (empty($username)) {
            echo json_encode(['success' => false, 'message' => '请输入用户名']);
            return;
        }

        try {
            $config = require $this->basePath . '/config/config.php';
            $db = $config['db'];
            $pdo = new PDO(
                "mysql:host={$db['host']};port={$db['port']};dbname={$db['dbname']};charset={$db['charset']}",
                $db['username'],
                $db['password']
            );
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

            $stmt = $pdo->prepare("SELECT security_question FROM admins WHERE username = :username LIMIT 1");
            $stmt->execute(['username' => $username]);
            $row = $stmt->fetch(PDO::FETCH_ASSOC);

            if ($row && !empty($row['security_question'])) {
                $_SESSION['reset_username'] = $username;
                echo json_encode([
                    'success' => true,
                    'question' => $row['security_question']
                ]);
            } else {
                echo json_encode([
                    'success' => false,
                    'message' => '用户不存在或未设置安全问题'
                ]);
            }
        } catch (PDOException $e) {
            http_response_code(500);
            echo json_encode(['success' => false, 'message' => '系统错误']);
        }
    }

    /**
     * 第二步: 验证安全问题答案
     *
     * 漏洞点: 答案正确时服务器端会设置 $_SESSION['security_verified'] = true,
     * 但 JSON 响应始终返回 {"success": false, "message": "安全问题回答错误"}。
     * 选手需拦截响应, 将 false 改为 true, 前端才会进入第三步(设置新密码)。
     * 如果答案错误, $_SESSION 不会被设置, 即使改了响应也无法真正重置密码。
     */
    private function verifySecurityAnswer()
    {
        $username = $_SESSION['reset_username'] ?? '';
        $answer = trim($_POST['answer'] ?? '');

        if (empty($username) || empty($answer)) {
            echo json_encode(['success' => false, 'message' => '参数错误']);
            return;
        }

        try {
            $config = require $this->basePath . '/config/config.php';
            $db = $config['db'];
            $pdo = new PDO(
                "mysql:host={$db['host']};port={$db['port']};dbname={$db['dbname']};charset={$db['charset']}",
                $db['username'],
                $db['password']
            );
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

            $stmt = $pdo->prepare("SELECT security_answer FROM admins WHERE username = :username LIMIT 1");
            $stmt->execute(['username' => $username]);
            $row = $stmt->fetch(PDO::FETCH_ASSOC);

            $isCorrect = false;
            if ($row && password_verify($answer, $row['security_answer'])) {
                $isCorrect = true;
                $_SESSION['security_verified'] = $username;
            }

            // 漏洞: 无论答案是否正确, 始终返回 false
            // 但 $isCorrect=true 时已设置 session, 选手改响应即可进入下一步
            echo json_encode([
                'success' => false,
                'message' => '安全问题回答错误'
            ]);
        } catch (PDOException $e) {
            http_response_code(500);
            echo json_encode(['success' => false, 'message' => '系统错误']);
        }
    }

    /**
     * 第三步: 重置密码
     *
     * 必须先通过第二步验证 ($_SESSION['security_verified'] 必须设置),
     * 否则即使选手构造请求也无法重置。
     */
    private function handleResetPassword()
    {
        $username = $_SESSION['reset_username'] ?? '';
        $verified = $_SESSION['security_verified'] ?? '';
        $newPassword = $_POST['new_password'] ?? '';

        if (empty($username) || $verified !== $username) {
            echo json_encode(['success' => false, 'message' => '请先完成安全验证']);
            return;
        }

        if (empty($newPassword) || strlen($newPassword) < 6) {
            echo json_encode(['success' => false, 'message' => '密码长度不能少于6位']);
            return;
        }

        try {
            $config = require $this->basePath . '/config/config.php';
            $db = $config['db'];
            $pdo = new PDO(
                "mysql:host={$db['host']};port={$db['port']};dbname={$db['dbname']};charset={$db['charset']}",
                $db['username'],
                $db['password']
            );
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

            $hashedPassword = password_hash($newPassword, PASSWORD_DEFAULT);
            $stmt = $pdo->prepare("UPDATE admins SET password = :p WHERE username = :u");
            $stmt->execute([':p' => $hashedPassword, ':u' => $username]);

            // 清理 session
            unset($_SESSION['reset_username'], $_SESSION['security_verified']);

            // 漏洞: 密码实际上已修改成功, 但始终返回失败
            echo json_encode([
                'success' => false,
                'message' => '重置失败，请联系管理员'
            ]);
        } catch (PDOException $e) {
            http_response_code(500);
            echo json_encode(['success' => false, 'message' => '系统错误']);
        }
    }
}
"""

fh = sftp.open('/home/gdadmin/AuthController.php', 'w')
fh.write(auth_controller)
fh.close()

# 3b. reset-password.php view (3-step flow)
reset_view = """<?php $currentPage = 'reset'; ?>
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>重置密码 - IPTV 代理系统</title>
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="/css/all.min.css" rel="stylesheet">
    <style>
        .card { max-width: 500px; margin: 80px auto; }
        .step-indicator { display: flex; justify-content: center; margin-bottom: 24px; }
        .step-dot {
            width: 32px; height: 32px; border-radius: 50%;
            background: #dee2e6; color: #6c757d;
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; font-size: 14px; margin: 0 4px;
        }
        .step-dot.active { background: #0d6efd; color: #fff; }
        .step-dot.done { background: #198754; color: #fff; }
        .step-line { width: 60px; height: 2px; background: #dee2e6; align-self: center; }
        .step-line.done { background: #198754; }
        .step-content { display: none; }
        .step-content.active { display: block; }
    </style>
</head>
<body class="bg-light">
    <div class="container">
        <div class="card shadow-sm">
            <div class="card-body p-4">
                <h4 class="card-title text-center mb-1">重置管理员密码</h4>
                <p class="text-center text-muted small mb-4">请按照步骤完成密码重置</p>

                <!-- 步骤指示器 -->
                <div class="step-indicator">
                    <div class="step-dot active" id="dot1">1</div>
                    <div class="step-line" id="line1"></div>
                    <div class="step-dot" id="dot2">2</div>
                    <div class="step-line" id="line2"></div>
                    <div class="step-dot" id="dot3">3</div>
                </div>

                <!-- 全局消息 -->
                <div id="globalMsg" class="alert alert-danger d-none"></div>

                <!-- 第一步: 输入用户名 -->
                <div class="step-content active" id="step1">
                    <div class="mb-3">
                        <label for="username" class="form-label">管理员账号</label>
                        <input type="text" class="form-control" id="username"
                               placeholder="请输入管理员用户名" required autofocus>
                    </div>
                    <button type="button" class="btn btn-primary w-100" id="btnLookup">
                        <i class="fas fa-search me-1"></i>查询安全问题
                    </button>
                    <div class="text-center mt-3">
                        <a href="/login" class="text-muted small text-decoration-none">
                            <i class="fas fa-arrow-left me-1"></i>返回登录
                        </a>
                    </div>
                </div>

                <!-- 第二步: 回答安全问题 -->
                <div class="step-content" id="step2">
                    <div class="alert alert-info">
                        <i class="fas fa-shield-alt me-2"></i>
                        <span id="securityQuestion">安全问题加载中...</span>
                    </div>
                    <div class="mb-3">
                        <label for="answer" class="form-label">您的答案</label>
                        <input type="text" class="form-control" id="answer"
                               placeholder="请输入您的答案" required>
                    </div>
                    <button type="button" class="btn btn-primary w-100" id="btnVerify">
                        <i class="fas fa-check-circle me-1"></i>验证答案
                    </button>
                    <div class="text-center mt-2">
                        <a href="#" id="backToStep1" class="text-muted small text-decoration-none">返回上一步</a>
                    </div>
                </div>

                <!-- 第三步: 设置新密码 -->
                <div class="step-content" id="step3">
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>安全验证通过，请设置新密码
                    </div>
                    <div class="mb-3">
                        <label for="newPassword" class="form-label">新密码</label>
                        <input type="password" class="form-control" id="newPassword"
                               placeholder="请输入新密码（至少6位）" required minlength="6">
                    </div>
                    <div class="mb-3">
                        <label for="confirmPassword" class="form-label">确认新密码</label>
                        <input type="password" class="form-control" id="confirmPassword"
                               placeholder="请再次输入新密码" required minlength="6">
                    </div>
                    <button type="button" class="btn btn-success w-100" id="btnReset">
                        <i class="fas fa-lock me-1"></i>重置密码
                    </button>
                    <div class="text-center mt-2">
                        <a href="#" id="backToStep2" class="text-muted small text-decoration-none">返回上一步</a>
                    </div>
                </div>

                <!-- 完成提示 -->
                <div class="step-content text-center" id="stepDone">
                    <div class="mb-3">
                        <i class="fas fa-check-circle text-success" style="font-size: 48px;"></i>
                    </div>
                    <h5>密码重置完成</h5>
                    <p class="text-muted">请使用新密码登录系统</p>
                    <a href="/login" class="btn btn-primary">
                        <i class="fas fa-sign-in-alt me-1"></i>前往登录
                    </a>
                </div>
            </div>
        </div>
    </div>

    <?php require __DIR__ . '/footer.php'; ?>
    <script src="/css/bootstrap.bundle.min.js" defer></script>
    <script>
    var currentStep = 1;
    var questionText = '';

    function setStep(step) {
        document.querySelectorAll('.step-content').forEach(function(el) { el.classList.remove('active'); });
        var target = document.getElementById('step' + step);
        if (target) target.classList.add('active');

        document.querySelectorAll('.step-dot').forEach(function(el) { el.classList.remove('active'); });
        for (var i = 1; i <= step; i++) {
            var dot = document.getElementById('dot' + i);
            if (dot) dot.classList.add(i < step ? 'done' : 'active');
        }
        document.querySelectorAll('.step-line').forEach(function(el) { el.classList.remove('done'); });
        for (var i = 1; i < step; i++) {
            var line = document.getElementById('line' + i);
            if (line) line.classList.add('done');
        }
        currentStep = step;
        document.getElementById('globalMsg').classList.add('d-none');
    }

    function showError(msg) {
        var el = document.getElementById('globalMsg');
        el.textContent = msg;
        el.classList.remove('d-none');
    }

    // Step 1: 查询用户名
    document.getElementById('btnLookup').addEventListener('click', async function() {
        var username = document.getElementById('username').value.trim();
        if (!username) { showError('请输入用户名'); return; }

        var btn = this;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>查询中...';

        try {
            var formData = new FormData();
            formData.append('action', 'lookup');
            formData.append('username', username);

            var resp = await fetch('/auth/reset-password', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            var result = await resp.json();

            if (result.success) {
                questionText = result.question;
                document.getElementById('securityQuestion').textContent = questionText;
                setStep(2);
                document.getElementById('answer').focus();
            } else {
                showError(result.message || '查询失败');
            }
        } catch (err) {
            showError('请求失败: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-search me-1"></i>查询安全问题';
        }
    });

    // Step 2: 验证安全答案 (漏洞点 — 答案正确时后端返回 false, 需改包)
    document.getElementById('btnVerify').addEventListener('click', async function() {
        var answer = document.getElementById('answer').value.trim();
        if (!answer) { showError('请输入安全问题答案'); return; }

        var btn = this;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>验证中...';

        try {
            var formData = new FormData();
            formData.append('action', 'verify');
            formData.append('answer', answer);

            var resp = await fetch('/auth/reset-password', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            var result = await resp.json();

            // 漏洞: 即使答案正确, result.success 也是 false
            // 选手需通过 Burp/Yakit 拦截响应, 将 false 改为 true
            if (result.success) {
                setStep(3);
                document.getElementById('newPassword').focus();
            } else {
                showError(result.message || '安全问题回答错误');
            }
        } catch (err) {
            showError('请求失败: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check-circle me-1"></i>验证答案';
        }
    });

    // Step 3: 重置密码 (漏洞点 — 密码已改但后端返回 false)
    document.getElementById('btnReset').addEventListener('click', async function() {
        var newPw = document.getElementById('newPassword').value;
        var confirmPw = document.getElementById('confirmPassword').value;

        if (newPw.length < 6) { showError('密码长度不能少于6位'); return; }
        if (newPw !== confirmPw) { showError('两次输入的密码不一致'); return; }

        var btn = this;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>重置中...';

        try {
            var formData = new FormData();
            formData.append('action', 'reset');
            formData.append('new_password', newPw);

            var resp = await fetch('/auth/reset-password', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            var result = await resp.json();

            // 漏洞: 密码已修改成功, 但 result.success 始终为 false
            // 选手需通过 Burp/Yakit 拦截响应, 将 false 改为 true
            if (result.success) {
                setStep('Done');
            } else {
                showError(result.message || '重置失败');
            }
        } catch (err) {
            showError('请求失败: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-lock me-1"></i>重置密码';
        }
    });

    // 返回按钮
    document.getElementById('backToStep1').addEventListener('click', function(e) {
        e.preventDefault(); setStep(1);
    });
    document.getElementById('backToStep2').addEventListener('click', function(e) {
        e.preventDefault(); setStep(2);
    });

    // 回车键提交
    document.getElementById('username').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') document.getElementById('btnLookup').click();
    });
    document.getElementById('answer').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') document.getElementById('btnVerify').click();
    });
    </script>
</body>
</html>
"""

fh = sftp.open('/home/gdadmin/reset-password.php', 'w')
fh.write(reset_view)
fh.close()

print('  AuthController.php 和 reset-password.php 已写入 /home/gdadmin/')

# ============================================================
# Part 4: Copy files to target locations
# ============================================================
print('\n[4] 复制文件到目标路径...')
run('cp /home/gdadmin/AuthController.php /opt/iptv-proxy/src/Controllers/AuthController.php', sudo=True)
run('cp /home/gdadmin/reset-password.php /opt/iptv-proxy/src/views/reset-password.php', sudo=True)
run('chown -R www-data:www-data /opt/iptv-proxy', sudo=True)

# ============================================================
# Part 5: Verify
# ============================================================
print('\n[5] 验证部署...')

# Check DB
print('  --- 管理员数据 ---')
run('mysql -u root -e "SELECT id, username, security_question, LEFT(password, 40) as pw_preview FROM iptv_proxy.admins WHERE username=\"admin\";" 2>&1', sudo=True)

# Test step 1: lookup
print('\n  --- Step 1: 查询用户名 ---')
run('curl -s -X POST http://localhost/auth/reset-password -d "action=lookup&username=admin" -H "X-Requested-With: XMLHttpRequest"')

# Test step 2: wrong answer
print('\n  --- Step 2: 错误答案 ---')
run('curl -s -X POST http://localhost/auth/reset-password -d "action=verify&answer=wrong" -H "X-Requested-With: XMLHttpRequest"')

# Test step 2: correct answer
print('\n  --- Step 2: 正确答案 (gdj) ---')
result = run('curl -s -c /tmp/reset_cookie.txt -X POST http://localhost/auth/reset-password -d "action=verify&answer=gdj" -H "X-Requested-With: XMLHttpRequest"')
# Note: even correct answer returns {"success":false}

# Test step 3: reset password (should work if session set correctly)
print('\n  --- Step 3: 重置密码 ---')
run('curl -s -b /tmp/reset_cookie.txt -X POST http://localhost/auth/reset-password -d "action=reset&new_password=att123456" -H "X-Requested-With: XMLHttpRequest"')

sftp.close()
ssh.close()
print('\n=== DONE ===')
print('管理员密码已改为: iPtV@Pr0xy#Adm!n2024')
print('安全问题: 单位英文缩写是？ 答案: gdj')
print('漏洞点: 安全答案验证和密码重置均返回 false, 需Burp改包')
