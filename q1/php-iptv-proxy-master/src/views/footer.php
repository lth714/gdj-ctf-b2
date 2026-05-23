<?php
/**
 * 通用页脚模板
 */
?>
<footer class="footer mt-auto py-3 bg-light border-top">
    <div class="container text-center">
        <div class="row align-items-center">
            <div class="col">
                <span class="text-muted">
                    <span class="me-3">版本：<strong>0.0.1</strong></span>
                    <span class="me-3">|</span>
                    <span class="me-3">五月天版权所有 &copy; <?php echo date('Y'); ?></span>
                    <span class="me-3">|</span>
                    <a href="https://github.com/wyt990/php-iptv-proxy" target="_blank" class="text-decoration-none">
                        <i class="fab fa-github"></i> GitHub
                    </a>
                </span>
            </div>
        </div>
    </div>
</footer>

<!-- 确保页脚始终在底部的CSS -->
<style>
html, body {
    height: 100%;
}
body {
    display: flex;
    flex-direction: column;
}
.content-wrapper {
    flex: 1 0 auto;
}
.footer {
    flex-shrink: 0;
    background-color: #f8f9fa !important;
    border-top: 1px solid #dee2e6;
}
</style> 