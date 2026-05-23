#!/bin/bash
# VM-B1 (DMZ) Setup Script — IPTV代理系统 (php-iptv-proxy)
# CTF Scenario B — 广电网络监控
# Run as root on Ubuntu 22.04

set -e

echo "=== VM-B1 (DMZ) Setup: IPTV代理系统 ==="

echo "[+] Updating system..."
apt update && apt upgrade -y

echo "[+] Installing packages (LEMP + Redis)..."
DEBIAN_FRONTEND=noninteractive apt install -y \
    nginx \
    php8.1 php8.1-fpm php8.1-mysql php8.1-mbstring \
    php8.1-xml php8.1-curl php8.1-gd php8.1-zip \
    php8.1-redis \
    mysql-server-8.0 mysql-client-8.0 \
    redis-server \
    curl wget netcat-openbsd nmap vim openssh-server unzip

echo "[+] Configuring MySQL..."
systemctl enable mysql --now

# Create database and application user
mysql -u root << 'SQLEOF'
CREATE DATABASE IF NOT EXISTS iptv_proxy CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER IF NOT EXISTS 'iptvadmin'@'localhost' IDENTIFIED BY 'Iptv@Proxy#2024';
GRANT ALL PRIVILEGES ON iptv_proxy.* TO 'iptvadmin'@'localhost';
FLUSH PRIVILEGES;
SQLEOF

echo "[+] Importing database schema..."
if [ -f /opt/deploy/files/iptv-proxy/src/Install/database.sql ]; then
    mysql -u root iptv_proxy < /opt/deploy/files/iptv-proxy/src/Install/database.sql
fi

echo "[+] Creating admin user (admin / admin123)..."
ADMIN_PASS=$(php -r "echo password_hash('admin123', PASSWORD_DEFAULT);")
mysql -u root iptv_proxy << SQLEOF
INSERT INTO admins (username, password, description) VALUES ('admin', '${ADMIN_PASS}', '系统管理员')
ON DUPLICATE KEY UPDATE password = VALUES(password);
SQLEOF

echo "[+] Configuring Redis..."
sed -i 's/^bind 127.0.0.1 -::1/bind 127.0.0.1/' /etc/redis/redis.conf
systemctl enable redis-server --now

echo "[+] Deploying php-iptv-proxy..."
mkdir -p /opt/iptv-proxy
if [ -d /opt/deploy/files/iptv-proxy ]; then
    cp -r /opt/deploy/files/iptv-proxy/* /opt/iptv-proxy/
else
    echo "[!] Source files not found at /opt/deploy/files/iptv-proxy"
    echo "[!] Please copy php-iptv-proxy source to /opt/deploy/files/iptv-proxy first"
    exit 1
fi

echo "[+] Generating config.php..."
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

echo "[+] Installing Composer dependencies..."
if [ -f /opt/iptv-proxy/composer.json ]; then
    cd /opt/iptv-proxy
    if command -v composer &>/dev/null; then
        composer install --no-dev --optimize-autoloader 2>&1 | tail -5
    else
        php -r "copy('https://install.phpcomposer.com/installer', 'composer-setup.php');"
        php composer-setup.php --quiet
        rm composer-setup.php
        php composer.phar install --no-dev --optimize-autoloader 2>&1 | tail -5
    fi
fi

echo "[+] Setting permissions..."
chown -R www-data:www-data /opt/iptv-proxy
chmod -R 755 /opt/iptv-proxy
mkdir -p /opt/iptv-proxy/storage/logs /opt/iptv-proxy/storage/cache
chmod -R 777 /opt/iptv-proxy/storage

echo "[+] Configuring PHP-FPM..."
sed -i 's/^user = www-data/user = www-data/' /etc/php/8.1/fpm/pool.d/www.conf
sed -i 's/^group = www-data/group = www-data/' /etc/php/8.1/fpm/pool.d/www.conf
sed -i 's/^listen.owner = www-data/listen.owner = www-data/' /etc/php/8.1/fpm/pool.d/www.conf
sed -i 's/^listen.group = www-data/listen.group = www-data/' /etc/php/8.1/fpm/pool.d/www.conf
systemctl enable php8.1-fpm --now

echo "[+] Configuring Nginx..."
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

echo "[+] Creating sudo tee privesc vector (B-6)..."
cat > /etc/sudoers.d/www-data-tee << 'SUDOEOF'
www-data ALL=(root) NOPASSWD: /usr/bin/tee
SUDOEOF
chmod 440 /etc/sudoers.d/www-data-tee

echo "[+] Creating operator user..."
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
usermod -aG sudo operator 2>/dev/null || true

echo "[+] Creating ops hint file..."
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

echo "[+] Configuring SSH..."
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config 2>/dev/null || true
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true

echo "[+] Setting up internal network..."
cat >> /etc/netplan/00-installer-config.yaml << 'NETEOF'
    eth1:
      dhcp4: no
      addresses: [192.168.110.1/24]
NETEOF

echo "[+] Cleaning up..."
rm -rf /tmp/* /var/cache/apt/archives/*.deb
history -c

echo ""
echo "============================================"
echo "  VM-B1 (DMZ) Setup Complete"
echo "============================================"
echo "  Web:      http://<IP>/"
echo "  Login:    admin / admin123"
echo "  Operator: operator / 0p3rat0r@GDJ"
echo "  Network:  192.168.110.1/24 on eth1"
echo "  Privesc:  sudo tee (www-data)"
echo "============================================"
echo ""
echo "Attack Chain:"
echo "  B-1: Password reset bypass ( /reset-password )"
echo "  B-2: Command injection  ( /admin/diag )"
echo "  B-6: sudo tee privesc"
