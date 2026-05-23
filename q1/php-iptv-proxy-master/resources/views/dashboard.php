<!DOCTYPE html>
<html>
<head>
    <!-- 其他 head 内容 -->
    <link href="/css/dashboard.css" rel="stylesheet">
</head>
<body>
    <!-- 添加检查间隔的隐藏输入 -->
    <input type="hidden" id="check_interval" value="<?php echo $config->get('check_interval', 10); ?>">
    
    <!-- 总带宽卡片 -->
    <div class="col-md-2">
        <div class="card stats-card stats-bandwidth">
            <div class="card-body">
                <h5 class="card-title">总带宽</h5>
                <p class="card-text2" id="upload_bandwidth">上行 - MB/s</p>
                <p class="card-text2" id="download_bandwidth">下行 - MB/s</p>
                <i class="fas fa-network-wired stats-icon"></i>
            </div>
        </div>
    </div>
    
    <!-- 其他内容 -->
    
    <!-- 在页面底部添加 JavaScript -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="/js/dashboard.js"></script>
</body>
</html> 