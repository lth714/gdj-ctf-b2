<?php
require_once '../config/config.php';
require_once BASE_PATH.'/includes/auth_validate.php';

$db = getDbInstance();

// Handle POST for add
if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['action']) && $_POST['action'] == 'add') {
    $data = filter_input_array(INPUT_POST, FILTER_SANITIZE_STRING);
    unset($data['action']);
    $data['status'] = 'pending';
    $data['uploader_id'] = $_SESSION['user_id'] ?? null;
    $db->insert('materials', $data);
    $_SESSION['success'] = "素材添加成功";
    header('Location: material_management.php');
    exit;
}

// Search & Pagination
$search_string = filter_input(INPUT_GET, 'search_string');
$page = filter_input(INPUT_GET, 'page') ?: 1;
$pagelimit = 20;

if ($search_string) {
    $db->where('title', '%' . $search_string . '%', 'like');
}
$db->orderBy('created_at', 'Desc');
$db->pageLimit = $pagelimit;
$rows = $db->arraybuilder()->paginate('materials', $page);
$total_pages = $db->totalPages;

include BASE_PATH.'/includes/header.php';
?>
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-6">
            <h1 class="page-header">节目素材管理</h1>
        </div>
        <div class="col-lg-6">
            <div class="page-action-links text-right">
                <button class="btn btn-success" data-toggle="modal" data-target="#addModal"><i class="glyphicon glyphicon-plus"></i> 上传素材</button>
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
                <th>素材标题</th>
                <th>类型</th>
                <th>状态</th>
                <th>创建时间</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($rows as $row): ?>
            <tr>
                <td><?php echo $row['id']; ?></td>
                <td><?php echo htmlspecialchars($row['title']); ?></td>
                <td><?php echo htmlspecialchars($row['type']); ?></td>
                <td>
                    <?php
                    if ($row['status'] == 'pending') echo '<span class="label label-warning">待审核</span>';
                    elseif ($row['status'] == 'approved') echo '<span class="label label-success">已审核</span>';
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
                echo '<li' . $li_class . '><a href="material_management.php?page=' . $i . '">' . $i . '</a></li>';
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
                    <h4 class="modal-title">上传节目素材</h4>
                </div>
                <div class="modal-body">
                    <input type="hidden" name="action" value="add">
                    <div class="form-group">
                        <label>素材标题</label>
                        <input type="text" name="title" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label>素材类型</label>
                        <select name="type" class="form-control">
                            <option value="视频">视频</option>
                            <option value="音频">音频</option>
                            <option value="图片">图片</option>
                            <option value="文档">文档</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>文件路径</label>
                        <input type="text" name="file_path" class="form-control" placeholder="上传后自动填充">
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
