#!/bin/bash
# VM-B2 (Internal) Setup Script — Zabbix 监控平台
# CTF Scenario B — CVE-2022-23131 (SAML Session Bypass)
# Run as root on Ubuntu 20.04

set -e

echo "=== VM-B2 (Internal) Setup: Zabbix 监控平台 ==="

echo "[+] Updating system..."
apt update && apt upgrade -y

echo "[+] Installing prerequisites..."
DEBIAN_FRONTEND=noninteractive apt install -y \
    postgresql-12 \
    apache2 \
    php7.4 php7.4-pgsql php7.4-mbstring php7.4-xml php7.4-curl \
    php7.4-gd php7.4-ldap php7.4-bcmath \
    curl wget netcat-openbsd nmap vim openssh-server \
    iptables-persistent gnupg

echo "[+] Adding Zabbix 5.4 repository..."
wget -q https://repo.zabbix.com/zabbix/5.4/ubuntu/pool/main/z/zabbix-release/zabbix-release_5.4-1+ubuntu20.04_all.deb \
    -O /tmp/zabbix-release.deb
dpkg -i /tmp/zabbix-release.deb 2>/dev/null || true
apt update

echo "[+] Installing Zabbix 5.4.8 packages..."
DEBIAN_FRONTEND=noninteractive apt install -y \
    zabbix-server-pgsql \
    zabbix-frontend-php \
    zabbix-apache-conf \
    zabbix-agent \
    zabbix-sql-scripts 2>&1 | tail -5

echo "[+] Configuring PostgreSQL for Zabbix..."
systemctl enable postgresql --now

sudo -u postgres psql << 'SQLEOF'
CREATE USER zabbix WITH PASSWORD 'Zabbix@DB#2024';
CREATE DATABASE zabbix OWNER zabbix;
GRANT ALL PRIVILEGES ON DATABASE zabbix TO zabbix;
SQLEOF

echo "[+] Importing Zabbix database schema..."
if [ -f /usr/share/zabbix-sql-scripts/postgresql/server.sql.gz ]; then
    zcat /usr/share/zabbix-sql-scripts/postgresql/server.sql.gz | sudo -u zabbix psql zabbix
elif [ -f /usr/share/doc/zabbix-sql-scripts/postgresql/server.sql.gz ]; then
    zcat /usr/share/doc/zabbix-sql-scripts/postgresql/server.sql.gz | sudo -u zabbix psql zabbix
else
    echo "[!] Zabbix SQL schema not found, trying alternate locations..."
    find /usr/share -name "server.sql.gz" 2>/dev/null | head -1 | xargs -I{} zcat {} | sudo -u zabbix psql zabbix
fi

echo "[+] Configuring Zabbix server..."
cat > /etc/zabbix/zabbix_server.conf << 'ZABEOF'
ListenPort=10051
LogFile=/var/log/zabbix/zabbix_server.log
LogFileSize=10
PidFile=/run/zabbix/zabbix_server.pid

DBHost=localhost
DBName=zabbix
DBUser=zabbix
DBPassword=Zabbix@DB#2024

StartPollers=5
StartTrappers=5
StartDiscoverers=1
CacheSize=8M
Timeout=10
ZABEOF

echo "[+] Configuring Zabbix frontend PHP..."
cat > /etc/zabbix/web/zabbix.conf.php << 'WEBEOF'
<?php
// Zabbix GUI configuration file.
global $DB;

$DB['TYPE']     = 'POSTGRESQL';
$DB['SERVER']   = 'localhost';
$DB['PORT']     = '5432';
$DB['DATABASE'] = 'zabbix';
$DB['USER']     = 'zabbix';
$DB['PASSWORD'] = 'Zabbix@DB#2024';

// Schema name for PostgreSQL
$DB['SCHEMA']   = 'public';

$ZBX_SERVER      = 'localhost';
$ZBX_SERVER_PORT = '10051';
$ZBX_SERVER_NAME = '广电播出监控平台';

$IMAGE_FORMAT_DEFAULT = IMAGE_FORMAT_PNG;
WEBEOF

echo "[+] Configuring Apache for Zabbix..."
cat > /etc/apache2/conf-available/zabbix-frontend-php.conf << 'APACHEOF'
<IfModule mod_php7.c>
    php_value max_execution_time 300
    php_value memory_limit 256M
    php_value post_max_size 32M
    php_value upload_max_filesize 16M
    php_value max_input_time 300
    php_value date.timezone Asia/Shanghai
</IfModule>

Alias / /usr/share/zabbix/
<Directory "/usr/share/zabbix">
    Options FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>
APACHEOF

a2enconf zabbix-frontend-php
a2dissite 000-default 2>/dev/null || true
systemctl restart apache2
systemctl enable apache2

echo "[+] Enabling Zabbix server..."
systemctl enable zabbix-server zabbix-agent --now

echo "[+] Enabling SAML SSO for Zabbix (CVE-2022-23131 prerequisite)..."
# Configure SAML authentication in Zabbix database
# These are fake IdP values — the CVE bypasses signature validation
sudo -u zabbix psql zabbix << 'SAMLSQL'
-- Enable SAML authentication
UPDATE config SET
    authentication_type = 1,
    saml_auth_enabled = 1,
    saml_idp_entityid = 'https://idp.gdj-broadcast.local/saml/metadata',
    saml_sso_url = 'https://idp.gdj-broadcast.local/saml/sso',
    saml_slo_url = 'https://idp.gdj-broadcast.local/saml/slo',
    saml_username_attribute = 'username',
    saml_sp_entityid = 'zabbix-gdj-monitor',
    saml_nameid_format = 'urn:oasis:names:tc:SAML:2.0:nameid-format:transient',
    saml_sign_messages = 0,
    saml_sign_assertions = 0,
    saml_sign_authn_requests = 0,
    saml_case_sensitive = 0,
    saml_x509cert = 'MIIC...FAKE...CERT',
    saml_status = 1
WHERE configid = 1;

-- Ensure Admin user has default password
UPDATE users SET passwd = '5fce1b3e34b520afeffb37ce08c7cd66' WHERE alias = 'Admin';
SAMLSQL

echo "[+] Creating sudo find privesc vector (B-7)..."
cat > /etc/sudoers.d/zabbix-find << 'SUDOEOF'
zabbix ALL=(root) NOPASSWD: /usr/bin/find
SUDOEOF
chmod 440 /etc/sudoers.d/zabbix-find

echo "[+] Creating operator user..."
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
usermod -aG sudo operator 2>/dev/null || true

echo "[+] Setting up internal network..."
# B2 is on the internal network only
cat > /etc/netplan/00-installer-config.yaml << 'NETEOF'
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses: [192.168.110.2/24]
NETEOF

echo "[+] Configuring iptables (internal network isolation)..."
cat > /etc/iptables/rules.v4 << 'IPTEOF'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]

-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow from DMZ (B1): Zabbix HTTP
-A INPUT -s 192.168.110.1/32 -p tcp --dport 80 -j ACCEPT

# Allow from DMZ (B1): Zabbix Agent (10050)
-A INPUT -s 192.168.110.1/32 -p tcp --dport 10050 -j ACCEPT

# Allow from DMZ (B1): PostgreSQL (for B-5)
-A INPUT -s 192.168.110.1/32 -p tcp --dport 5432 -j ACCEPT

# Allow all internal traffic
-A INPUT -s 192.168.110.0/24 -j ACCEPT
-A INPUT -s 127.0.0.0/8 -j ACCEPT
-A INPUT -p icmp -j ACCEPT

# SSH is NOT accessible from DMZ (B1)
COMMIT
IPTEOF

iptables-restore < /etc/iptables/rules.v4
netfilter-persistent save 2>/dev/null || true

echo "[+] Configuring SSH..."
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config 2>/dev/null || true
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true

echo "[+] Creating ops reference files..."
cat > /opt/zabbix_db_note.txt << 'ZBXNOTE'
===== Zabbix PostgreSQL 连接信息 =====
数据库: zabbix
用户:   zabbix
密码:   Zabbix@DB#2024
主机:   localhost:5432

配置文件位置:
  /etc/zabbix/zabbix_server.conf
  /etc/zabbix/web/zabbix.conf.php
ZBXNOTE
chmod 644 /opt/zabbix_db_note.txt

echo "[+] Cleaning up..."
rm -rf /tmp/* /var/cache/apt/archives/*.deb
history -c

echo ""
echo "============================================"
echo "  VM-B2 (Internal) Setup Complete"
echo "============================================"
echo "  Zabbix:   http://192.168.110.2/"
echo "  Admin:    Admin / zabbix"
echo "  Operator: operator / 0p3rat0r@GDJ"
echo "  Network:  192.168.110.2/24 on eth0"
echo "  Privesc:  sudo find (zabbix)"
echo "============================================"
echo ""
echo "Attack Chain:"
echo "  B-3: Lateral movement B1->B2 (discover Zabbix)"
echo "  B-4: CVE-2022-23131 SAML session bypass"
echo "  B-5: Read PG credentials from zabbix_server.conf"
echo "  B-7: sudo find privesc"
