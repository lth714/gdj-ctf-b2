<?php
require_once '../config/config.php';
require_once BASE_PATH.'/includes/auth_validate.php';

$db = getDbInstance();

// Handle POST for add
if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['action']) && $_POST['action'] == 'add') {
    $data = filter_input_array(INPUT_POST, FILTER_SANITIZE_STRING);
    unset($data['action']);
    $data['status'] = 'pending';
    $db->insert('epg_files', $data);
    $_SESSION['success'] = "EPG文件导入成功";
    header('Location: epg_management.php');
    exit;
}

// Search & Pagination
$search_string = filter_input(INPUT_GET, 'search_string');
$page = filter_input(INPUT_GET, 'page') ?: 1;
$pagelimit = 20;

if ($search_string) {
    $db->where('file_name', '%' . $search_string . '%', 'like');
}
$db->orderBy('created_at', 'Desc');
$db->pageLimit = $pagelimit;
$rows = $db->arraybuilder()->paginate('epg_files', $page);
$total_pages = $db->totalPages;

include BASE_PATH.'/includes/header.php';
?>
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-6">
            <h1 class="page-header">EPG文件管理</h1>
        </div>
        <div class="col-lg-6">
            <div class="page-action-links text-right">
                <button class="btn btn-success" data-toggle="modal" data-target="#addModal"><i class="glyphicon glyphicon-plus"></i> 导入EPG</button>
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
                <th>文件名</th>
                <th>频道编码</th>
                <th>发布日期</th>
                <th>状态</th>
                <th>上传时间</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($rows as $row): ?>
            <tr>
                <td><?php echo $row['id']; ?></td>
                <td><?php echo htmlspecialchars($row['file_name']); ?></td>
                <td><?php echo htmlspecialchars($row['channel_code']); ?></td>
                <td><?php echo htmlspecialchars($row['publish_date']); ?></td>
                <td>
                    <?php
                    if ($row['status'] == 'pending') echo '<span class="label label-warning">待审核</span>';
                    elseif ($row['status'] == 'published') echo '<span class="label label-success">已发布</span>';
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
                echo '<li' . $li_class . '><a href="epg_management.php?page=' . $i . '">' . $i . '</a></li>';
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
                    <h4 class="modal-title">导入EPG文件</h4>
                </div>
                <div class="modal-body">
                    <input type="hidden" name="action" value="add">
                    <div class="form-group">
                        <label>文件名</label>
                        <input type="text" name="file_name" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label>频道编码</label>
                        <select name="channel_code" class="form-control">
                            <option value="cctv1">cctv1 - CCTV-1 综合</option>
                            <option value="cctv2">cctv2 - CCTV-2 财经</option>
                            <option value="cctv13">cctv13 - CCTV-新闻</option>
                            <option value="cctv5">cctv5 - CCTV-体育</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>发布日期</label>
                        <input type="date" name="publish_date" class="form-control" required>
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
