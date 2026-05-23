                    <div class="mb-3">
                        <label for="monitor_refresh_interval" class="form-label">监控刷新时间（秒）</label>
                        <input type="number" class="form-control" id="monitor_refresh_interval" name="monitor_refresh_interval" value="<?= $settings['monitor_refresh_interval'] ?? 5 ?>" min="1">
                    </div>

                    <div class="mb-3">
                        <label for="max_error_count" class="form-label">最大异常次数</label>
                        <input type="number" class="form-control" id="max_error_count" name="max_error_count" value="<?= $settings['max_error_count'] ?? 3 ?>" min="1">
                        <div class="form-text">当频道检查异常次数达到此值时，将自动删除该频道</div>
                    </div>

                    <!-- 代理服务器设置 -->
                    <div class="card mb-4">
                        <div class="card-header">
                            <h5 class="mb-0">代理服务器设置</h5>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <label class="form-label">监听地址</label>
                                <input type="text" class="form-control" name="proxy_host" value="<?= htmlspecialchars($settings['proxy_host'] ?? '0.0.0.0') ?>">
                                <small class="text-muted">默认 0.0.0.0 表示监听所有网卡</small>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">监听端口</label>
                                <input type="number" class="form-control" name="proxy_port" value="<?= intval($settings['proxy_port'] ?? 8081) ?>">
                                <small class="text-muted">建议使用大于 1024 的端口</small>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">连接超时时间（秒）</label>
                                <input type="number" class="form-control" name="proxy_timeout" value="<?= intval($settings['proxy_timeout'] ?? 10) ?>">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">缓冲区大小（字节）</label>
                                <input type="number" class="form-control" name="proxy_buffer_size" value="<?= intval($settings['proxy_buffer_size'] ?? 8192) ?>">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">服务状态检查间隔（秒）</label>
                                <input type="number" class="form-control" name="status_check_interval" value="<?= intval($settings['status_check_interval'] ?? 10) ?>" min="1" max="60">
                                <small class="text-muted">设置检查代理服务状态的时间间隔，建议设置在 1-60 秒之间</small>
                            </div>
                        </div>
                    </div>

                    <div class="mb-3">