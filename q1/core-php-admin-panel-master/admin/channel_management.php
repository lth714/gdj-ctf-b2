<?php
require_once '../config/config.php';
require_once BASE_PATH.'/includes/auth_validate.php';

$db = getDbInstance();

// Handle POST for add
if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['action'])) {
    if ($_POST['action'] == 'add') {
        $data = filter_input_array(INPUT_POST, FILTER_SANITIZE_STRING);
        unset($data['action']);
        $db->insert('channels', $data);
        $_SESSION['success'] = "频道添加成功";
    } elseif ($_POST['action'] == 'edit') {
        $id = filter_input(INPUT_POST, 'id', FILTER_VALIDATE_INT);
        $data = filter_input_array(INPUT_POST, FILTER_SANITIZE_STRING);
        unset($data['action'], $data['id']);
        $db->where('id', $id);
        $db->update('channels', $data);
        $_SESSION['success'] = "频道更新成功";
    }
    header('Location: channel_management.php');
    exit;
}

// Handle delete (soft)
if (isset($_GET['del_id'])) {
    $db->where('id', filter_input(INPUT_GET, 'del_id', FILTER_VALIDATE_INT));
    $db->update('channels', array('status' => 0));
    $_SESSION['info'] = "频道已停用";
    header('Location: channel_management.php');
    exit;
}

// Search & Pagination
$search_string = filter_input(INPUT_GET, 'search_string');
$page = filter_input(INPUT_GET, 'page') ?: 1;
$pagelimit = 20;

if ($search_string) {
    $db->where('name', '%' . $search_string . '%', 'like');
}
$db->orderBy('sort_order', 'Asc');
$db->pageLimit = $pagelimit;
$rows = $db->arraybuilder()->paginate('channels', $page);
$total_pages = $db->totalPages;

include BASE_PATH.'/includes/header.php';
?>
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-6">
            <h1 class="page-header">频道栏目管理</h1>
        </div>
        <div class="col-lg-6">
            <div class="page-action-links text-right">
                <button class="btn btn-success" data-toggle="modal" data-target="#addModal"><i class="glyphicon glyphicon-plus"></i> 添加频道</button>
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
                <th>频道名称</th>
                <th>频道编码</th>
                <th>排序</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($rows as $row): ?>
            <tr>
                <td><?php echo $row['id']; ?></td>
                <td><?php echo htmlspecialchars($row['name']); ?></td>
                <td><?php echo htmlspecialchars($row['code']); ?></td>
                <td><?php echo $row['sort_order']; ?></td>
                <td><?php echo $row['status'] == 1 ? '<span class="label label-success">启用</span>' : '<span class="label label-warning">停用</span>'; ?></td>
                <td><?php echo htmlspecialchars($row['created_at']); ?></td>
                <td>
                    <button class="btn btn-primary btn-sm edit-btn" data-id="<?php echo $row['id']; ?>" data-name="<?php echo htmlspecialchars($row['name']); ?>" data-code="<?php echo htmlspecialchars($row['code']); ?>" data-sort="<?php echo $row['sort_order']; ?>" data-status="<?php echo $row['status']; ?>"><i class="glyphicon glyphicon-edit"></i></button>
                    <a href="?del_id=<?php echo $row['id']; ?>" class="btn btn-danger btn-sm" onclick="return confirm('确定要停用该频道吗？')"><i class="glyphicon glyphicon-trash"></i></a>
                </td>
            </tr>
            <?php endforeach; ?>
        </tbody>
    </table>

    <!-- Pagination -->
    <div class="text-center">
        <?php
        if ($total_pages > 1) {
            echo '<ul class="pagination text-center">';
            for ($i = 1; $i <= $total_pages; $i++) {
                ($page == $i) ? $li_class = ' class="active"' : $li_class = '';
                echo '<li' . $li_class . '><a href="channel_management.php?page=' . $i . '">' . $i . '</a></li>';
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
                    <h4 class="modal-title">添加频道</h4>
                </div>
                <div class="modal-body">
                    <input type="hidden" name="action" value="add">
                    <div class="form-group">
                        <label>频道名称</label>
                        <input type="text" name="name" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label>频道编码</label>
                        <input type="text" name="code" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label>排序</label>
                        <input type="number" name="sort_order" class="form-control" value="0">
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

<!-- Edit Modal -->
<div class="modal fade" id="editModal" role="dialog">
    <div class="modal-dialog">
        <form method="POST">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal">&times;</button>
                    <h4 class="modal-title">编辑频道</h4>
                </div>
                <div class="modal-body">
                    <input type="hidden" name="action" value="edit">
                    <input type="hidden" name="id" id="edit-id">
                    <div class="form-group">
                        <label>频道名称</label>
                        <input type="text" name="name" id="edit-name" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label>频道编码</label>
                        <input type="text" name="code" id="edit-code" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label>排序</label>
                        <input type="number" name="sort_order" id="edit-sort" class="form-control" value="0">
                    </div>
                    <div class="form-group">
                        <label>状态</label>
                        <select name="status" id="edit-status" class="form-control">
                            <option value="1">启用</option>
                            <option value="0">停用</option>
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

<script>
$('.edit-btn').click(function() {
    $('#edit-id').val($(this).data('id'));
    $('#edit-name').val($(this).data('name'));
    $('#edit-code').val($(this).data('code'));
    $('#edit-sort').val($(this).data('sort'));
    $('#edit-status').val($(this).data('status'));
    $('#editModal').modal('show');
});
</script>
<?php include BASE_PATH.'/includes/footer.php'; ?>
