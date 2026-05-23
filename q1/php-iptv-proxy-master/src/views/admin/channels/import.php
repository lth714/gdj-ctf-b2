<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>导入频道 - IPTV 代理系统</title>
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="/css/all.min.css" rel="stylesheet">
    <style>
        .import-option {
            display: none;
        }
        .import-option.active {
            display: block;
        }
    </style>
</head>
<body>
    <?php $currentPage = 'import'; ?>
    <?php require __DIR__ . '/../../navbar.php'; ?>

    <div class="container mt-4">
        <h2>导入频道</h2>
        
        <?php if (isset($_SESSION['flash_message'])): ?>
            <div class="alert alert-<?= $_SESSION['flash_message']['type'] ?> alert-dismissible fade show" role="alert">
                <?= $_SESSION['flash_message']['message'] ?>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
            <?php unset($_SESSION['flash_message']); ?>
        <?php endif; ?>
        
        <div class="card">
            <div class="card-header">
                <ul class="nav nav-tabs card-header-tabs" id="importTabs">
                    <li class="nav-item">
                        <a class="nav-link active" href="#" data-type="file">
                            <i class="fas fa-file-upload"></i> 上传文件
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" data-type="url">
                            <i class="fas fa-link"></i> 在线导入
                        </a>
                    </li>
                </ul>
            </div>
            <div class="card-body">
                <form action="/admin/channels/import" method="post" enctype="multipart/form-data" id="importForm">
                    <input type="hidden" name="import_type" id="importType" value="file">
                    
                    <!-- 文件上传选项 -->
                    <div class="import-option active" id="fileOption">
                        <div class="mb-3">
                            <label for="file" class="form-label">选择文件</label>
                            <input type="file" class="form-control" id="file" name="file" accept=".txt,.m3u,.m3u8">
                            <div class="form-text">支持的文件格式：TXT, M3U, M3U8</div>
                        </div>
                    </div>

                    <!-- 在线导入选项 -->
                    <div class="import-option" id="urlOption">
                        <div class="mb-3">
                            <label for="url" class="form-label">在线文件地址</label>
                            <input type="url" class="form-control" id="url" name="url" placeholder="请输入频道列表文件的URL">
                            <div class="form-text">支持 TXT, M3U, M3U8 格式的在线文件</div>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-file-import"></i> 开始导入
                    </button>
                </form>
            </div>
        </div>

        <div class="card mt-4">
            <div class="card-header bg-light">
                <h5 class="card-title mb-0">
                    <i class="fas fa-info-circle"></i> 导入说明
                </h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6><i class="fas fa-file-alt"></i> TXT 文件格式要求：</h6>
                        <pre class="bg-light p-3 rounded">分组名称,#genre#
频道名称,频道地址
频道名称,频道地址</pre>
                    </div>
                    <div class="col-md-6">
                        <h6><i class="fas fa-file-code"></i> M3U/M3U8 文件格式要求：</h6>
                        <pre class="bg-light p-3 rounded">#EXTM3U
#EXTINF:-1 group-title="分组名称",频道名称
频道地址
#EXTINF:-1 group-title="分组名称",频道名称
频道地址</pre>
                    </div>
                </div>
            </div>
        </div>
    </div>
	<?php require __DIR__ . '/../../footer.php'; ?>
    <script src="/css/bootstrap.bundle.min.js"></script>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const importTabs = document.getElementById('importTabs');
        const importType = document.getElementById('importType');
        const fileOption = document.getElementById('fileOption');
        const urlOption = document.getElementById('urlOption');
        const fileInput = document.getElementById('file');
        const urlInput = document.getElementById('url');
        const form = document.getElementById('importForm');

        // 只监听导入选项卡的点击事件
        importTabs.addEventListener('click', function(e) {
            // 确保点击的是选项卡链接
            if (e.target.classList.contains('nav-link')) {
                e.preventDefault();
                
                // 更新导航标签状态
                importTabs.querySelectorAll('.nav-link').forEach(link => {
                    link.classList.remove('active');
                });
                e.target.classList.add('active');
                
                // 更新表单显示
                const type = e.target.dataset.type;
                importType.value = type;
                
                if (type === 'file') {
                    fileOption.classList.add('active');
                    urlOption.classList.remove('active');
                    fileInput.required = true;
                    urlInput.required = false;
                } else {
                    urlOption.classList.add('active');
                    fileOption.classList.remove('active');
                    urlInput.required = true;
                    fileInput.required = false;
                }
            }
        });

        // 表单提交验证
        form.addEventListener('submit', function(e) {
            const type = importType.value;
            if (type === 'file' && !fileInput.value) {
                e.preventDefault();
                alert('请选择要导入的文件');
            } else if (type === 'url' && !urlInput.value) {
                e.preventDefault();
                alert('请输入在线文件地址');
            }
        });

        // 自动隐藏提示信息
        const alert = document.querySelector('.alert');
        if (alert) {
            setTimeout(() => {
                const closeButton = alert.querySelector('.btn-close');
                if (closeButton) {
                    closeButton.click();
                }
            }, 5000); // 5秒后自动关闭
        }
    });
    </script>
</body>
</html> 