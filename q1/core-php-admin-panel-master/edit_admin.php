<?php
require_once './config/config.php';
require_once 'includes/auth_validate.php';

//User ID for which we are performing operation
$admin_user_id = filter_input(INPUT_GET, 'admin_user_id');
$operation = filter_input(INPUT_GET, 'operation', FILTER_SANITIZE_STRING);
($operation == 'edit') ? $edit = true : $edit = false;
//Serve POST request.
if ($_SERVER['REQUEST_METHOD'] == 'POST') {

    // Sanitize input post if we want
    $data_to_update = filter_input_array(INPUT_POST);
    //Check whether the user name already exists ;
    $db = getDbInstance();
    $db->where('username', $data_to_update['username']);
    $db->where('id', $admin_user_id, '!=');
    $row = $db->getOne('users');

    if (!empty($row['username'])) {

        $_SESSION['failure'] = "用户名已存在";

        $query_string = http_build_query(array(
            'admin_user_id' => $admin_user_id,
            'operation' => $operation,
        ));
        header('location: edit_admin.php?'.$query_string );
        exit;
    }

    $admin_user_id = filter_input(INPUT_GET, 'admin_user_id', FILTER_VALIDATE_INT);

    // Handle password: only hash if a new one is provided
    if (!empty($data_to_update['password'])) {
        $data_to_update['password_hash'] = password_hash($data_to_update['password'], PASSWORD_DEFAULT);
    }
    unset($data_to_update['password']);

    $db = getDbInstance();
    $db->where('id', $admin_user_id);
    $stat = $db->update('users', $data_to_update);

    if ($stat) {
        $_SESSION['success'] = "用户更新成功";
    } else {
        $_SESSION['failure'] = "用户更新失败: " . $db->getLastError();
    }

    header('location: admin_users.php');
    exit;

}

//Select where clause
$db = getDbInstance();
$db->where('id', $admin_user_id);

$user = $db->getOne("users");

// import header
require_once 'includes/header.php';
?>
<div id="page-wrapper">

    <div class="row">
     <div class="col-lg-12">
            <h2 class="page-header">编辑用户</h2>
        </div>

    </div>
    <?php include_once 'includes/flash_messages.php';?>
    <form class="well form-horizontal" action="" method="post"  id="contact_form" enctype="multipart/form-data">
        <?php include_once './forms/admin_users_form.php';?>
    </form>
</div>




<?php include_once 'includes/footer.php';?>