<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $pageTitle ?? 'IPTV 系统安装'; ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {
            background-color: #f8f9fa;
        }
        .install-container {
            max-width: 1000px;
            margin: 30px auto;
        }
        .step-indicator {
            margin-bottom: 30px;
        }
        .step-indicator .step {
            padding: 10px 20px;
            background: #fff;
            border-radius: 4px;
            margin: 0 5px;
            position: relative;
        }
        .step-indicator .step.active {
            background: #0d6efd;
            color: #fff;
        }
        .step-indicator .step.completed {
            background: #198754;
            color: #fff;
        }
        .install-footer {
            margin-top: 30px;
            text-align: center;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="install-container">
        <!-- 步骤指示器 -->
        <div class="step-indicator d-flex justify-content-center mb-4">
            <?php for ($i = 1; $i <= 4; $i++): ?>
            <div class="step <?php 
                echo $currentStep === $i ? 'active' : 
                    ($currentStep > $i ? 'completed' : ''); 
            ?>">
                <i class="bi <?php 
                    echo $currentStep > $i ? 'bi-check-circle-fill' : 
                        'bi-circle-fill'; 
                ?>"></i>
                步骤 <?php echo $i; ?>
            </div>
            <?php endfor; ?>
        </div>

        <!-- 主要内容区域 -->
        <div class="content">
            <?php include $contentTemplate; ?>
        </div>

        <!-- 页脚 -->
        <div class="install-footer">
            <p>IPTV System &copy; <?php echo date('Y'); ?></p>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <?php if (isset($pageScripts)): ?>
    <?php foreach ($pageScripts as $script): ?>
    <script src="<?php echo $script; ?>"></script>
    <?php endforeach; ?>
    <?php endif; ?>
</body>
</html>