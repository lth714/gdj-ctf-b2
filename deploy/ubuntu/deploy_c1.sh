#!/bin/bash
# ============================================================
# Server-C1 (DMZ) 一键部署 — 广电视听内容运营与接口管理平台
# 用法: sudo bash deploy_c1.sh
# 前提: 已从 Git clone 项目到本地，在项目根目录执行
#       Ubuntu 20.04/22.04, 可连接互联网
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PHP_SRC="$PROJECT_ROOT/q1/core-php-admin-panel-master"

echo "============================================"
echo " Server-C1 (DMZ) 一键部署"
echo " 广电视听内容运营与接口管理平台"
echo " Nginx + PHP-FPM + MySQL"
echo "============================================"

if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] 请用 sudo 运行: sudo bash $0"
    exit 1
fi

if [ ! -d "$PHP_SRC" ]; then
    echo "[ERROR] 找不到 PHP 源码目录: $PHP_SRC"
    echo "        请确保在项目根目录执行此脚本"
    exit 1
fi

# ============ 1. 系统更新 ============
echo "[1/12] 更新系统..."
apt update && apt upgrade -y

# ============ 2. 安装软件包 ============
echo "[2/12] 安装 LEMP 环境..."
# Ubuntu 20.04 使用 PHP 7.4 (系统自带), 22.04 使用 PHP 8.1
# 先尝试安装 PHP 8.1, 失败则回退到 PHP 7.4
set +e
DEBIAN_FRONTEND=noninteractive apt install -y \
    nginx \
    php8.1 php8.1-fpm php8.1-mysql php8.1-mbstring \
    php8.1-xml php8.1-curl php8.1-gd php8.1-zip \
    php8.1-redis \
    mysql-server mysql-client \
    redis-tools \
    curl wget netcat-openbsd nmap vim openssh-server unzip 2>&1
PHP81_OK=$?
set -e

if [ $PHP81_OK -ne 0 ]; then
    echo "   [INFO] PHP 8.1 不可用，改用 PHP 7.4..."
    DEBIAN_FRONTEND=noninteractive apt install -y \
        nginx \
        php7.4 php7.4-fpm php7.4-mysql php7.4-mbstring \
        php7.4-xml php7.4-curl php7.4-gd php7.4-zip \
        php-redis \
        mysql-server mysql-client \
        redis-tools \
        curl wget netcat-openbsd nmap vim openssh-server unzip
    PHP_VER="7.4"
else
    PHP_VER="8.1"
fi
echo "   [OK] PHP $PHP_VER 安装完成"

# ============ 3. MySQL 配置 ============
echo "[3/12] 配置 MySQL 数据库..."
systemctl enable mysql --now

# 创建数据库和应用用户
mysql -u root << 'SQLEOF'
CREATE DATABASE IF NOT EXISTS media_ops
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'media_app'@'localhost' IDENTIFIED BY 'MediaDB@2026!';
GRANT SELECT, INSERT, UPDATE, DELETE ON media_ops.* TO 'media_app'@'localhost';
FLUSH PRIVILEGES;
SQLEOF

# 导入数据库结构
if [ -f "$PHP_SRC/sql/media_ops.sql" ]; then
    mysql -u root media_ops < "$PHP_SRC/sql/media_ops.sql"
    echo "   [OK] 数据库结构导入完成 (9张表 + 种子数据)"
else
    echo "   [ERROR] 找不到 sql/media_ops.sql"
    exit 1
fi

echo "   [OK] MySQL 配置完成: media_app / MediaDB@2026!"

# ============ 4. PHP-FPM ============
echo "[4/12] 配置 PHP-FPM (PHP $PHP_VER)..."
sed -i 's/^user = www-data/user = www-data/' /etc/php/$PHP_VER/fpm/pool.d/www.conf
sed -i 's/^group = www-data/group = www-data/' /etc/php/$PHP_VER/fpm/pool.d/www.conf
# 允许较大的 POST 数据（模板导入可能较大）
sed -i 's/upload_max_filesize = .*/upload_max_filesize = 32M/' /etc/php/$PHP_VER/fpm/php.ini
sed -i 's/post_max_size = .*/post_max_size = 32M/' /etc/php/$PHP_VER/fpm/php.ini
systemctl enable php$PHP_VER-fpm --now

# ============ 5. 部署 PHP 应用 ============
echo "[5/12] 部署 PHP 应用到 /var/www/html..."
rm -rf /var/www/html/*
cp -r "$PHP_SRC"/* /var/www/html/
rm -f /var/www/html/.gitignore
rm -rf /var/www/html/.git 2>/dev/null || true

# 修改 config.php DB 凭据（确保和 MySQL 中创建的一致）
cat > /var/www/html/config/config.php << 'CONFEOF'
<?php

//Note: This file should be included first in every php page.
error_reporting(E_ALL);
ini_set('display_errors', 'Off');
define('BASE_PATH', dirname(dirname(__FILE__)));
define('APP_FOLDER', 'simpleadmin');
define('CURRENT_PAGE', basename($_SERVER['REQUEST_URI']));

require_once BASE_PATH . '/lib/MysqliDb/MysqliDb.php';
require_once BASE_PATH . '/helpers/helpers.php';

/*
|--------------------------------------------------------------------------
| DATABASE CONFIGURATION
|--------------------------------------------------------------------------
 */

define('DB_HOST', "localhost");
define('DB_USER', "media_app");
define('DB_PASSWORD', "MediaDB@2026!");
define('DB_NAME', "media_ops");

// 扩展数据库与缓存服务配置见 config/database.php
// require_once BASE_PATH . '/config/database.php';

/**
 * Get instance of DB object
 */
function getDbInstance() {
    return new MysqliDb(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME);
}
CONFEOF

# ============ 6. 文件权限 ============
echo "[6/12] 设置文件权限..."
chown -R www-data:www-data /var/www/html
chmod -R 755 /var/www/html
# uploads 目录需要可写（模板缓存生成和素材上传）
chmod -R 777 /var/www/html/uploads
echo "   [OK] uploads/ 目录已设为可写"

# ============ 7. Nginx ============
echo "[7/12] 配置 Nginx..."
cat > /etc/nginx/sites-available/media-ops << 'NGXEOF'
server {
    listen 80 default_server;
    server_name _;
    root /var/www/html;
    index index.php index.html;

    # 禁止直接访问配置文件
    location ~ /config/database\.php$ {
        deny all;
    }

    # 禁止访问 .sql 和隐藏文件
    location ~ /\. {
        deny all;
    }

    location ~ \.sql$ {
        deny all;
    }

    # API 路由重写
    location /api/ {
        if (!-e $request_filename) {
            rewrite ^/api/(.*)$ /api/index.php last;
        }
    }

    # 主路由
    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
    }
}
NGXEOF

# 修正 PHP-FPM socket 路径为实际 PHP 版本
sed -i "s/php8.1-fpm.sock/php$PHP_VER-fpm.sock/" /etc/nginx/sites-available/media-ops

ln -sf /etc/nginx/sites-available/media-ops /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/default.old 2>/dev/null || true
nginx -t && systemctl restart nginx
systemctl enable nginx

# ============ 8. 防火墙 ============
echo "[8/12] 配置防火墙..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp
ufw allow 22/tcp
ufw --force enable
echo "   [OK] 防火墙: 仅开放 80/tcp, 22/tcp"

# ============ 9. iptables 规则（允许 C1 访问 C2 Redis） ============
echo "[9/12] 配置 iptables..."
# 允许出站到 C2 Redis (192.168.110.20:6379)
iptables -A OUTPUT -d 192.168.110.20 -p tcp --dport 6379 -j ACCEPT 2>/dev/null || true
echo "   [OK] iptables: 允许访问 192.168.110.20:6379"

# ============ 10. operator 用户 ============
echo "[10/12] 创建运维用户..."
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd 2>/dev/null || true
usermod -aG sudo operator 2>/dev/null || true

# ============ 11. 运维提示文件 ============
echo "[11/12] 创建运维提示文件..."
mkdir -p /opt/ops
cat > /opt/ops/access.txt << 'OPSEOF'
=====================================================
  广电视听内容运营平台 — 部署信息
  部署日期: 2024-06-15
=====================================================

  服务端口:
    - Web: 80 (Nginx + PHP-FPM)
    - MySQL: 3306 (仅本地)
    - SSH: 22

  数据库:
    库名: media_ops
    用户: media_app / MediaDB@2026!

  后台管理:
    URL: http://<本机IP>/
    管理员: admin / Admin@Media2026
    运营: operator / Operator@Media2026
    编辑: editor / Editor@Media2026

  接口文档:
    Swagger: /swagger/index.html
    OpenAPI: /swagger/openapi.yaml

  缓存发布支撑区:
    内网缓存节点: 192.168.110.20:6379
    队列 Key: media:publish:queue

  运维注意事项:
    1. 部分 API 接口联调期间临时开放，后续需统一接入认证网关
    2. 发布模板导入支持旧版序列化格式（历史兼容）
    3. 接口文档(swagger/)为内部联调使用，不对外暴露
OPSEOF
chmod 644 /opt/ops/access.txt

# ============ 12. 收尾 ============
echo "[12/12] 清理收尾..."
hostnamectl set-hostname gdctf-C1
sed -i '/127.0.1.1/d' /etc/hosts 2>/dev/null || true
echo "127.0.1.1 gdctf-C1" >> /etc/hosts
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true
rm -rf /tmp/*
history -c

echo ""
echo "============================================"
echo "  [OK] Server-C1 (DMZ) 部署完成!"
echo "============================================"
echo "  Web:       http://192.168.110.10/"
echo "  Swagger:   http://192.168.110.10/swagger/"
echo "  Login:     admin / Admin@Media2026"
echo "              operator / Operator@Media2026"
echo "              editor / Editor@Media2026"
echo "============================================"
echo ""
echo "攻击链验证 (C1):"
echo "  1. Swagger 未授权: curl http://192.168.110.10/swagger/openapi.yaml"
echo "  2. 用户API未授权: curl http://192.168.110.10/api/v1/users"
echo "  3. 创建管理员: curl -X POST http://192.168.110.10/api/v1/users -H 'Content-Type: application/json' -d '{\"username\":\"testadmin\",\"password\":\"Test123!\",\"role\":\"admin\"}'"
echo "  4. 反序列化入口: curl -X POST http://192.168.110.10/api/v1/templates/import -H 'Content-Type: application/json' -d '{\"package\":\"...\"}'"
echo "  5. 查看数据库配置: webshell后 cat /var/www/html/config/database.php"
echo ""
echo "  配置凭据: cat /opt/ops/access.txt"
echo "============================================"
