#!/bin/bash
# VM-C2 (Internal) Setup Script — 内部办公 Internal Layer
# OpenLDAP + Samba + MySQL + Drupal (N-Day: CVE-2018-7600 Drupalgeddon2)
# Run as root on Ubuntu 20.04

set -e

echo "[+] Updating system..."
apt update && apt upgrade -y

echo "[+] Installing packages..."
DEBIAN_FRONTEND=noninteractive apt install -y \
    slapd ldap-utils samba mysql-server-8.0 \
    apache2 php7.4 php7.4-mysql php7.4-mbstring php7.4-xml php7.4-curl \
    php7.4-gd libapache2-mod-php7.4 \
    openssh-server curl wget netcat-openbsd nmap vim \
    iptables-persistent

echo "[+] Configuring OpenLDAP..."
# Reconfigure slapd with domain
echo "slapd slapd/domain string gdj.local" | debconf-set-selections
echo "slapd slapd/internal/adminpw password Ldap@Admin#2024" | debconf-set-selections
echo "slapd slapd/internal/generated_adminpw password Ldap@Admin#2024" | debconf-set-selections
echo "slapd slapd/password1 password Ldap@Admin#2024" | debconf-set-selections
echo "slapd slapd/password2 password Ldap@Admin#2024" | debconf-set-selections
echo "slapd slapd/backend string MDB" | debconf-set-selections
dpkg-reconfigure -f noninteractive slapd

# Create base LDIF
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

# Allow remote LDAP access
sed -i 's/SLAPD_SERVICES="ldap:\/\/\/ ldapi:\/\/\/"/SLAPD_SERVICES="ldap:\/\/0.0.0.0 ldapi:\/\/\/"/' /etc/default/slapd 2>/dev/null || true
systemctl restart slapd

echo "[+] Configuring Samba..."
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

echo "[+] Configuring MySQL..."
systemctl enable mysql --now

# Initialize OA database
mysql -u root << SQLEOF
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024';
FLUSH PRIVILEGES;
SQLEOF

if [ -f /opt/deploy/init_db.sql ]; then
    mysql -u root -p'R00t@Mysql#2024' < /opt/deploy/init_db.sql
    echo "[+] OA database initialized from init_db.sql"
else
    echo "[!] WARNING: init_db.sql not found. OA database will be EMPTY."
    mysql -u root -p'R00t@Mysql#2024' -e "CREATE DATABASE IF NOT EXISTS oa CHARACTER SET utf8mb4;"
fi

# Allow remote connections
sed -i 's/bind-address.*=.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf
systemctl restart mysql

echo "[+] Setting up Drupal 7.57 (N-Day target CVE-2018-7600)..."
mkdir -p /var/www/drupal

# Try pre-downloaded tarball first
if [ -f /opt/deploy/files/drupal.tar.gz ]; then
    echo "[+] Extracting Drupal from pre-downloaded archive..."
    tar xzf /opt/deploy/files/drupal.tar.gz -C /tmp/
    mv /tmp/drupal-7.57/* /var/www/drupal/
    mv /tmp/drupal-7.57/.htaccess /var/www/drupal/ 2>/dev/null || true
    rm -rf /tmp/drupal-7.57
else
    echo "[!] drupal.tar.gz not found. Manual download required."
    cat > /var/www/drupal/INSTALL.txt << 'DREOF'
Drupal 7.57 Setup (CVE-2018-7600 / Drupalgeddon2 target)

1. Download Drupal 7.57:
   wget https://ftp.drupal.org/files/projects/drupal-7.57.tar.gz -O /tmp/drupal.tar.gz
   tar xzf /tmp/drupal.tar.gz -C /var/www/
   mv /var/www/drupal-7.57/* /var/www/drupal/
   mv /var/www/drupal-7.57/.htaccess /var/www/drupal/

2. Create MySQL database:
   mysql -u root -p'R00t@Mysql#2024' -e "CREATE DATABASE drupal CHARACTER SET utf8mb4;"
   mysql -u root -p'R00t@Mysql#2024' -e "GRANT ALL ON drupal.* TO 'oauser'@'%';"

3. Configure settings.php:
   cp /var/www/drupal/sites/default/default.settings.php /var/www/drupal/sites/default/settings.php
   chmod 666 /var/www/drupal/sites/default/settings.php

4. Set permissions:
   chown -R www-data:www-data /var/www/drupal
   mkdir -p /var/www/drupal/sites/default/files
   chmod 777 /var/www/drupal/sites/default/files

5. Access: http://192.168.120.2/
   Complete installation wizard
   Set admin password: 0p3rat0r@GDJ

CVE-2018-7600 (Drupalgeddon2):
  Unauthenticated RCE via Form API
  POST /user/register?element_parents=account/mail/%23value&ajax_form=1
  &_wrapper_format=drupal_ajax
  &form_id=user_register_form
  &mail[#post_render][]=exec
  &mail[#type]=markup
  &mail[#markup]=id
DREOF
fi

# Create Drupal database
mysql -u root -p'R00t@Mysql#2024' -e "CREATE DATABASE IF NOT EXISTS drupal CHARACTER SET utf8mb4;"
mysql -u root -p'R00t@Mysql#2024' -e "GRANT ALL ON drupal.* TO 'oauser'@'%';" 2>/dev/null || true

# Set permissions
chown -R www-data:www-data /var/www/drupal
mkdir -p /var/www/drupal/sites/default/files
chmod 777 /var/www/drupal/sites/default/files

# Apache vhost for Drupal on port 80
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

echo "[+] Setting up SSH user..."
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
usermod -aG sudo operator

echo "[+] Configuring iptables (network isolation)..."
cat > /etc/iptables/rules.v4 << 'EOF'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]

-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow from VM-C1: LDAP (389)
-A INPUT -s 192.168.120.1/32 -p tcp --dport 389 -j ACCEPT

# Allow from VM-C1: Samba (445)
-A INPUT -s 192.168.120.1/32 -p tcp --dport 445 -j ACCEPT
-A INPUT -s 192.168.120.1/32 -p tcp --dport 139 -j ACCEPT

# Allow from VM-C1: MySQL (3306)
-A INPUT -s 192.168.120.1/32 -p tcp --dport 3306 -j ACCEPT

# Allow from VM-C1: Drupal/HTTP (80) - "内部门户"
-A INPUT -s 192.168.120.1/32 -p tcp --dport 80 -j ACCEPT

# SSH BLOCKED from VM-C1
# Access via Drupal RCE or Samba creds

# Allow internal
-A INPUT -s 192.168.120.0/24 -j ACCEPT
-A INPUT -s 127.0.0.0/8 -j ACCEPT
-A INPUT -p icmp -j ACCEPT

COMMIT
EOF

iptables-restore < /etc/iptables/rules.v4
netfilter-persistent save

echo "[+] Creating privilege escalation vector..."
echo "operator ALL=(ALL) NOPASSWD: /usr/bin/find" > /etc/sudoers.d/operator-escalate

echo "[+] Setting up internal network..."
cat >> /etc/netplan/00-installer-config.yaml << 'EOF'
    eth0:
      dhcp4: no
      addresses: [192.168.120.2/24]
EOF

echo "[+] Cleaning up..."
rm -rf /tmp/* /var/cache/apt/archives/*.deb
rm -f /tmp/base.ldif

echo "[✓] VM-C2 setup complete."
echo "    Internal IP:  192.168.120.2"
echo "    LDAP:        192.168.120.2:389"
echo "    Samba:       192.168.120.2:445"
echo "    MySQL:       192.168.120.2:3306"
echo "    Drupal:      http://192.168.120.2/"
echo "    iptables:    Only 389/445/3306/80 from VM-C1"
