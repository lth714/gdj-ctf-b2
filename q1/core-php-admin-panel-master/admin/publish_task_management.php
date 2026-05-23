<?php
require_once '../config/config.php';
require_once BASE_PATH.'/includes/auth_validate.php';

$db = getDbInstance();

// Handle POST for add
if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['action']) && $_POST['action'] == 'add') {
    $data = filter_input_array(INPUT_POST, FILTER_SANITIZE_STRING);
    unset($data['action']);
    $data['status'] = 'pending';
    $data['created_at'] = date('Y-m-d H:i:s');
    $db->insert('publish_tasks', $data);
    $_SESSION['success'] = "发布任务创建成功";
    header('Location: publish_task_management.php');
    exit;
}

// Search & Pagination
$search_string = filter_input(INPUT_GET, 'search_string');
$page = filter_input(INPUT_GET, 'page') ?: 1;
$pagelimit = 20;

if ($search_string) {
    $db->where('task_name', '%' . $search_string . '%', 'like');
}
$db->orderBy('created_at', 'Desc');
$db->pageLimit = $pagelimit;
$rows = $db->arraybuilder()->paginate('publish_tasks', $page);
$total_pages = $db->totalPages;

include BASE_PATH.'/includes/header.php';
?>
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-6">
            <h1 class="page-header">发布任务管理</h1>
        </div>
        <div class="col-lg-6">
            <div class="page-action-links text-right">
                <button class="btn btn-success" data-toggle="modal" data-target="#addModal"><i class="glyphicon glyphicon-plus"></i> 创建任务</button>
            </div>
        </div>
    </div>
    <?php include BASE_PATH.'/includes/flash_messages.php'; ?>

    <div class="well text-center filter-form">
        <form class="form form-inline" action="">
            <label for="input_search">搜索</label>
            <input type="text" class="form-control" name="search_string" value="<?php echo htmlspecialchars($search_string); ?>">
            <input type="submit" value="查询" class="btn btn-primary">
        </form>
    </div>
    <hr>

    <table class="table table-striped table-bordered table-condensed">
        <thead>
            <tr>
                <th>ID</th>
                <th>任务名称</th>
                <th>任务类型</th>
                <th>目标节点</th>
                <th>状态</th>
                <th>创建时间</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($rows as $row): ?>
            <tr>
                <td><?php echo $row['id']; ?></td>
                <td><?php echo htmlspecialchars($row['task_name']); ?></td>
                <td><?php echo htmlspecialchars($row['task_type']); ?></td>
                <td><?php echo htmlspecialchars($row['target_node']); ?></td>
                <td>
                    <?php
                    if ($row['status'] == 'pending') echo '<span class="label label-warning">等待中</span>';
                    elseif ($row['status'] == 'running') echo '<span class="label label-info">执行中</span>';
                    elseif ($row['status'] == 'completed') echo '<span class="label label-success">已完成</span>';
                    else echo '<span class="label label-default">' . htmlspecialchars($row['status']) . '</span>';
                    ?>
                </td>
                <td><?php echo htmlspecialchars($row['created_at']); ?></td>
            </tr>
            <?php endforeach; ?>
        </tbody>
    </table>

    <div class="text-center">
        <?php
        if ($total_pages > 1) {
            echo '<ul class="pagination text-center">';
            for ($i = 1; $i <= $total_pages; $i++) {
                ($page == $i) ? $li_class = ' class="active"' : $li_class = '';
                echo '<li' . $li_class . '><a href="publish_task_management.php?page=' . $i . '">' . $i . '</a></li>';
            }
            echo '</ul>';
        }
        ?>
    </div>
</div>

<!-- Add Modal -->
<div class="modal fade" id="addModal" role="dialog">
    <div class="modal-dialog">
        <form method="POST">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal">&times;</button>
                    <h4 class="modal-title">创建发布任务</h4>
                </div>
                <div class="modal-body">
                    <input type="hidden" name="action" value="add">
                    <div class="form-group">
                        <label>任务名称</label>
                        <input type="text" name="task_name" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label>任务类型</label>
                        <select name="task_type" class="form-control">
                            <option value="epg_sync">EPG同步</option>
                            <option value="cover_refresh">频道封面刷新</option>
                            <option value="material_push">节目素材发布</option>
                            <option value="cache_warmup">缓存预热</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>目标节点</label>
                        <select name="target_node" class="form-control">
                            <option value="华北缓存节点-01">华北缓存节点-01</option>
                            <option value="华东缓存节点-01">华东缓存节点-01</option>
                            <option value="华南缓存节点-01">华南缓存节点-01</option>
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="submit" class="btn btn-success">保存</button>
                    <button type="button" class="btn btn-default" data-dismiss="modal">取消</button>
                </div>
            </div>
        </form>
    </div>
</div>
<?php include BASE_PATH.'/includes/footer.php'; ?>
