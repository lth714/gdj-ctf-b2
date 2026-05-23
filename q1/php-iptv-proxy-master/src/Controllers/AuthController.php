<?php

namespace App\Controllers;

class AuthController
{
    private $basePath;

    public function __construct()
    {
        $this->basePath = dirname(__DIR__, 2);
    }

    /**
     * 显示登录页面
     */
    public function login()
    {
        if (isset($_SESSION['user']) && !empty($_SESSION['user'])) {
            header('Location: /');
            exit;
        }

        require $this->basePath . '/src/views/login.php';
    }

    /**
     * 处理登录请求
     */
    public function handleLogin()
    {
        try {
            if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
                throw new \Exception('Invalid request method');
            }

            header('Content-Type: application/json');

            $username = $_POST['username'] ?? '';
            $password = $_POST['password'] ?? '';

            if (empty($username) || empty($password)) {
                throw new \Exception('用户名和密码不能为空');
            }

            $config = require $this->basePath . '/config/config.php';
            $dbConfig = $config['db'];
            $dsn = "mysql:host={$dbConfig['host']};port={$dbConfig['port']};dbname={$dbConfig['dbname']}";
            $pdo = new \PDO($dsn, $dbConfig['username'], $dbConfig['password']);
            $pdo->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

            $stmt = $pdo->prepare("SELECT * FROM admins WHERE username = ?");
            $stmt->execute([$username]);
            $user = $stmt->fetch(\PDO::FETCH_ASSOC);

            if (!$user) {
                throw new \Exception('用户不存在');
            }

            if (!password_verify($password, $user['password'])) {
                throw new \Exception('密码错误');
            }

            $_SESSION['user'] = [
                'id' => $user['id'],
                'username' => $user['username'],
                'login_time' => time()
            ];

            echo json_encode([
                'success' => true,
                'message' => '登录成功'
            ]);
            exit;
        } catch (\Exception $e) {
            http_response_code(400);
            echo json_encode([
                'success' => false,
                'error' => $e->getMessage()
            ]);
            exit;
        }
    }

    /**
     * 处理退出登录
     */
    public function logout()
    {
        $_SESSION = array();

        if (isset($_COOKIE[session_name()])) {
            setcookie(session_name(), '', time() - 3600, '/');
        }

        session_destroy();

        header('Location: /login');
        exit;
    }

    /**
     * 密码重置页面入口 (三步流程)
     * GET  -> 显示页面
     * POST -> 根据 action 参数分发到不同步骤
     */
    public function forgotPassword()
    {
        if ($_SERVER['REQUEST_METHOD'] === 'GET') {
            if (isset($_SESSION['user']) && !empty($_SESSION['user'])) {
                header('Location: /');
                exit;
            }
            require $this->basePath . '/src/views/reset-password.php';
            return;
        }

        // POST: 三步流程分发
        header('Content-Type: application/json');

        $action = $_POST['action'] ?? '';

        try {
            if ($action === 'lookup') {
                $this->lookupUsername();
            } elseif ($action === 'verify') {
                $this->verifySecurityAnswer();
            } elseif ($action === 'reset') {
                $this->handleResetPassword();
            } else {
                throw new \Exception('无效请求');
            }
        } catch (\Exception $e) {
            http_response_code(400);
            echo json_encode([
                'success' => false,
                'error' => $e->getMessage()
            ]);
            exit;
        }
    }

    /**
     * 第一步: 查询用户名, 返回安全问题
     */
    private function lookupUsername()
    {
        $username = trim($_POST['username'] ?? '');

        if (empty($username)) {
            throw new \Exception('请输入用户名');
        }

        $config = require $this->basePath . '/config/config.php';
        $dbConfig = $config['db'];
        $dsn = "mysql:host={$dbConfig['host']};port={$dbConfig['port']};dbname={$dbConfig['dbname']}";
        $pdo = new \PDO($dsn, $dbConfig['username'], $dbConfig['password']);
        $pdo->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

        $stmt = $pdo->prepare("SELECT security_question FROM admins WHERE username = ? LIMIT 1");
        $stmt->execute([$username]);
        $row = $stmt->fetch(\PDO::FETCH_ASSOC);

        if ($row && !empty($row['security_question'])) {
            $_SESSION['reset_username'] = $username;
            echo json_encode([
                'success' => true,
                'question' => $row['security_question']
            ]);
        } else {
            throw new \Exception('用户不存在或未设置安全问题');
        }
    }

    /**
     * 第二步: 验证安全问题答案
     *
     * 漏洞点: 答案正确时服务器设置 $_SESSION['security_verified'] = true,
     * 但 JSON 响应始终返回 {"success": false}.
     * 选手需拦截响应包, 将 false 改为 true, 前端才会进入第三步。
     * 若答案错误, session 不会被设置, 即使改了响应也无法真正重置密码。
     */
    private function verifySecurityAnswer()
    {
        $username = $_SESSION['reset_username'] ?? '';
        $answer = trim($_POST['answer'] ?? '');

        if (empty($username) || empty($answer)) {
            throw new \Exception('参数错误');
        }

        $config = require $this->basePath . '/config/config.php';
        $dbConfig = $config['db'];
        $dsn = "mysql:host={$dbConfig['host']};port={$dbConfig['port']};dbname={$dbConfig['dbname']}";
        $pdo = new \PDO($dsn, $dbConfig['username'], $dbConfig['password']);
        $pdo->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

        $stmt = $pdo->prepare("SELECT security_answer FROM admins WHERE username = ? LIMIT 1");
        $stmt->execute([$username]);
        $row = $stmt->fetch(\PDO::FETCH_ASSOC);

        if ($row && password_verify($answer, $row['security_answer'])) {
            // 答案正确, 设置 session 标记
            $_SESSION['security_verified'] = $username;
        }

        // 漏洞: 无论答案是否正确, 始终返回 false
        // 选手需通过 Burp/Yakit 拦截响应, 修改 success 为 true
        echo json_encode([
            'success' => false,
            'error' => '安全问题回答错误'
        ]);
        exit;
    }

    /**
     * 第三步: 重置密码
     *
     * 必须先通过第二步验证 (检查 $_SESSION['security_verified']),
     * 否则即使选手构造请求也无法完成重置。
     * 密码实际已修改, 但响应始终返回 false。
     */
    private function handleResetPassword()
    {
        $username = $_SESSION['reset_username'] ?? '';
        $verified = $_SESSION['security_verified'] ?? '';
        $newPassword = $_POST['new_password'] ?? '';

        if (empty($username) || $verified !== $username) {
            throw new \Exception('请先完成安全验证');
        }

        if (empty($newPassword) || strlen($newPassword) < 6) {
            throw new \Exception('密码长度不能少于6个字符');
        }

        $config = require $this->basePath . '/config/config.php';
        $dbConfig = $config['db'];
        $dsn = "mysql:host={$dbConfig['host']};port={$dbConfig['port']};dbname={$dbConfig['dbname']}";
        $pdo = new \PDO($dsn, $dbConfig['username'], $dbConfig['password']);
        $pdo->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

        // 检查用户是否存在
        $stmt = $pdo->prepare("SELECT id FROM admins WHERE username = ?");
        $stmt->execute([$username]);
        if (!$stmt->fetch()) {
            throw new \Exception('用户不存在');
        }

        // 更新密码
        $hashedPassword = password_hash($newPassword, PASSWORD_DEFAULT);
        $stmt = $pdo->prepare("UPDATE admins SET password = ? WHERE username = ?");
        $stmt->execute([$hashedPassword, $username]);

        // 清理 session
        unset($_SESSION['reset_username'], $_SESSION['security_verified']);

        // 漏洞: 密码已成功修改, 但响应始终返回 false
        // 选手需拦截响应包, 将 false 改为 true
        echo json_encode([
            'success' => false,
            'error' => '重置失败，请联系管理员'
        ]);
        exit;
    }

    /**
     * 检查是否已登录
     */
    public static function checkLogin()
    {
        if (!isset($_SESSION['user']) || empty($_SESSION['user'])) {
            if (isset($_SERVER['HTTP_X_REQUESTED_WITH']) &&
                strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest') {
                header('Content-Type: application/json');
                http_response_code(401);
                echo json_encode([
                    'success' => false,
                    'error' => '未登录或会话已过期'
                ]);
                exit;
            } else {
                header('Location: /login');
                exit;
            }
        }
    }
}
