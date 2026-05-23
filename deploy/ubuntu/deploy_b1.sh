#!/bin/bash
# ============================================================
# VM-B1 (DMZ) 一键部署 — php-iptv-proxy 广电IPTV代理系统
# 用法: sudo bash deploy_b1.sh
# 前提: 已从 Git clone 项目到本地，在项目根目录执行
#       Ubuntu 22.04, 可连接互联网
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
IPTV_SRC="$PROJECT_ROOT/q1/php-iptv-proxy-master"

echo "============================================"
echo " Scenario B — B1 (DMZ) 一键部署"
echo " php-iptv-proxy + MySQL + Redis + Nginx"
echo "============================================"

if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] 请用 sudo 运行: sudo bash $0"
    exit 1
fi

if [ ! -d "$IPTV_SRC" ]; then
    echo "[ERROR] 找不到 php-iptv-proxy 源码目录: $IPTV_SRC"
    echo "        请确保在项目根目录执行此脚本"
    exit 1
fi

# ============ 1. 系统更新 ============
echo "[1/10] 更新系统..."
apt update && apt upgrade -y

# ============ 2. 安装软件包 ============
echo "[2/10] 安装 LEMP + Redis..."
DEBIAN_FRONTEND=noninteractive apt install -y \
    nginx \
    php8.1 php8.1-fpm php8.1-mysql php8.1-mbstring \
    php8.1-xml php8.1-curl php8.1-gd php8.1-zip \
    php8.1-redis \
    mysql-server mysql-client \
    redis-server \
    curl wget netcat-openbsd nmap vim openssh-server unzip \
    composer 2>/dev/null || true

# ============ 3. MySQL ============
echo "[3/10] 配置 MySQL 数据库..."
systemctl enable mysql --now

mysql -u root << 'SQLEOF'
CREATE DATABASE IF NOT EXISTS iptv_proxy CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER IF NOT EXISTS 'iptvadmin'@'localhost' IDENTIFIED BY 'Iptv@Proxy#2024';
GRANT ALL PRIVILEGES ON iptv_proxy.* TO 'iptvadmin'@'localhost';
FLUSH PRIVILEGES;
SQLEOF

# 导入数据库结构
if [ -f "$IPTV_SRC/src/Install/database.sql" ]; then
    mysql -u root iptv_proxy < "$IPTV_SRC/src/Install/database.sql"
    echo "   [OK] 数据库结构导入完成"
else
    echo "   [WARN] 找不到 database.sql, 跳过"
fi

# 创建 admin 用户
ADMIN_PASS=$(php -r "echo password_hash('admin123', PASSWORD_DEFAULT);")
mysql -u root iptv_proxy << SQLEOF
INSERT INTO admins (username, password, description) VALUES ('admin', '${ADMIN_PASS}', '系统管理员')
ON DUPLICATE KEY UPDATE password = VALUES(password);
SQLEOF
echo "   [OK] 管理员 admin/admin123 已创建"

# ============ 4. Redis ============
echo "[4/10] 配置 Redis..."
sed -i 's/^bind 127.0.0.1 -::1/bind 127.0.0.1/' /etc/redis/redis.conf
systemctl enable redis-server --now

# ============ 5. 部署 php-iptv-proxy ============
echo "[5/10] 部署 php-iptv-proxy 到 /opt/iptv-proxy..."
rm -rf /opt/iptv-proxy
cp -r "$IPTV_SRC" /opt/iptv-proxy

# 生成数据库配置
mkdir -p /opt/iptv-proxy/config
cat > /opt/iptv-proxy/config/config.php << 'CONFEOF'
<?php
return [
    'db' => [
        'host' => '127.0.0.1',
        'port' => 3306,
        'dbname' => 'iptv_proxy',
        'username' => 'iptvadmin',
        'password' => 'Iptv@Proxy#2024',
        'charset' => 'utf8mb4',
    ],
    'redis' => [
        'host' => '127.0.0.1',
        'port' => 6379,
        'password' => '',
    ],
    'app' => [
        'debug' => false,
        'site_name' => 'IPTV代理系统',
    ],
];
CONFEOF

# 安装 Composer 依赖
if [ -f /opt/iptv-proxy/composer.json ]; then
    cd /opt/iptv-proxy
    if command -v composer &>/dev/null; then
        composer install --no-dev --optimize-autoloader 2>&1 | tail -3
    else
        php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
        php composer-setup.php --quiet
        rm composer-setup.php
        php composer.phar install --no-dev --optimize-autoloader 2>&1 | tail -3
    fi
    echo "   [OK] Composer 依赖安装完成"
fi

# 权限设置
chown -R www-data:www-data /opt/iptv-proxy
chmod -R 755 /opt/iptv-proxy
mkdir -p /opt/iptv-proxy/storage/logs /opt/iptv-proxy/storage/cache
chmod -R 777 /opt/iptv-proxy/storage

# ============ 6. PHP-FPM ============
echo "[6/10] 配置 PHP-FPM..."
sed -i 's/^user = www-data/user = www-data/' /etc/php/8.1/fpm/pool.d/www.conf
sed -i 's/^group = www-data/group = www-data/' /etc/php/8.1/fpm/pool.d/www.conf
systemctl enable php8.1-fpm --now

# ============ 7. Nginx ============
echo "[7/10] 配置 Nginx..."
cat > /etc/nginx/sites-available/iptv-proxy << 'NGXEOF'
server {
    listen 80 default_server;
    server_name _;
    root /opt/iptv-proxy/public;
    index index.php index.html;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
    }

    location ~ /\. {
        deny all;
    }
}
NGXEOF

ln -sf /etc/nginx/sites-available/iptv-proxy /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/default.old 2>/dev/null || true
nginx -t && systemctl restart nginx
systemctl enable nginx

# ============ 8. sudo tee 提权向量 (B-7) ============
echo "[8/10] 配置提权向量..."
cat > /etc/sudoers.d/www-data-tee << 'SUDOEOF'
www-data ALL=(root) NOPASSWD: /usr/bin/tee
SUDOEOF
chmod 440 /etc/sudoers.d/www-data-tee

# ============ 9. 环境信息 ============
echo "[9/10] 创建运维提示文件..."
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
usermod -aG sudo operator 2>/dev/null || true

mkdir -p /opt/ops
cat > /opt/ops/deploy_note.txt << 'OPSEOF'
===== 广电监控系统部署备忘 =====
日期: 2024-03-15
部署人: 运维工程师

服务部署架构:
  - 前端代理 (本机): IPTV代理系统, Nginx :80
  - 内网监控 (192.168.110.2): Zabbix 监控平台, http端口

运维注意事项:
  1. IPTV频道源定期导入，模板见 /opt/iptv-proxy/storage/
  2. 内网Zabbix监控所有播出节点状态
  3. 网络诊断功能限管理员使用，检测上游CDN及源站连通性

内网访问:
  Zabbix: http://192.168.110.2/
  SSH运维: operator / 0p3rat0r@GDJ
OPSEOF
chmod 644 /opt/ops/deploy_note.txt

# ============ 10. 收尾 ============
echo "[10/10] 清理..."
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true
rm -rf /tmp/*
history -c

echo ""
echo "============================================"
echo "  [OK] B1 (DMZ) 部署完成!"
echo "============================================"
echo "  Web:      http://<本机IP>/"
echo "  Login:    admin / admin123"
echo "  Operator: operator / 0p3rat0r@GDJ"
echo "============================================"
echo ""
echo "攻击链 (B1):"
echo "  B-1: 密码重置绕过   /reset-password"
echo "  B-2: 命令注入       /admin/diag"
echo "  B-3: B1 MySQL 凭据  mysql -u iptvadmin"
echo "  B-7: sudo tee 提权"
