<?php
require_once 'includes/auth_validate.php';
require_once './config/config.php';
$del_id = filter_input(INPUT_POST, 'del_id');
 $db = getDbInstance();

// Soft delete: set status to 0 (disabled) instead of actually deleting
if ($del_id && $_SERVER['REQUEST_METHOD'] == 'POST') {

    $db->where('id', $del_id);
    $stat = $db->update('users', array('status' => 0));
    if ($stat) {
        $_SESSION['info'] = "用户已禁用";
        header('location: admin_users.php');
        exit;
    }
}