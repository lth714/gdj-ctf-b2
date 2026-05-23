#!/bin/bash
# VM-C1 (DMZ) Setup Script — 内部办公OA系统 (RuoYi魔改版)
# Run as root on Ubuntu 20.04

set -e

echo "[+] Updating system..."
apt update && apt upgrade -y

echo "[+] Installing packages..."
DEBIAN_FRONTEND=noninteractive apt install -y \
    software-properties-common nginx maven mysql-server-8.0 mysql-client \
    ldap-utils smbclient \
    php7.4 php7.4-mysql php7.4-mbstring php7.4-xml php7.4-curl \
    libapache2-mod-php7.4 apache2 \
    curl wget netcat-openbsd nmap vim openssh-server \
    iptables-persistent

echo "[+] Installing Java 17 (requires PPA on Ubuntu 20.04)..."
add-apt-repository ppa:openjdk-r/ppa -y
apt update
DEBIAN_FRONTEND=noninteractive apt install -y openjdk-17-jdk

echo "[+] Configuring local MySQL..."
systemctl enable mysql --now
mysql -u root << 'SQLEOF'
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024';
FLUSH PRIVILEGES;
SQLEOF

# Import init_db.sql (creates ry database)
if [ -f /opt/deploy/init_db.sql ]; then
    mysql -u root -p'R00t@Mysql#2024' < /opt/deploy/init_db.sql
    echo "[+] ry database created from init_db.sql"
else
    echo "[!] WARNING: init_db.sql not found. Creating ry database manually."
    mysql -u root -p'R00t@Mysql#2024' -e "CREATE DATABASE IF NOT EXISTS ry CHARACTER SET utf8mb4;"
fi

echo "[+] Building RuoYi OA application..."
mkdir -p /opt/oa-app
cp -r ../files/ruoyi/* /opt/oa-app/
cd /opt/oa-app
mvn clean package -DskipTests -q

echo "[+] Importing RuoYi database schema..."
if [ -f /opt/oa-app/sql/quartz.sql ]; then
    mysql -u root -p'R00t@Mysql#2024' ry < /opt/oa-app/sql/quartz.sql
fi
if [ -f /opt/oa-app/sql/ry_20260319.sql ]; then
    mysql -u root -p'R00t@Mysql#2024' ry < /opt/oa-app/sql/ry_20260319.sql
    echo "[+] RuoYi schema imported successfully"
else
    echo "[!] WARNING: ry_20260319.sql not found. RuoYi tables will be empty."
fi

echo "[+] Setting up OA service (Spring Boot)..."
cat > /etc/systemd/system/oa-app.service << 'SVCEOF'
[Unit]
Description=GDJ OA System (RuoYi)
After=network.target mysql.service

[Service]
Type=simple
User=tomcat
Group=tomcat
WorkingDirectory=/opt/oa-app
ExecStart=/usr/bin/java -jar /opt/oa-app/ruoyi/ruoyi-admin/target/ruoyi-admin.jar --spring.profiles.active=druid --logging.file.path=/home/tomcat/logs
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable oa-app

echo "[+] Configuring nginx reverse proxy..."
cat > /etc/nginx/sites-available/oa.conf << 'NGXEOF'
server {
    listen 80 default_server;
    server_name _;

    # RuoYi OA (Spring Boot on 8080)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Roundcube Webmail (:8081 Apache)
    location /mail {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGXEOF

ln -sf /etc/nginx/sites-available/oa.conf /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/default.old 2>/dev/null || true
nginx -t && systemctl restart nginx
systemctl enable nginx --now

echo "[+] Setting up Roundcube Webmail..."
apt install -y roundcube roundcube-mysql 2>/dev/null || true

cat > /etc/roundcube/config.inc.php << 'RCEOF'
<?php
$config['db_dsnw'] = 'sqlite:////var/lib/roundcube/roundcube.db?mode=0646';
$config['default_host'] = 'localhost';
$config['smtp_server'] = 'localhost';
$config['smtp_port'] = 25;
$config['product_name'] = '广电局 Webmail';
$config['plugins'] = [];
RCEOF

# Apache2 for Roundcube on 8081
cat > /etc/apache2/ports.conf << 'APEOF'
Listen 8081
APEOF

cat > /etc/apache2/sites-available/webmail.conf << 'APEOF'
<VirtualHost *:8081>
    DocumentRoot /var/lib/roundcube/public_html
    <Directory /var/lib/roundcube/public_html>
        Options -Indexes
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
APEOF

a2dissite 000-default 2>/dev/null || true
a2ensite webmail
a2enmod rewrite
systemctl restart apache2
systemctl enable apache2

echo "[+] Creating ops config with hints..."
mkdir -p /opt/ops
cat > /opt/ops/internal_notes.txt << 'OPSEOF'
===== 内网服务清单 =====
LDAP认证: 192.168.120.2:389 (dc=gdj,dc=local)
文件服务器(Samba): 192.168.120.2:445
OA数据库(MySQL): 192.168.120.2:3306
内部门户网站: http://192.168.120.2:80 (Drupal 7)

运维SSH: operator@192.168.120.2 / 0p3rat0r@GDJ
注意: SSH端口在VM-C2可能不通，需通过Drupal获取SSH
OPSEOF
chmod 600 /opt/ops/internal_notes.txt

echo "[+] Setting up sudo for privilege escalation (C-6, 100pts)..."
useradd -m -s /bin/bash tomcat 2>/dev/null || true
echo "tomcat ALL=(root) NOPASSWD: /usr/bin/tee" > /etc/sudoers.d/tomcat
chmod 440 /etc/sudoers.d/tomcat

# Ensure tomcat can write to application directories
chown -R tomcat:tomcat /opt/oa-app
mkdir -p /home/tomcat/logs && chown tomcat:tomcat /home/tomcat/logs

# Also fix the log directory from logback.xml default path
mkdir -p /home/ruoyi/logs && chown -R tomcat:tomcat /home/ruoyi/logs 2>/dev/null || true

echo "[+] Configuring SSH..."
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart sshd

echo "[+] Setting up internal network..."
cat >> /etc/netplan/00-installer-config.yaml << 'NETEOF'
    eth1:
      dhcp4: no
      addresses: [192.168.120.1/24]
NETEOF

echo "[+] Starting OA application..."
systemctl start oa-app

echo "[+] Cleaning up..."
rm -rf /tmp/* /var/cache/apt/archives/*.deb
history -c

echo "[✓] VM-C1 setup complete."
echo "    External:  DHCP on eth0"
echo "    Internal:  192.168.120.1 on eth1"
echo "    OA:        http://<IP>/"
echo "    API:       http://<IP>/api/ping"
echo "    Webmail:   http://<IP>/mail"
echo "    Register:  http://<IP>/register (captcha backdoor: gdj2024)"
echo ""
echo "    OA DB:     192.168.120.2:3306 (oauser/Oaus3r@2024!)"
echo "    LDAP:      192.168.120.2:389 (Ldap@Admin#2024 in config)"
echo "    Drupal:    http://192.168.120.2/ (CVE-2018-7600)"
