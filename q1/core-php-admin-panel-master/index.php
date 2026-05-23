<?php
require_once './config/config.php';
require_once 'includes/auth_validate.php';

//Get DB instance. function is defined in config.php
$db = getDbInstance();

//Get Dashboard information
$todayPublishTasks = $db->rawQuery("SELECT COUNT(*) as cnt FROM publish_tasks WHERE DATE(created_at) = CURDATE()");
$pendingMaterials = $db->rawQuery("SELECT COUNT(*) as cnt FROM materials WHERE status = 'pending'");
$cacheRefreshCount = $db->rawQuery("SELECT COUNT(*) as cnt FROM operation_logs WHERE action = 'cache_refresh' AND DATE(created_at) = CURDATE()");
$onlineCacheNodes = $db->rawQuery("SELECT COUNT(*) as cnt FROM cache_nodes WHERE status = 'online'");
$totalCacheNodes = $db->rawQuery("SELECT COUNT(*) as cnt FROM cache_nodes");
$apiCallCount = $db->rawQuery("SELECT COUNT(*) as cnt FROM operation_logs WHERE action = 'api_call' AND DATE(created_at) = CURDATE()");
$recentLogs = $db->rawQuery("SELECT * FROM operation_logs ORDER BY created_at DESC LIMIT 5");

$numTodayPublish = $todayPublishTasks[0]['cnt'] ?? 0;
$numPendingMaterials = $pendingMaterials[0]['cnt'] ?? 0;
$numCacheRefresh = $cacheRefreshCount[0]['cnt'] ?? 0;
$numOnlineNodes = $onlineCacheNodes[0]['cnt'] ?? 0;
$numTotalNodes = $totalCacheNodes[0]['cnt'] ?? 0;
$numApiCalls = $apiCallCount[0]['cnt'] ?? 0;

include_once('includes/header.php');
?>
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-12">
            <h1 class="page-header">控制台</h1>
        </div>
        <!-- /.col-lg-12 -->
    </div>
    <!-- /.row -->
    <div class="row">
        <div class="col-lg-3 col-md-6">
            <div class="panel panel-primary">
                <div class="panel-heading">
                    <div class="row">
                        <div class="col-xs-3">
                            <i class="fa fa-cloud-upload fa-5x"></i>
                        </div>
                        <div class="col-xs-9 text-right">
                            <div class="huge"><?php echo $numTodayPublish; ?></div>
                            <div>今日发布任务</div>
                        </div>
                    </div>
                </div>
                <a href="admin/publish_task_management.php">
                    <div class="panel-footer">
                        <span class="pull-left">查看详情</span>
                        <span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span>
                        <div class="clearfix"></div>
                    </div>
                </a>
            </div>
        </div>
        <div class="col-lg-3 col-md-6">
            <div class="panel panel-yellow">
                <div class="panel-heading">
                    <div class="row">
                        <div class="col-xs-3">
                            <i class="fa fa-film fa-5x"></i>
                        </div>
                        <div class="col-xs-9 text-right">
                            <div class="huge"><?php echo $numPendingMaterials; ?></div>
                            <div>待审核节目素材</div>
                        </div>
                    </div>
                </div>
                <a href="admin/material_management.php">
                    <div class="panel-footer">
                        <span class="pull-left">查看详情</span>
                        <span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span>
                        <div class="clearfix"></div>
                    </div>
                </a>
            </div>
        </div>
        <div class="col-lg-3 col-md-6">
            <div class="panel panel-green">
                <div class="panel-heading">
                    <div class="row">
                        <div class="col-xs-3">
                            <i class="fa fa-refresh fa-5x"></i>
                        </div>
                        <div class="col-xs-9 text-right">
                            <div class="huge"><?php echo $numCacheRefresh; ?></div>
                            <div>缓存刷新次数</div>
                        </div>
                    </div>
                </div>
                <a href="admin/cache_management.php">
                    <div class="panel-footer">
                        <span class="pull-left">查看详情</span>
                        <span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span>
                        <div class="clearfix"></div>
                    </div>
                </a>
            </div>
        </div>
        <div class="col-lg-3 col-md-6">
            <div class="panel panel-info">
                <div class="panel-heading">
                    <div class="row">
                        <div class="col-xs-3">
                            <i class="fa fa-server fa-5x"></i>
                        </div>
                        <div class="col-xs-9 text-right">
                            <div class="huge"><?php echo $numOnlineNodes; ?>/<?php echo $numTotalNodes; ?></div>
                            <div>内网缓存节点状态</div>
                        </div>
                    </div>
                </div>
                <a href="admin/cache_management.php">
                    <div class="panel-footer">
                        <span class="pull-left">查看详情</span>
                        <span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span>
                        <div class="clearfix"></div>
                    </div>
                </a>
            </div>
        </div>
    </div>
    <!-- /.row -->
    <div class="row">
        <div class="col-lg-3 col-md-6">
            <div class="panel panel-red">
                <div class="panel-heading">
                    <div class="row">
                        <div class="col-xs-3">
                            <i class="fa fa-line-chart fa-5x"></i>
                        </div>
                        <div class="col-xs-9 text-right">
                            <div class="huge"><?php echo $numApiCalls; ?></div>
                            <div>接口调用次数</div>
                        </div>
                    </div>
                </div>
                <a href="admin/operation_logs.php">
                    <div class="panel-footer">
                        <span class="pull-left">查看详情</span>
                        <span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span>
                        <div class="clearfix"></div>
                    </div>
                </a>
            </div>
        </div>
        <div class="col-lg-9 col-md-6">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <i class="fa fa-history fa-fw"></i> 最近操作日志
                </div>
                <div class="panel-body">
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>操作用户</th>
                                    <th>操作类型</th>
                                    <th>IP地址</th>
                                    <th>操作时间</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php foreach ($recentLogs as $log): ?>
                                <tr>
                                    <td><?php echo htmlspecialchars($log['username']); ?></td>
                                    <td><?php echo htmlspecialchars($log['action']); ?></td>
                                    <td><?php echo htmlspecialchars($log['ip']); ?></td>
                                    <td><?php echo htmlspecialchars($log['created_at']); ?></td>
                                </tr>
                                <?php endforeach; ?>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <!-- /.row -->
</div>
<!-- /#page-wrapper -->

<?php include_once('includes/footer.php'); ?>
