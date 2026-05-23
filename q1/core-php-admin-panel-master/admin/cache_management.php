<?php
require_once '../config/config.php';
require_once BASE_PATH.'/includes/auth_validate.php';

$db = getDbInstance();

// Handle cache refresh action
if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['action']) && $_POST['action'] == 'refresh') {
    $node_id = filter_input(INPUT_POST, 'node_id', FILTER_VALIDATE_INT);
    // Log the cache refresh operation
    $log_data = array(
        'username' => $_SESSION['username'] ?? 'unknown',
        'action' => 'cache_refresh',
        'ip' => $_SERVER['REMOTE_ADDR'],
        'created_at' => date('Y-m-d H:i:s')
    );
    $db->insert('operation_logs', $log_data);

    // Update node heartbeat
    if ($node_id) {
        $db->where('id', $node_id);
        $db->update('cache_nodes', array('last_heartbeat' => date('Y-m-d H:i:s'), 'status' => 'online'));
    }

    $_SESSION['success'] = "缓存刷新指令已发送至支撑节点";
    header('Location: cache_management.php');
    exit;
}

// Get all cache nodes
$rows = $db->get('cache_nodes');

include BASE_PATH.'/includes/header.php';
?>
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-12">
            <h1 class="page-header">缓存刷新管理</h1>
        </div>
    </div>
    <?php include BASE_PATH.'/includes/flash_messages.php'; ?>

    <div class="row">
        <div class="col-lg-12">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <i class="fa fa-server fa-fw"></i> 缓存发布支撑节点状态
                </div>
                <div class="panel-body">
                    <table class="table table-striped table-bordered">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>节点名称</th>
                                <th>节点地址</th>
                                <th>状态</th>
                                <th>最后心跳</th>
                                <th>备注</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($rows as $row): ?>
                            <tr>
                                <td><?php echo $row['id']; ?></td>
                                <td><?php echo htmlspecialchars($row['node_name']); ?></td>
                                <td><?php echo htmlspecialchars($row['ip'] . ':' . $row['port']); ?></td>
                                <td>
                                    <?php if ($row['status'] == 'online'): ?>
                                        <span class="label label-success">在线</span>
                                    <?php else: ?>
                                        <span class="label label-danger">离线</span>
                                    <?php endif; ?>
                                </td>
                                <td><?php echo htmlspecialchars($row['last_heartbeat']); ?></td>
                                <td><?php echo htmlspecialchars($row['remark']); ?></td>
                                <td>
                                    <form method="POST" style="display:inline">
                                        <input type="hidden" name="action" value="refresh">
                                        <input type="hidden" name="node_id" value="<?php echo $row['id']; ?>">
                                        <button type="submit" class="btn btn-primary btn-sm"><i class="fa fa-refresh"></i> 刷新缓存</button>
                                    </form>
                                </td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
<?php include BASE_PATH.'/includes/footer.php'; ?>
