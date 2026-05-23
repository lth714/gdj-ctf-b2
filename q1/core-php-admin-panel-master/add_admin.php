<?php
require_once './config/config.php';
require_once 'includes/auth_validate.php';


if ($_SERVER['REQUEST_METHOD'] == 'POST')
{
    $data_to_store = filter_input_array(INPUT_POST);
    $db = getDbInstance();
    //Check whether the user name already exists ;
    $db->where('username', $data_to_store['username']);
    $db->get('users');

    if($db->count >=1){
        $_SESSION['failure'] = "用户名已存在";
        header('location: add_admin.php');
        exit();
    }

    //Encrypt password
    $data_to_store['password_hash'] = password_hash($data_to_store['password'], PASSWORD_DEFAULT);
    unset($data_to_store['password']);
    //reset db instance
    $db = getDbInstance();
    $last_id = $db->insert('users', $data_to_store);
    if($last_id)
    {

        $_SESSION['success'] = "用户添加成功";
        header('location: admin_users.php');
        exit();
    }

}

$edit = false;


require_once 'includes/header.php';
?>
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-12">
            <h2 class="page-header">添加用户</h2>
        </div>
    </div>
     <?php
    include_once('includes/flash_messages.php');
    ?>
    <form class="well form-horizontal" action=" " method="post"  id="contact_form" enctype="multipart/form-data">
        <?php include_once './forms/admin_users_form.php'; ?>
    </form>
</div>




<?php include_once 'includes/footer.php'; ?>