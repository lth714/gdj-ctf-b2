<?php
// api/middleware.php
session_start();

function apiRequireAuth() {
    if (!isset($_SESSION['user_logged_in']) || $_SESSION['user_logged_in'] !== true) {
        http_response_code(401);
        echo json_encode(array('code' => 401, 'message' => '未授权访问，请先登录'), JSON_UNESCAPED_UNICODE);
        exit;
    }
}

function apiRequireRole($role) {
    apiRequireAuth();
    if ($_SESSION['role'] !== $role && $_SESSION['role'] !== 'admin') {
        http_response_code(403);
        echo json_encode(array('code' => 403, 'message' => '权限不足'), JSON_UNESCAPED_UNICODE);
        exit;
    }
}

function getJsonBody() {
    $raw = file_get_contents('php://input');
    $data = json_decode($raw, true);
    return $data ? $data : array();
}

function apiResponse($code, $message, $data = null) {
    http_response_code($code >= 400 ? $code : 200);
    $resp = array('code' => $code, 'message' => $message);
    if ($data !== null) {
        $resp['data'] = $data;
    }
    echo json_encode($resp, JSON_UNESCAPED_UNICODE);
    exit;
}
