<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>编辑频道 - IPTV 代理系统</title>
    <link href="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <?php $currentPage = 'channels'; ?>
    <?php require __DIR__ . '/../../navbar.php'; ?>

    <div class="container-fluid mx-auto" style="width: 98%;">
        <div class="row">
            <div class="col-md-12">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h2>编辑频道</h2>
                    <a href="/admin/channels" class="btn btn-secondary">返回列表</a>
                </div>

                <?php if (isset($_SESSION['flash_message'])): ?>
                    <div class="alert alert-<?= $_SESSION['flash_message']['type'] ?>">
                        <?= $_SESSION['flash_message']['message'] ?>
                    </div>
                    <?php unset($_SESSION['flash_message']); ?>
                <?php endif; ?>

                <div class="card">
                    <div class="card-body">
                        <form action="/admin/channels/update/<?= $channel['id'] ?>" method="POST">
                            <div class="mb-3">
                                <label for="name" class="form-label">频道名称</label>
                                <input type="text" class="form-control" id="name" name="name" value="<?= htmlspecialchars($channel['name']) ?>" required>
                            </div>

                            <div class="mb-3">
                                <label for="source_url" class="form-label">源地址</label>
                                <input type="url" class="form-control" id="source_url" name="source_url" value="<?= htmlspecialchars($channel['source_url']) ?>" required>
                                <div class="form-text">支持 HTTP/HTTPS/RTMP/RTSP 等流媒体地址</div>
                            </div>

                            <div class="mb-3">
                                <label for="proxy_url" class="form-label">代理地址</label>
                                <input type="text" class="form-control" id="proxy_url" value="<?= htmlspecialchars($channel['proxy_url']) ?>" readonly>
                                <div class="form-text">代理地址不可修改</div>
                            </div>

                            <div class="mb-3">
                                <label for="group_id" class="form-label">所属分组</label>
                                <select class="form-select" id="group_id" name="group_id">
                                    <option value="">未分组</option>
                                    <?php foreach ($groups as $group): ?>
                                    <option value="<?= $group['id'] ?>" <?= ($channel['group_id'] == $group['id'] ? 'selected' : '') ?>>
                                        <?= htmlspecialchars($group['name']) ?>
                                    </option>
                                    <?php endforeach; ?>
                                </select>
                            </div>

                            <div class="text-end">
                                <button type="submit" class="btn btn-primary">保存修改</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
</body>
</html> 