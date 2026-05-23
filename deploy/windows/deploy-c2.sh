#!/bin/bash
# VM-C2 Internal — OpenLDAP + Samba + MySQL + Drupal 7.57 (CVE-2018-7600)
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== Fix DNS ==="
echo "nameserver 114.114.114.114" > /etc/resolv.conf
echo "nameserver 223.5.5.5" >> /etc/resolv.conf

echo "=== Fix apt source (aliyun) ==="
sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
apt update

echo "=== Install packages ==="
apt install -y slapd ldap-utils samba mysql-server-8.0 apache2 php7.4 php7.4-mysql php7.4-mbstring php7.4-xml php7.4-curl php7.4-gd libapache2-mod-php7.4 openssh-server curl wget netcat-openbsd iptables-persistent 2>&1 | tail -3

echo "=== Configure OpenLDAP ==="
echo "slapd slapd/domain string gdj.local" | debconf-set-selections
echo "slapd slapd/internal/adminpw password Ldap@Admin#2024" | debconf-set-selections
echo "slapd slapd/internal/generated_adminpw password Ldap@Admin#2024" | debconf-set-selections
echo "slapd slapd/password1 password Ldap@Admin#2024" | debconf-set-selections
echo "slapd slapd/password2 password Ldap@Admin#2024" | debconf-set-selections
echo "slapd slapd/backend string MDB" | debconf-set-selections
dpkg-reconfigure -f noninteractive slapd

cat > /tmp/base.ldif << 'LDIFEOF'
dn: ou=users,dc=gdj,dc=local
objectClass: organizationalUnit
ou: users

dn: ou=groups,dc=gdj,dc=local
objectClass: organizationalUnit
ou: groups

dn: cn=admin,ou=users,dc=gdj,dc=local
objectClass: inetOrgPerson
cn: admin
sn: Admin
mail: admin@gdj.local
userPassword: Admin@OA2024

dn: cn=zhangsan,ou=users,dc=gdj,dc=local
objectClass: inetOrgPerson
cn: zhangsan
sn: Zhang
mail: zhangsan@gdj.local
userPassword: Pass@1234

dn: cn=operator,ou=users,dc=gdj,dc=local
objectClass: inetOrgPerson
cn: operator
sn: Operator
mail: operator@gdj.local
userPassword: 0p3rat0r@GDJ
LDIFEOF

ldapadd -x -D "cn=admin,dc=gdj,dc=local" -w "Ldap@Admin#2024" -f /tmp/base.ldif 2>/dev/null || true

# Allow remote LDAP
sed -i 's/SLAPD_SERVICES="ldap:\/\/\/ ldapi:\/\/\/"/SLAPD_SERVICES="ldap:\/\/0.0.0.0 ldapi:\/\/\/"/' /etc/default/slapd 2>/dev/null || true
systemctl restart slapd
echo "slapd: $(systemctl is-active slapd)"

echo "=== Configure Samba ==="
cat > /etc/samba/smb.conf << 'EOF'
[global]
   workgroup = GDJ
   server string = GDJ Internal File Server
   security = user
   map to guest = Bad User
   log file = /var/log/samba/log.%m
   max log size = 1000

[public]
   path = /srv/samba/public
   browseable = yes
   read only = yes
   guest ok = yes
   comment = Public Documents
EOF

mkdir -p /srv/samba/public
cat > /srv/samba/public/运维手册.txt << 'EOF'
===========================================
广电局内部OA系统运维手册 v3.0
===========================================

一、服务器列表
  DMZ Web服务器 (OA): 192.168.120.1
  Internal 后端服务器:  192.168.120.2

二、登录信息
  Internal服务器 SSH:
    地址: 192.168.120.2
    用户: operator
    密码: 0p3rat0r@GDJ

  数据库 (MySQL):
    地址: 192.168.120.2:3306
    用户: oauser / Oaus3r@2024!

  LDAP管理:
    地址: 192.168.120.2:389
    Bind DN: cn=admin,dc=gdj,dc=local
    Bind密码: Ldap@Admin#2024

三、内部应用
  内部门户网站: http://192.168.120.2/
  (仅限内网访问，DMZ不可直接访问)

四、故障处理
  如遇到服务异常，SSH登录后执行:
    sudo systemctl restart apache2
    sudo systemctl restart mysql

五、重要提醒
  - 请勿将本手册外传
  - 定期更换密码
  - 运维结束后清理SSH历史

编写日期: 2024-01-15
编写人: 张工
===========================================
EOF

chmod 644 /srv/samba/public/运维手册.txt
systemctl restart smbd
echo "smbd: $(systemctl is-active smbd)"

echo "=== Configure MySQL ==="
systemctl enable mysql --now
mysql -u root << 'SQLEOF'
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024';
FLUSH PRIVILEGES;
SQLEOF

# Create oa database
mysql -u root -p'R00t@Mysql#2024' -e "CREATE DATABASE IF NOT EXISTS oa CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Create oauser
mysql -u root -p'R00t@Mysql#2024' << 'SQLEOF'
CREATE USER IF NOT EXISTS 'oauser'@'%' IDENTIFIED BY 'Oaus3r@2024!';
CREATE USER IF NOT EXISTS 'oauser'@'localhost' IDENTIFIED BY 'Oaus3r@2024!';
GRANT ALL PRIVILEGES ON oa.* TO 'oauser'@'%';
GRANT ALL PRIVILEGES ON oa.* TO 'oauser'@'localhost';
FLUSH PRIVILEGES;
SQLEOF

# Create and populate users table
mysql -u root -p'R00t@Mysql#2024' oa << 'SQLEOF'
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    email VARCHAR(100) DEFAULT '',
    department VARCHAR(50) DEFAULT '',
    role VARCHAR(20) DEFAULT 'user'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO users (username, password, email, department, role) VALUES
('admin',    'admin123',      'admin@gdj.local',     '技术部', 'admin'),
('zhangsan', 'Pass@1234',     'zhangsan@gdj.local',  '市场部', 'user'),
('lisi',     'Lisi@2024',     'lisi@gdj.local',      '研发部', 'user'),
('wangwu',   'WangWu#5678',   'wangwu@gdj.local',    '运维部', 'user'),
('operator', '0p3rat0r@GDJ',  'operator@gdj.local',  '运维部', 'operator');
SQLEOF

# Allow remote connections
sed -i 's/bind-address.*=.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf
systemctl restart mysql
echo "mysql: $(systemctl is-active mysql)"

echo "=== Setup Drupal 7.57 ==="
mkdir -p /var/www/drupal

if [ -f /tmp/drupal-7.57.tar.gz ]; then
    tar xzf /tmp/drupal-7.57.tar.gz -C /tmp/
    mv /tmp/drupal-7.57/* /var/www/drupal/
    mv /tmp/drupal-7.57/.htaccess /var/www/drupal/ 2>/dev/null || true
    rm -rf /tmp/drupal-7.57
    echo "Drupal extracted"
else
    echo "WARNING: drupal-7.57.tar.gz not found!"
fi

# Create Drupal database
mysql -u root -p'R00t@Mysql#2024' -e "CREATE DATABASE IF NOT EXISTS drupal CHARACTER SET utf8mb4;"
mysql -u root -p'R00t@Mysql#2024' -e "GRANT ALL ON drupal.* TO 'oauser'@'%';" 2>/dev/null || true

# Drupal settings
chown -R www-data:www-data /var/www/drupal
mkdir -p /var/www/drupal/sites/default/files
chmod 777 /var/www/drupal/sites/default/files

# Copy settings if exists
if [ -f /var/www/drupal/sites/default/default.settings.php ]; then
    cp /var/www/drupal/sites/default/default.settings.php /var/www/drupal/sites/default/settings.php
    chmod 666 /var/www/drupal/sites/default/settings.php
fi

# Apache for Drupal on port 80
cat > /etc/apache2/sites-available/drupal.conf << 'EOF'
<VirtualHost *:80>
    DocumentRoot /var/www/drupal
    <Directory /var/www/drupal>
        Options FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    ErrorLog ${APACHE_LOG_DIR}/drupal_error.log
    CustomLog ${APACHE_LOG_DIR}/drupal_access.log combined
</VirtualHost>
EOF

a2dissite 000-default 2>/dev/null || true
a2ensite drupal
a2enmod rewrite
systemctl restart apache2
echo "apache2: $(systemctl is-active apache2)"

echo "=== Create operator user ==="
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
usermod -aG sudo operator
echo "operator: $(id operator 2>&1)"

echo "=== sudo find privesc (C-8) ==="
echo "operator ALL=(ALL) NOPASSWD: /usr/bin/find" > /etc/sudoers.d/operator-escalate

echo "=== SSH config ==="
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config 2>/dev/null || true
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true

echo "=== iptables ==="
mkdir -p /etc/iptables
cat > /etc/iptables/rules.v4 << 'IPTEOF'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p tcp --dport 22 -j ACCEPT
-A INPUT -s 192.168.120.1/32 -p tcp --dport 389 -j ACCEPT
-A INPUT -s 192.168.120.1/32 -p tcp --dport 445 -j ACCEPT
-A INPUT -s 192.168.120.1/32 -p tcp --dport 139 -j ACCEPT
-A INPUT -s 192.168.120.1/32 -p tcp --dport 3306 -j ACCEPT
-A INPUT -s 192.168.120.1/32 -p tcp --dport 80 -j ACCEPT
-A INPUT -s 192.168.120.0/24 -j ACCEPT
-A INPUT -s 127.0.0.0/8 -j ACCEPT
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
rm -f /tmp/base.ldif /tmp/drupal-7.57.tar.gz /tmp/deploy-c2.sh

echo ""
echo "=== VERIFICATION ==="
echo "slapd: $(systemctl is-active slapd)"
echo "smbd: $(systemctl is-active smbd)"
echo "mysql: $(systemctl is-active mysql)"
echo "apache2: $(systemctl is-active apache2)"
echo "operator: $(id operator 2>&1)"
echo "sudo find: $(cat /etc/sudoers.d/operator-escalate 2>&1)"
echo "iptables: $(iptables -L INPUT -n | head -1)"
echo "Port 389: $(ss -tlnp | grep ':389 ' | wc -l) listening"
echo "Port 445: $(ss -tlnp | grep ':445 ' | wc -l) listening"
echo "Port 3306: $(ss -tlnp | grep ':3306 ' | wc -l) listening"
echo "Port 80: $(ss -tlnp | grep ':80 ' | wc -l) listening"
echo ""
echo "[✓] VM-C2 setup complete."
echo "    LDAP:   192.168.120.2:389"
echo "    Samba:  192.168.120.2:445"
echo "    MySQL:  192.168.120.2:3306"
echo "    Drupal: http://192.168.120.2/"
echo "    SSH:    operator@192.168.101.x (0p3rat0r@GDJ)"
