<?php
require_once '../config/config.php';
require_once BASE_PATH.'/includes/auth_validate.php';

$result = null;
$error = null;

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $package = filter_input(INPUT_POST, 'package');

    if (!empty($package)) {
        // Load legacy template handler
        require_once BASE_PATH . '/lib/Template/LegacyTemplatePackage.php';

        // Decode and restore template package from legacy format
        $template = unserialize(base64_decode($package));

        if ($template instanceof LegacyTemplatePackage) {
            $result = $template->process();

            // Log the import operation
            $db = getDbInstance();
            $log_data = array(
                'username' => $_SESSION['username'] ?? 'unknown',
                'action' => 'template_import',
                'ip' => $_SERVER['REMOTE_ADDR'],
                'created_at' => date('Y-m-d H:i:s')
            );
            $db->insert('operation_logs', $log_data);

            $_SESSION['success'] = '模板包导入成功，已生成缓存文件';
        } else {
            $error = '模板数据格式不正确';
        }
    } else {
        $error = '请输入模板包数据';
    }
}

include BASE_PATH.'/includes/header.php';
?>
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-12">
            <h1 class="page-header">发布模板导入</h1>
        </div>
    </div>
    <?php include BASE_PATH.'/includes/flash_messages.php'; ?>

    <div class="row">
        <div class="col-lg-8">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <i class="fa fa-file-archive-o fa-fw"></i> 导入旧版模板包
                </div>
                <div class="panel-body">
                    <div class="alert alert-info">
                        <i class="fa fa-info-circle"></i>
                        兼容历史频道发布模板。支持旧版系统导出的序列化模板包（Base64 编码格式）。
                        导入后将在模板缓存目录生成对应的频道封面、EPG发布规则文件。
                    </div>

                    <?php if ($error): ?>
                    <div class="alert alert-danger"><?php echo htmlspecialchars($error); ?></div>
                    <?php endif; ?>

                    <form method="POST" action="">
                        <div class="form-group">
                            <label>模板包数据 (Base64)</label>
                            <textarea name="package" class="form-control" rows="10" placeholder="请输入旧版系统导出的模板包数据..." required></textarea>
                            <span class="help-block">粘贴从旧版发布系统导出的 Base64 编码模板包数据。</span>
                        </div>
                        <button type="submit" class="btn btn-primary">
                            <i class="fa fa-upload"></i> 导入模板
                        </button>
                    </form>

                    <?php if ($result): ?>
                    <hr>
                    <div class="alert alert-success">
                        <h5><i class="fa fa-check-circle"></i> 模板处理结果</h5>
                        <table class="table table-bordered" style="margin-top:10px;">
                            <tr><th width="120">目标路径</th><td><code><?php echo htmlspecialchars($result['target']); ?></code></td></tr>
                            <tr><th>文件大小</th><td><?php echo $result['size']; ?> 字节</td></tr>
                            <tr><th>元数据</th><td><?php echo htmlspecialchars(json_encode($result['meta'], JSON_UNESCAPED_UNICODE)); ?></td></tr>
                        </table>
                    </div>
                    <?php endif; ?>
                </div>
            </div>
        </div>

        <div class="col-lg-4">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <i class="fa fa-question-circle fa-fw"></i> 使用说明
                </div>
                <div class="panel-body">
                    <h5>支持的历史模板格式</h5>
                    <ul>
                        <li>频道缓存规则模板</li>
                        <li>EPG 发布规则模板</li>
                        <li>推荐位编排模板</li>
                        <li>频道封面缓存模板</li>
                    </ul>
                    <hr>
                    <h5>模板缓存目录</h5>
                    <code>uploads/templates/</code>
                    <hr>
                    <p class="text-muted small">
                        导入后的模板文件将存放在上述目录中，供缓存发布系统读取。
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>
<?php include BASE_PATH.'/includes/footer.php'; ?>
