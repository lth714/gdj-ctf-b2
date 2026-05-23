#!/bin/bash
# VM-C1 DMZ — RuoYi OA + Roundcube Webmail
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== Fix DNS ==="
echo "nameserver 114.114.114.114" > /etc/resolv.conf
echo "nameserver 223.5.5.5" >> /etc/resolv.conf

echo "=== Fix apt source (aliyun) ==="
sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
apt update

echo "=== Install base packages ==="
apt install -y nginx mysql-server-8.0 mysql-client openssh-server curl wget iptables-persistent ldap-utils smbclient php7.4 php7.4-mysql php7.4-mbstring php7.4-xml php7.4-curl libapache2-mod-php7.4 apache2 maven unzip netcat-openbsd 2>&1 | tail -5

echo "=== Install Java 17 (PPA) ==="
add-apt-repository ppa:openjdk-r/ppa -y
apt update
apt install -y openjdk-17-jdk
java -version 2>&1 | head -1

echo "=== Configure MySQL ==="
systemctl enable mysql --now
mysql -u root << 'SQLEOF'
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024';
FLUSH PRIVILEGES;
SQLEOF

echo "=== Create ry database ==="
mysql -u root -p'R00t@Mysql#2024' -e "CREATE DATABASE IF NOT EXISTS ry CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo "ry database: OK"

echo "=== Extract and build RuoYi OA ==="
mkdir -p /opt/oa-app
cd /opt/oa-app
tar xzf /tmp/ruoyi.tar.gz
# Find the root pom.xml (it's inside the 'ruoyi' subdir)
cd /opt/oa-app/ruoyi

echo "=== Maven build (this takes 5-10 min) ==="
mvn clean package -DskipTests -q 2>&1 | tail -10
echo "Maven build exit: $?"

echo "=== Import RuoYi SQL schema ==="
if [ -f /opt/oa-app/ruoyi/sql/quartz.sql ]; then
    mysql -u root -p'R00t@Mysql#2024' ry < /opt/oa-app/ruoyi/sql/quartz.sql
    echo "quartz.sql imported"
fi
if [ -f /opt/oa-app/ruoyi/sql/ry_20260319.sql ]; then
    mysql -u root -p'R00t@Mysql#2024' ry < /opt/oa-app/ruoyi/sql/ry_20260319.sql
    echo "ry_20260319.sql imported"
else
    echo "WARNING: ry_20260319.sql not found"
fi

echo "=== Setup OA systemd service ==="
# Find the jar
JAR=$(find /opt/oa-app -name "ruoyi-admin*.jar" 2>/dev/null | head -1)
if [ -z "$JAR" ]; then
    JAR="/opt/oa-app/ruoyi/ruoyi-admin/target/ruoyi-admin-4.8.3.jar"
fi
echo "JAR: $JAR"
ls -lh "$JAR" 2>/dev/null || echo "JAR_NOT_FOUND"

cat > /etc/systemd/system/oa-app.service << 'SVCEOF'
[Unit]
Description=GDJ OA System (RuoYi)
After=network.target mysql.service

[Service]
User=root
WorkingDirectory=/opt/oa-app
ExecStart=/usr/bin/java -jar JAR_PLACEHOLDER --spring.profiles.active=druid
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

# Replace placeholder with actual jar path
sed -i "s|JAR_PLACEHOLDER|$JAR|g" /etc/systemd/system/oa-app.service

systemctl daemon-reload
systemctl enable oa-app --now
echo "OA App: $(systemctl is-active oa-app)"

echo "=== Configure Nginx reverse proxy ==="
cat > /etc/nginx/sites-available/oa.conf << 'NGXEOF'
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

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
echo "Nginx: $(systemctl is-active nginx)"

echo "=== Setup Roundcube Webmail ==="
apt install -y roundcube roundcube-mysql 2>/dev/null || true

mkdir -p /var/lib/roundcube
cat > /etc/roundcube/config.inc.php << 'RCEOF'
<?php
$config['db_dsnw'] = 'sqlite:////var/lib/roundcube/roundcube.db?mode=0646';
$config['default_host'] = 'localhost';
$config['smtp_server'] = 'localhost';
$config['smtp_port'] = 25;
$config['product_name'] = '广电局 Webmail';
$config['plugins'] = [];
RCEOF

# Apache for Roundcube on 8081
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
echo "Apache: $(systemctl is-active apache2)"

echo "=== Ops hints file ==="
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

echo "=== Tomcat sudo tee privesc (C-6) ==="
useradd -m -s /bin/bash tomcat 2>/dev/null || true
echo "tomcat ALL=(root) NOPASSWD: /usr/bin/tee" > /etc/sudoers.d/tomcat

echo "=== Create operator user ==="
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
usermod -aG sudo operator
echo "operator: $(id operator 2>&1)"

echo "=== SSH config ==="
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config 2>/dev/null || true
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true

echo "=== iptables DMZ ==="
mkdir -p /etc/iptables
cat > /etc/iptables/rules.v4 << 'IPTEOF'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p tcp --dport 22 -j ACCEPT
-A INPUT -p tcp --dport 80 -j ACCEPT
-A INPUT -p icmp -j ACCEPT
COMMIT
IPTEOF

iptables-restore < /etc/iptables/rules.v4

cat > /etc/rc.local << 'EOF'
#!/bin/bash
/sbin/iptables-restore < /etc/iptables/rules.v4
exit 0
EOF
chmod +x /etc/rc.local

echo "=== Cleanup ==="
rm -f /tmp/ruoyi.tar.gz /tmp/deploy-c1.sh

echo ""
echo "=== VERIFICATION ==="
echo "MySQL: $(systemctl is-active mysql)"
echo "OA App: $(systemctl is-active oa-app)"
echo "Nginx: $(systemctl is-active nginx)"
echo "Apache: $(systemctl is-active apache2)"
echo "operator: $(id operator 2>&1)"
echo "tomcat sudo: $(cat /etc/sudoers.d/tomcat 2>&1)"
echo "iptables: $(iptables -L INPUT -n | head -1)"
echo "Port 80: $(ss -tlnp | grep ':80 ' | wc -l) listening"
echo "Port 8080: $(ss -tlnp | grep ':8080 ' | wc -l) listening"
echo "Port 8081: $(ss -tlnp | grep ':8081 ' | wc -l) listening"
echo "Port 3306: $(ss -tlnp | grep ':3306 ' | wc -l) listening"
echo ""
echo "[✓] VM-C1 setup complete."
echo "    OA:       http://192.168.100.1/"
echo "    Webmail:  http://192.168.100.1/mail"
echo "    Druid:    http://192.168.100.1/druid/ (ruoyi/123456)"
echo "    SSH:      operator@192.168.101.140 (0p3rat0r@GDJ)"
