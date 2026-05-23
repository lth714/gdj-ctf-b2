#!/bin/bash
# =============================================
# VM-A1 (DMZ) Setup — 融媒体新闻采编发布系统
# Ubuntu 20.04, Run as root
# =============================================
set -e

echo "=========================================="
echo " VM-A1 融媒体新闻采编发布系统 部署脚本"
echo "=========================================="

# -------------------------------
# 1. 系统更新 + 基础软件
# -------------------------------
echo "[1/7] Updating system & installing packages..."
apt update
DEBIAN_FRONTEND=noninteractive apt install -y \
    nginx \
    mysql-server \
    php7.4 php7.4-fpm php7.4-mysql php7.4-mbstring \
    php7.4-xml php7.4-curl php7.4-gd php7.4-zip \
    curl wget netcat-openbsd vim unzip \
    openssh-server sudo

# -------------------------------
# 2. 配置 MySQL
# -------------------------------
echo "[2/7] Configuring MySQL..."
systemctl enable mysql
systemctl start mysql

# 设置 root 密码 (如果尚未设置)
mysql -u root << 'EOSQL' 2>/dev/null || true
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024';
FLUSH PRIVILEGES;
EOSQL

# 导入数据库
echo "[2/7] Importing database..."
mysql -u root -p'R00t@Mysql#2024' < /tmp/deploy/init_db.sql 2>/dev/null || \
mysql -u root < /tmp/deploy/init_db.sql

# -------------------------------
# 3. 部署 CMS 文件
# -------------------------------
echo "[3/7] Deploying CMS files..."
mkdir -p /var/www/html/baixiu
cp -r /tmp/deploy/news_dev-master/* /var/www/html/baixiu/

# 确保 init_db.sql 不在 web 目录
rm -f /var/www/html/baixiu/init_db.sql

# 设置权限
chown -R www-data:www-data /var/www/html/baixiu
chmod -R 755 /var/www/html/baixiu

# 确保 static/uploads 可写
mkdir -p /var/www/html/baixiu/static/uploads
chmod -R 777 /var/www/html/baixiu/static/uploads

# -------------------------------
# 4. 配置 PHP-FPM
# -------------------------------
echo "[4/7] Configuring PHP-FPM..."
systemctl enable php7.4-fpm
systemctl start php7.4-fpm

# -------------------------------
# 5. 配置 Nginx
# -------------------------------
echo "[5/7] Configuring Nginx..."

cat > /etc/nginx/sites-available/default << 'NGXEOF'
server {
    listen 80 default_server;
    server_name _;

    root /var/www/html/baixiu;
    index index.php index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php7.4-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }
}
NGXEOF

systemctl enable nginx
systemctl restart nginx

# -------------------------------
# 6. 配置提权: www-data sudo tee → root
# -------------------------------
echo "[6/7] Configuring privilege escalation (sudo tee)..."

cat > /etc/sudoers.d/www-data << 'SUDOEOF'
www-data ALL=(root) NOPASSWD: /usr/bin/tee
SUDOEOF
chmod 440 /etc/sudoers.d/www-data

# -------------------------------
# 7. 清理
# -------------------------------
echo "[7/7] Cleaning up..."
rm -rf /tmp/deploy

echo ""
echo "=========================================="
echo " VM-A1 部署完成!"
echo " Web: http://<IP>/baixiu/"
echo " Admin: http://<IP>/baixiu/admin/login.php"
echo " DB: baixiu / root:R00t@Mysql#2024"
echo ""
echo " 提权链: www-data -> sudo tee -> root"
echo " 漏洞: 登录框 SQL 注入 -> INTO OUTFILE webshell"
echo "=========================================="
