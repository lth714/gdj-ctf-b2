<?php
require_once '../config/config.php';
require_once BASE_PATH.'/includes/auth_validate.php';

$db = getDbInstance();

// Search & Pagination
$search_string = filter_input(INPUT_GET, 'search_string');
$page = filter_input(INPUT_GET, 'page') ?: 1;
$pagelimit = 25;

if ($search_string) {
    $db->where('username', '%' . $search_string . '%', 'like');
}
$db->orderBy('created_at', 'Desc');
$db->pageLimit = $pagelimit;
$rows = $db->arraybuilder()->paginate('operation_logs', $page);
$total_pages = $db->totalPages;

include BASE_PATH.'/includes/header.php';
?>
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-12">
            <h1 class="page-header">操作日志</h1>
        </div>
    </div>
    <?php include BASE_PATH.'/includes/flash_messages.php'; ?>

    <div class="well text-center filter-form">
        <form class="form form-inline" action="">
            <label for="input_search">搜索用户</label>
            <input type="text" class="form-control" name="search_string" value="<?php echo htmlspecialchars($search_string); ?>">
            <input type="submit" value="查询" class="btn btn-primary">
        </form>
    </div>
    <hr>

    <table class="table table-striped table-bordered table-condensed">
        <thead>
            <tr>
                <th>ID</th>
                <th>操作用户</th>
                <th>操作类型</th>
                <th>IP地址</th>
                <th>操作时间</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($rows as $row): ?>
            <tr>
                <td><?php echo $row['id']; ?></td>
                <td><?php echo htmlspecialchars($row['username']); ?></td>
                <td><?php echo htmlspecialchars($row['action']); ?></td>
                <td><?php echo htmlspecialchars($row['ip']); ?></td>
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
                echo '<li' . $li_class . '><a href="operation_logs.php?page=' . $i . '">' . $i . '</a></li>';
            }
            echo '</ul>';
        }
        ?>
    </div>
</div>
<?php include BASE_PATH.'/includes/footer.php'; ?>
