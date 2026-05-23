<?php $currentPage = 'diag'; ?>
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>网络诊断 - IPTV 代理系统</title>
    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="/css/all.min.css" rel="stylesheet">
    <style>
        .terminal-output {
            background: #1a1a2e;
            color: #00ff88;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            padding: 16px;
            border-radius: 6px;
            min-height: 200px;
            max-height: 500px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .terminal-output .cmd-line {
            color: #ffcc00;
        }
        .terminal-output .error {
            color: #ff4444;
        }
    </style>
</head>
<body>
    <?php require __DIR__ . '/../../navbar.php'; ?>

    <div class="container-fluid mx-auto" style="width: 98%;">
        <div class="row">
            <div class="col-md-12">
                <h2>网络诊断</h2>
                <p class="text-muted">检测 IPTV 源站网络连通性及延迟</p>

                <div class="row">
                    <div class="col-md-5">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0"><i class="fas fa-network-wired me-2"></i>诊断参数</h5>
                            </div>
                            <div class="card-body">
                                <form id="diagForm">
                                    <div class="mb-3">
                                        <label for="target" class="form-label">目标地址</label>
                                        <input type="text" class="form-control" id="target" name="target"
                                               placeholder="例如: 8.8.8.8 或 iptv-source.example.com"
                                               required>
                                        <div class="form-text">输入 IP 地址或域名，系统将执行 ping 连通性检测。</div>
                                    </div>
                                    <div class="d-grid">
                                        <button type="submit" class="btn btn-primary" id="submitBtn">
                                            <i class="fas fa-paper-plane me-1"></i>开始检测
                                        </button>
                                    </div>
                                </form>
                                <div class="mt-3">
                                    <small class="text-muted">
                                        <i class="fas fa-info-circle me-1"></i>
                                        常用检测目标：CDN节点、源站服务器、上游代理
                                    </small>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-7">
                        <div class="card">
                            <div class="card-header d-flex justify-content-between align-items-center">
                                <h5 class="card-title mb-0"><i class="fas fa-terminal me-2"></i>执行结果</h5>
                                <button class="btn btn-sm btn-outline-secondary" id="clearBtn" type="button">
                                    <i class="fas fa-eraser me-1"></i>清空
                                </button>
                            </div>
                            <div class="card-body">
                                <div class="terminal-output" id="output">
                                    <span class="text-muted">等待执行诊断命令...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <?php require __DIR__ . '/../../footer.php'; ?>
    <script src="/css/bootstrap.bundle.min.js" defer></script>
    <script>
    document.getElementById('diagForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        var submitBtn = document.getElementById('submitBtn');
        var output = document.getElementById('output');
        var target = document.getElementById('target').value.trim();

        if (!target) return;

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>检测中...';
        output.innerHTML = '<span class="cmd-line">$ ping -c 3 ' + target + '</span>\n执行中...';

        try {
            var formData = new FormData();
            formData.append('target', target);

            var resp = await fetch('/admin/diag/execute', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            var result = await resp.json();

            if (result.success) {
                output.innerHTML = '<span class="cmd-line">$ ' + result.command + '</span>\n' + result.output;
            } else {
                output.innerHTML = '<span class="cmd-line">$ ping -c 3 ' + target + '</span>\n<span class="error">[错误] ' + (result.error || '未知错误') + '</span>';
            }
        } catch (err) {
            output.innerHTML = '<span class="cmd-line">$ ping -c 3 ' + target + '</span>\n<span class="error">[错误] 请求失败: ' + err.message + '</span>';
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-paper-plane me-1"></i>开始检测';
        }
    });

    document.getElementById('clearBtn').addEventListener('click', function() {
        document.getElementById('output').innerHTML = '<span class="text-muted">等待执行诊断命令...</span>';
    });
    </script>
</body>
</html>
