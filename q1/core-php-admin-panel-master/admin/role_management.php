<?php
require_once '../config/config.php';
require_once BASE_PATH.'/includes/auth_validate.php';

$db = getDbInstance();
$rows = $db->get('roles');

include BASE_PATH.'/includes/header.php';
?>
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-12">
            <h1 class="page-header">角色管理</h1>
        </div>
    </div>
    <?php include BASE_PATH.'/includes/flash_messages.php'; ?>

    <table class="table table-striped table-bordered">
        <thead>
            <tr>
                <th width="10%">ID</th>
                <th width="25%">角色标识</th>
                <th width="35%">显示名称</th>
                <th width="30%">创建时间</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($rows as $row): ?>
            <tr>
                <td><?php echo $row['id']; ?></td>
                <td><?php echo htmlspecialchars($row['name']); ?></td>
                <td><?php echo htmlspecialchars($row['display_name']); ?></td>
                <td><?php echo htmlspecialchars($row['created_at']); ?></td>
            </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
</div>
<?php include BASE_PATH.'/includes/footer.php'; ?>
