// 更新总带宽显示
function updateBandwidth() {
    fetch('/admin/proxy/bandwidth-stats')
        .then(response => response.json())
        .then(response => {
            if (response.success && response.data.total) {
                const total = response.data.total;
                document.getElementById('upload_bandwidth').textContent = '上行 ' + total.bandwidth.upload;
                document.getElementById('download_bandwidth').textContent = '下行 ' + total.bandwidth.download;
                
                // 如果有活跃流量，添加高亮效果
                const bandwidthCard = document.querySelector('.stats-bandwidth');
                if (total.channels_with_traffic > 0) {
                    bandwidthCard.classList.add('active');
                } else {
                    bandwidthCard.classList.remove('active');
                }
            }
        })
        .catch(error => {
            console.error('获取带宽数据失败:', error);
            document.getElementById('upload_bandwidth').textContent = '上行 - MB/s';
            document.getElementById('download_bandwidth').textContent = '下行 - MB/s';
            document.querySelector('.stats-bandwidth').classList.remove('active');
        });
}