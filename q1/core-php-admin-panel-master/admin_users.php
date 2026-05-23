<?php
require_once 'config/config.php';
require_once BASE_PATH.'/includes/auth_validate.php';

// Users class
require_once BASE_PATH.'/lib/Users/Users.php';
$users = new Users();

// Get Input data from query string
$search_string = filter_input(INPUT_GET, 'search_string');
$filter_col = filter_input(INPUT_GET, 'filter_col');
$order_by = filter_input(INPUT_GET, 'order_by');

// Per page limit for pagination.
$pagelimit = 20;

// Get current page.
$page = filter_input(INPUT_GET, 'page');
if (!$page)
{
    $page = 1;
}

// If filter types are not selected we show latest added data first
if (!$filter_col)
{
    $filter_col = 'id';
}
if (!$order_by)
{
    $order_by = 'Desc';
}

//Get DB instance.
$db = getDbInstance();
$select = array('id', 'username', 'nickname', 'email', 'role', 'status', 'created_at');

//Start building query according to input parameters.
if ($search_string)
{
    $db->where('username', '%' . $search_string . '%', 'like');
}

if ($order_by)
{
    $db->orderBy($filter_col, $order_by);
}

// Set pagination limit
$db->pageLimit = $pagelimit;

// Get result of the query.
$rows = $db->arraybuilder()->paginate('users', $page, $select);
$total_pages = $db->totalPages;

include BASE_PATH.'/includes/header.php';
?>
<!-- Main container -->
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-6">
            <h1 class="page-header">用户管理</h1>
        </div>
        <div class="col-lg-6">
            <div class="page-action-links text-right">
                <a href="add_admin.php" class="btn btn-success"><i class="glyphicon glyphicon-plus"></i> 添加用户</a>
            </div>
        </div>
    </div>
    <?php include BASE_PATH.'/includes/flash_messages.php'; ?>

    <!-- Filters -->
    <div class="well text-center filter-form">
        <form class="form form-inline" action="">
            <label for="input_search">搜索</label>
            <input type="text" class="form-control" id="input_search" name="search_string" value="<?php echo htmlspecialchars($search_string, ENT_QUOTES, 'UTF-8'); ?>">
            <label for="input_order">排序</label>
            <select name="filter_col" class="form-control">
                <?php
                foreach ($users->setOrderingValues() as $opt_value => $opt_name):
                    ($order_by === $opt_value) ? $selected = 'selected' : $selected = '';
                    echo ' <option value="'.$opt_value.'" '.$selected.'>'.$opt_name.'</option>';
                endforeach;
                ?>
            </select>
            <select name="order_by" class="form-control" id="input_order">
                <option value="Asc" <?php
                if ($order_by == 'Asc') {
                    echo 'selected';
                }
                ?> >升序</option>
                <option value="Desc" <?php
                if ($order_by == 'Desc') {
                    echo 'selected';
                }
                ?>>降序</option>
            </select>
            <input type="submit" value="查询" class="btn btn-primary">
        </form>
    </div>
    <hr>
    <!-- //Filters -->

    <!-- Table -->
    <table class="table table-striped table-bordered table-condensed">
        <thead>
            <tr>
                <th width="5%">ID</th>
                <th width="15%">用户名</th>
                <th width="15%">昵称</th>
                <th width="20%">邮箱</th>
                <th width="10%">角色</th>
                <th width="10%">状态</th>
                <th width="15%">创建时间</th>
                <th width="10%">操作</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($rows as $row): ?>
            <tr>
                <td><?php echo $row['id']; ?></td>
                <td><?php echo htmlspecialchars($row['username']); ?></td>
                <td><?php echo htmlspecialchars($row['nickname']); ?></td>
                <td><?php echo htmlspecialchars($row['email']); ?></td>
                <td>
                    <?php
                    $roleLabel = $row['role'];
                    if ($row['role'] == 'admin') echo '<span class="label label-danger">系统管理员</span>';
                    elseif ($row['role'] == 'operator') echo '<span class="label label-primary">运营人员</span>';
                    else echo '<span class="label label-default">编辑人员</span>';
                    ?>
                </td>
                <td>
                    <?php if ($row['status'] == 1): ?>
                        <span class="label label-success">启用</span>
                    <?php else: ?>
                        <span class="label label-warning">禁用</span>
                    <?php endif; ?>
                </td>
                <td><?php echo htmlspecialchars($row['created_at']); ?></td>
                <td>
                    <a href="edit_admin.php?admin_user_id=<?php echo $row['id']; ?>&operation=edit" class="btn btn-primary"><i class="glyphicon glyphicon-edit"></i></a>
                    <a href="#" class="btn btn-danger delete_btn" data-toggle="modal" data-target="#confirm-delete-<?php echo $row['id']; ?>"><i class="glyphicon glyphicon-trash"></i></a>
                </td>
            </tr>
            <!-- Delete Confirmation Modal -->
            <div class="modal fade" id="confirm-delete-<?php echo $row['id']; ?>" role="dialog">
                <div class="modal-dialog">
                    <form action="delete_user.php" method="POST">
                        <div class="modal-content">
                            <div class="modal-header">
                                <button type="button" class="close" data-dismiss="modal">&times;</button>
                                <h4 class="modal-title">确认操作</h4>
                            </div>
                            <div class="modal-body">
                                <input type="hidden" name="del_id" id="del_id" value="<?php echo $row['id']; ?>">
                                <p>确定要禁用该用户吗？</p>
                            </div>
                            <div class="modal-footer">
                                <button type="submit" class="btn btn-default pull-left">确认</button>
                                <button type="button" class="btn btn-default" data-dismiss="modal">取消</button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            <!-- //Delete Confirmation Modal -->
            <?php endforeach; ?>
        </tbody>
    </table>
    <!-- //Table -->

    <!-- Pagination -->
    <div class="text-center">
        <?php
        if (!empty($_GET)) {
            unset($_GET['page']);
            $http_query = "?" . http_build_query($_GET);
        } else {
            $http_query = "?";
        }
        if ($total_pages > 1) {
            echo '<ul class="pagination text-center">';
            for ($i = 1; $i <= $total_pages; $i++) {
                ($page == $i) ? $li_class = ' class="active"' : $li_class = '';
                echo '<li' . $li_class . '><a href="admin_users.php' . $http_query . '&page=' . $i . '">' . $i . '</a></li>';
            }
            echo '</ul>';
        }
        ?>
    </div>
    <!-- //Pagination -->
</div>
<!-- //Main container -->
<?php include BASE_PATH.'/includes/footer.php'; ?>