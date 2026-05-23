<?php
require_once '../config/config.php';
require_once BASE_PATH.'/includes/auth_validate.php';

include BASE_PATH.'/includes/header.php';
?>
<div id="page-wrapper">
    <div class="row">
        <div class="col-lg-12">
            <h1 class="page-header">接口文档</h1>
            <p class="text-muted">广电视听内容运营平台 API 接口联调文档</p>
        </div>
    </div>

    <div class="row">
        <div class="col-lg-12">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <i class="fa fa-book fa-fw"></i> OpenAPI 接口文档
                </div>
                <div class="panel-body">
                    <p>完整的 API 接口文档可通过以下链接访问：</p>
                    <a href="/swagger/index.html" target="_blank" class="btn btn-primary">
                        <i class="fa fa-external-link"></i> 打开接口文档 (Swagger)
                    </a>
                    <a href="/swagger/openapi.yaml" target="_blank" class="btn btn-default">
                        <i class="fa fa-code"></i> 下载 OpenAPI 规范
                    </a>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-lg-12">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <i class="fa fa-info-circle fa-fw"></i> 接口概览
                </div>
                <div class="panel-body">
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>模块</th>
                                <th>前缀</th>
                                <th>说明</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td>系统信息</td><td><code>/api/v1/system</code></td><td>获取系统版本与环境信息</td></tr>
                            <tr><td>认证</td><td><code>/api/v1/auth</code></td><td>用户登录与认证</td></tr>
                            <tr><td>用户管理</td><td><code>/api/v1/users</code></td><td>用户CRUD操作</td></tr>
                            <tr><td>角色管理</td><td><code>/api/v1/roles</code></td><td>角色信息查询</td></tr>
                            <tr><td>频道栏目</td><td><code>/api/v1/channels</code></td><td>频道栏目管理</td></tr>
                            <tr><td>节目素材</td><td><code>/api/v1/materials</code></td><td>节目素材管理</td></tr>
                            <tr><td>EPG文件</td><td><code>/api/v1/epg</code></td><td>EPG电子节目单管理</td></tr>
                            <tr><td>发布任务</td><td><code>/api/v1/publish</code></td><td>内容发布任务管理</td></tr>
                            <tr><td>缓存管理</td><td><code>/api/v1/cache</code></td><td>缓存节点与刷新管理</td></tr>
                            <tr><td>模板导入</td><td><code>/api/v1/templates</code></td><td>发布模板导入</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
<?php include BASE_PATH.'/includes/footer.php'; ?>
