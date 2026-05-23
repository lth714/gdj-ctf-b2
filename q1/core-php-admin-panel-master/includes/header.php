<!DOCTYPE html>
<html lang="zh-CN">

    <head>

        <meta charset="utf-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="description" content="">
        <meta name="author" content="">

        <title>广电视听内容运营平台</title>

        <!-- Bootstrap Core CSS -->
        <link  rel="stylesheet" href="/assets/css/bootstrap.min.css"/>

        <!-- MetisMenu CSS -->
        <link href="/assets/js/metisMenu/metisMenu.min.css" rel="stylesheet">

        <!-- Custom CSS -->
        <link href="/assets/css/sb-admin-2.css" rel="stylesheet">
        <!-- Custom Fonts -->
        <link href="/assets/fonts/font-awesome/css/font-awesome.min.css" rel="stylesheet" type="text/css">

        <!-- HTML5 Shim and Respond.js IE8 support of HTML5 elements and media queries -->
        <!-- WARNING: Respond.js doesn't work if you view the page via file:// -->
        <!--[if lt IE 9]>
            <script src="https://oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>
            <script src="https://oss.maxcdn.com/libs/respond.js/1.4.2/respond.min.js"></script>
        <![endif]-->
        <script src="/assets/js/jquery.min.js" type="text/javascript"></script>

    </head>

    <body>

        <div id="wrapper">

            <!-- Navigation -->
            <?php if (isset($_SESSION['user_logged_in']) && $_SESSION['user_logged_in'] == true): ?>
                <nav class="navbar navbar-default navbar-static-top" role="navigation" style="margin-bottom: 0">
                    <div class="navbar-header">
                        <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-collapse">
                            <span class="sr-only">Toggle navigation</span>
                            <span class="icon-bar"></span>
                            <span class="icon-bar"></span>
                            <span class="icon-bar"></span>
                        </button>
                        <a class="navbar-brand" href="">广电视听内容运营平台</a>
                    </div>
                    <!-- /.navbar-header -->

                    <ul class="nav navbar-top-links navbar-right">
                        <li class="dropdown">
                            <a class="dropdown-toggle" data-toggle="dropdown" href="#">
                                <i class="fa fa-user fa-fw"></i> <?php echo htmlspecialchars($_SESSION['username'] ?? ''); ?> <i class="fa fa-caret-down"></i>
                            </a>
                            <ul class="dropdown-menu dropdown-user">
                                <li><a href="#"><i class="fa fa-user fa-fw"></i> 用户信息</a>
                                </li>
                                <li><a href="#"><i class="fa fa-gear fa-fw"></i> 系统设置</a>
                                </li>
                                <li class="divider"></li>
                                <li><a href="/logout.php"><i class="fa fa-sign-out fa-fw"></i> 安全退出</a>
                                </li>
                            </ul>
                            <!-- /.dropdown-user -->
                        </li>
                        <!-- /.dropdown -->
                    </ul>
                    <!-- /.navbar-top-links -->

                    <div class="navbar-default sidebar" role="navigation">
                        <div class="sidebar-nav navbar-collapse">
                            <ul class="nav" id="side-menu">
                                <li>
                                    <a href="/index.php"><i class="fa fa-dashboard fa-fw"></i> 控制台</a>
                                </li>

                                <li <?php echo (CURRENT_PAGE == "admin_users.php" || CURRENT_PAGE == "add_admin.php" || CURRENT_PAGE == "edit_admin.php") ? 'class="active"' : ''; ?>>
                                    <a href="#"><i class="fa fa-users fa-fw"></i> 用户管理<span class="fa arrow"></span></a>
                                    <ul class="nav nav-second-level">
                                        <li>
                                            <a href="/admin_users.php"><i class="fa fa-list fa-fw"></i>用户列表</a>
                                        </li>
                                        <li>
                                            <a href="/add_admin.php"><i class="fa fa-plus fa-fw"></i>添加用户</a>
                                        </li>
                                    </ul>
                                </li>

                                <li>
                                    <a href="/admin/role_management.php"><i class="fa fa-user-md fa-fw"></i> 角色管理</a>
                                </li>

                                <li <?php echo (CURRENT_PAGE == "admin/channel_management.php") ? 'class="active"' : ''; ?>>
                                    <a href="#"><i class="fa fa-television fa-fw"></i> 频道栏目管理<span class="fa arrow"></span></a>
                                    <ul class="nav nav-second-level">
                                        <li>
                                            <a href="/admin/channel_management.php"><i class="fa fa-list fa-fw"></i>频道列表</a>
                                        </li>
                                    </ul>
                                </li>

                                <li <?php echo (CURRENT_PAGE == "admin/material_management.php") ? 'class="active"' : ''; ?>>
                                    <a href="#"><i class="fa fa-film fa-fw"></i> 节目素材管理<span class="fa arrow"></span></a>
                                    <ul class="nav nav-second-level">
                                        <li>
                                            <a href="/admin/material_management.php"><i class="fa fa-list fa-fw"></i>素材列表</a>
                                        </li>
                                    </ul>
                                </li>

                                <li <?php echo (CURRENT_PAGE == "admin/epg_management.php") ? 'class="active"' : ''; ?>>
                                    <a href="#"><i class="fa fa-calendar fa-fw"></i> EPG文件管理<span class="fa arrow"></span></a>
                                    <ul class="nav nav-second-level">
                                        <li>
                                            <a href="/admin/epg_management.php"><i class="fa fa-list fa-fw"></i>EPG列表</a>
                                        </li>
                                    </ul>
                                </li>

                                <li <?php echo (CURRENT_PAGE == "admin/publish_task_management.php") ? 'class="active"' : ''; ?>>
                                    <a href="#"><i class="fa fa-cloud-upload fa-fw"></i> 发布任务管理<span class="fa arrow"></span></a>
                                    <ul class="nav nav-second-level">
                                        <li>
                                            <a href="/admin/publish_task_management.php"><i class="fa fa-list fa-fw"></i>任务列表</a>
                                        </li>
                                    </ul>
                                </li>

                                <li <?php echo (CURRENT_PAGE == "admin/cache_management.php") ? 'class="active"' : ''; ?>>
                                    <a href="#"><i class="fa fa-refresh fa-fw"></i> 缓存刷新管理<span class="fa arrow"></span></a>
                                    <ul class="nav nav-second-level">
                                        <li>
                                            <a href="/admin/cache_management.php"><i class="fa fa-list fa-fw"></i>缓存节点</a>
                                        </li>
                                    </ul>
                                </li>

                                <li>
                                    <a href="/admin/api_docs.php"><i class="fa fa-book fa-fw"></i> 接口文档</a>
                                </li>

                                <li>
                                    <a href="/admin/template_import.php"><i class="fa fa-file-archive-o fa-fw"></i> 发布模板导入</a>
                                </li>

                                <li>
                                    <a href="/admin/operation_logs.php"><i class="fa fa-history fa-fw"></i> 操作日志</a>
                                </li>
                            </ul>
                        </div>
                        <!-- /.sidebar-collapse -->
                    </div>
                    <!-- /.navbar-static-side -->
                </nav>
            <?php endif;?>
            <!-- The End of the Header -->