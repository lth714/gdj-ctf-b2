<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统安装 - 环境检查</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {
            background-color: #f5f8fa;
        }
        .install-container {
            max-width: 1000px;
            margin: 30px auto;
        }
        .check-item {
            margin-bottom: 15px;
            padding: 15px;
            border-radius: 8px;
            background-color: #fff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        .check-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .status-icon {
            font-size: 1.2em;
            margin-right: 10px;
            display: inline-block;
            width: 24px;
            text-align: center;
        }
        .status-passed { color: #10B981; }
        .status-failed { color: #EF4444; }
        .status-warning { color: #F59E0B; }
        .install-guide {
            margin-top: 8px;
            padding: 8px 12px;
            background-color: #F3F4F6;
            border-radius: 6px;
            font-size: 0.9em;
            color: #4B5563;
        }
        .step-indicator {
            display: flex;
            justify-content: center;
            margin-bottom: 30px;
        }
        .step {
            padding: 8px 20px;
            margin: 0 5px;
            background: #fff;
            border-radius: 20px;
            font-weight: 500;
            color: #6B7280;
            position: relative;
        }
        .step.active {
            background: #3B82F6;
            color: #fff;
        }
        .step.completed {
            background: #10B981;
            color: #fff;
        }
    </style>
</head>
<body>
    <div class="install-container">
        <!-- 步骤指示器 -->
        <div class="step-indicator">
            <div class="step active">
                <i class="bi bi-1-circle-fill"></i> 环境检查
            </div>
            <div class="step">
                <i class="bi bi-2-circle"></i> 数据库配置
            </div>
            <div class="step">
                <i class="bi bi-3-circle"></i> Redis配置
            </div>
            <div class="step">
                <i class="bi bi-4-circle"></i> 管理员设置
            </div>
            <div class="step">
                <i class="bi bi-5-circle"></i> 完成安装
            </div>
        </div>

        <div class="card">
            <div class="card-header bg-white py-3">
                <h3 class="card-title mb-0">系统环境检查</h3>
            </div>
            <div class="card-body">
                <!-- 总体状态 -->
                <div class="alert <?php echo $results['all_passed'] ? 'alert-success' : 'alert-danger'; ?> d-flex align-items-center" role="alert">
                    <i class="bi <?php echo $results['all_passed'] ? 'bi-check-circle-fill' : 'bi-exclamation-triangle-fill'; ?> me-2"></i>
                    <div>
                        <?php if ($results['all_passed']): ?>
                            恭喜！您的系统满足所有必需的运行条件
                        <?php else: ?>
                            您的系统不满足某些必需的运行条件，请查看详细信息并进行相应设置
                        <?php endif; ?>
                    </div>
                </div>

                <!-- PHP版本检查 -->
                <h4 class="mt-4 mb-3">PHP版本</h4>
                <div class="check-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="status-icon <?php echo $results['php']['passed'] ? 'status-passed' : 'status-failed'; ?>">
                                <i class="bi <?php echo $results['php']['passed'] ? 'bi-check-circle-fill' : 'bi-x-circle-fill'; ?>"></i>
                            </span>
                            <strong>PHP版本</strong>
                            <span class="text-muted ms-2"><?php echo $results['php']['description']; ?></span>
                        </div>
                        <div>
                            <span class="badge <?php echo $results['php']['passed'] ? 'bg-success' : 'bg-danger'; ?>">
                                当前版本: <?php echo $results['php']['current']; ?>
                                (需求: <?php echo $results['php']['required']; ?>)
                            </span>
                        </div>
                    </div>
                </div>

                <!-- PHP扩展检查 -->
                <h4 class="mt-4 mb-3">PHP扩展</h4>
                <?php foreach ($results['extensions']['items'] as $ext => $info): ?>
                <div class="check-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <span class="status-icon <?php echo $info['passed'] ? 'status-passed' : ($info['required'] ? 'status-failed' : 'status-warning'); ?>">
                                <i class="bi <?php echo $info['passed'] ? 'bi-check-circle-fill' : ($info['required'] ? 'bi-x-circle-fill' : 'bi-exclamation-circle-fill'); ?>"></i>
                            </span>
                            <strong><?php echo $ext; ?></strong>
                            <span class="text-muted ms-2"><?php echo $info['description']; ?></span>
                            <?php if (!$info['passed']): ?>
                            <div class="install-guide">
                                <i class="bi bi-terminal"></i>
                                <strong>安装方法：</strong> <?php echo $info['install_guide']; ?>
                            </div>
                            <?php endif; ?>
                        </div>
                        <div>
                            <span class="badge <?php echo $info['passed'] ? 'bg-success' : ($info['required'] ? 'bg-danger' : 'bg-warning'); ?>">
                                <?php echo $info['passed'] ? '已安装' : ($info['required'] ? '未安装' : '建议安装'); ?>
                            </span>
                        </div>
                    </div>
                </div>
                <?php endforeach; ?>

                <!-- 系统要求检查 -->
                <h4 class="mt-4 mb-3">系统要求</h4>
                <?php foreach ($results['system']['items'] as $item): ?>
                <div class="check-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <span class="status-icon <?php echo $item['passed'] ? 'status-passed' : 'status-failed'; ?>">
                                <i class="bi <?php echo $item['passed'] ? 'bi-check-circle-fill' : 'bi-x-circle-fill'; ?>"></i>
                            </span>
                            <strong><?php echo $item['name']; ?></strong>
                            <span class="text-muted ms-2"><?php echo $item['description']; ?></span>
                            <?php if (!$item['passed']): ?>
                            <div class="install-guide">
                                <i class="bi bi-gear"></i>
                                <strong>修改方法：</strong> <?php echo $item['install_guide']; ?>
                            </div>
                            <?php endif; ?>
                        </div>
                        <div>
                            <span class="badge <?php echo $item['passed'] ? 'bg-success' : 'bg-danger'; ?>">
                                当前值: <?php echo $item['current']; ?>
                                (建议: <?php echo $item['required']; ?>)
                            </span>
                        </div>
                    </div>
                </div>
                <?php endforeach; ?>
                <!-- 在系统要求检查后添加 -->
                <h4 class="mt-4 mb-3">配置文件检查</h4>
                <div class="check-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <span class="status-icon <?php echo ($results['config']['config_exists'] && $results['config']['config_writable']) ? 'status-passed' : 'status-failed'; ?>">
                                <i class="bi <?php echo ($results['config']['config_exists'] && $results['config']['config_writable']) ? 'bi-check-circle-fill' : 'bi-x-circle-fill'; ?>"></i>
                            </span>
                            <strong>配置文件</strong>
                            <span class="text-muted ms-2">检查配置文件状态</span>
                            <?php if ($results['config']['error']): ?>
                            <div class="install-guide text-danger">
                                <i class="bi bi-exclamation-triangle"></i>
                                <strong>错误：</strong> <?php echo $results['config']['error']; ?>
                            </div>
                            <?php endif; ?>
                            
                            <div class="mt-2">
                                <ul class="list-unstyled">
                                    <li>
                                        <i class="bi <?php echo $results['config']['template_exists'] ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'; ?>"></i>
                                        配置模板文件: <?php echo $results['config']['template_exists'] ? '存在' : '不存在'; ?>
                                    </li>
                                    <li>
                                        <i class="bi <?php echo $results['config']['config_exists'] ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'; ?>"></i>
                                        配置文件: <?php echo $results['config']['config_exists'] ? '已创建' : '未创建'; ?>
                                    </li>
                                    <li>
                                        <i class="bi <?php echo $results['config']['config_writable'] ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'; ?>"></i>
                                        配置文件权限: <?php echo $results['config']['config_writable'] ? '可写' : '不可写'; ?>
                                    </li>
                                    <?php if ($results['config']['created']): ?>
                                    <li>
                                        <i class="bi bi-info-circle-fill text-info"></i>
                                        配置文件已从模板自动创建
                                    </li>
                                    <?php endif; ?>
                                </ul>
                            </div>
                        </div>
                        <div>
                            <span class="badge <?php echo ($results['config']['config_exists'] && $results['config']['config_writable']) ? 'bg-success' : 'bg-danger'; ?>">
                                <?php echo ($results['config']['config_exists'] && $results['config']['config_writable']) ? '正常' : '需要处理'; ?>
                            </span>
                        </div>
                    </div>
                </div>
                <!-- 操作按钮 -->
                <div class="mt-4 text-center">
                    <button type="button" class="btn btn-primary me-2" onclick="window.location.reload()">
                        <i class="bi bi-arrow-clockwise"></i> 重新检查
                    </button>
                    <?php if ($results['all_passed']): ?>
                    <a href="?step=2" class="btn btn-success">
                        <i class="bi bi-arrow-right"></i> 下一步
                    </a>
                    <?php else: ?>
                    <button type="button" class="btn btn-secondary" disabled>
                        <i class="bi bi-arrow-right"></i> 下一步
                    </button>
                    <?php endif; ?>
                </div>
            </div>
        </div>
    </div>

    <script src="/css/bootstrap.bundle.min.js"></script>
</body>
</html>