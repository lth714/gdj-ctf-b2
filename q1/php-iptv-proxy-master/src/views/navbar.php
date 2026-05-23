<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
    <div class="container-fluid">
        <a class="navbar-brand" href="/">
            <i class="fas fa-tv me-2"></i>IPTV 代理系统
        </a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav me-auto">
				<li class="nav-item">
                    <a class="nav-link <?= $currentPage === 'home' ? 'active' : '' ?>" href="/">
                        <i class="fas fa-house-user me-1"></i>首页
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link <?= $currentPage === 'channels' ? 'active' : '' ?>" href="/admin/channels">
                        <i class="fas fa-list me-1"></i>频道管理
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link <?= $currentPage === 'import' ? 'active' : '' ?>" href="/admin/channels/import">
                        <i class="fas fa-file-import me-1"></i>导入频道
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link <?= $currentPage === 'monitor' ? 'active' : '' ?>" href="/admin/monitor">
                        <i class="fas fa-chart-line me-1"></i>系统监控
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link <?= $currentPage === 'diag' ? 'active' : '' ?>" href="/admin/diag">
                        <i class="fas fa-stethoscope me-1"></i>网络诊断
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link <?= $currentPage === 'logs' ? 'active' : '' ?>" href="/admin/logs">
                        <i class="fas fa-history me-1"></i>操作日志
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link <?= $currentPage === 'error_logs' ? 'active' : '' ?>" href="/admin/error-logs">
                        <i class="fas fa-exclamation-triangle me-1"></i>错误日志
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link <?= $currentPage === 'settings' ? 'active' : '' ?>" href="/admin/settings">
                        <i class="fas fa-cog me-1"></i>系统设置
                    </a>
                </li>
            </ul>
            <ul class="navbar-nav">
                <li class="nav-item">
                    <a class="nav-link" href="/auth/logout.php">
                        <i class="fas fa-sign-out-alt me-1"></i>退出登录
                    </a>
                </li>
            </ul>
        </div>
    </div>
</nav> 