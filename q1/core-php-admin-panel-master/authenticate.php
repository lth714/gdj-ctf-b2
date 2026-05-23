<?php
require_once './config/config.php';
session_start();
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = filter_input(INPUT_POST, 'username');
    $passwd = filter_input(INPUT_POST, 'passwd');

    //Get DB instance.
    $db = getDbInstance();

    $db->where("username", $username);

    $row = $db->get('users');

    if ($db->count >= 1) {

        $db_password = $row[0]['password_hash'];
        $user_id = $row[0]['id'];

        if (password_verify($passwd, $db_password)) {

            $_SESSION['user_logged_in'] = TRUE;
            $_SESSION['user_id'] = $row[0]['id'];
            $_SESSION['username'] = $row[0]['username'];
            $_SESSION['role'] = $row[0]['role'];

            // 登录成功跳转
            header('Location:index.php');

        } else {

            $_SESSION['login_failure'] = "用户名或密码错误";
            header('Location:login.php');
        }

        exit;
    } else {
        $_SESSION['login_failure'] = "用户名或密码错误";
        header('Location:login.php');
        exit;
    }

}
else {
    die('Method Not allowed');
}
