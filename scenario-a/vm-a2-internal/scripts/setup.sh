#!/bin/bash
# VM-A2 (Internal) Setup Script — IPTV内容编排 Internal Services Layer
# Run as root on Ubuntu 20.04

set -e

echo "[+] Updating system..."
apt update && apt upgrade -y

echo "[+] Installing packages..."
apt install -y mysql-server-8.0 redis-server python3 python3-pip \
    openssh-server curl wget netcat-openbsd nmap vim \
    openjdk-11-jdk

echo "[+] Configuring MySQL..."
systemctl enable mysql --now

# Create MySQL root config file (database connection reference)
cat > /etc/mysql/mysql.conf.d/root.cnf << 'EOF'
[client]
user=root
password=R00t@Mysql#2024
EOF
chmod 644 /etc/mysql/mysql.conf.d/root.cnf

# Initialize CMS database
mysql -u root << SQLEOF
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024';
FLUSH PRIVILEGES;
SQLEOF

# Copy and execute init_db.sql from the deployment
if [ -f /opt/deploy/init_db.sql ]; then
    mysql -u root -p'R00t@Mysql#2024' < /opt/deploy/init_db.sql
    echo "[+] IPTV platform database initialized from init_db.sql"
else
    echo "[!] WARNING: init_db.sql not found. Database will be EMPTY."
    echo "[!] CMS application on VM-A1 will fail to connect to MySQL."
    mysql -u root -p'R00t@Mysql#2024' -e "CREATE DATABASE IF NOT EXISTS cms CHARACTER SET utf8mb4;"
    mysql -u root -p'R00t@Mysql#2024' -e "CREATE USER IF NOT EXISTS 'cmsuser'@'%' IDENTIFIED BY 'Cm5Us3r@2024!';"
    mysql -u root -p'R00t@Mysql#2024' -e "GRANT ALL PRIVILEGES ON cms.* TO 'cmsuser'@'%';"
    mysql -u root -p'R00t@Mysql#2024' -e "GRANT ALL PRIVILEGES ON cms.* TO 'cmsuser'@'localhost';"
    mysql -u root -p'R00t@Mysql#2024' -e "GRANT FILE ON *.* TO 'cmsuser'@'%';"
    mysql -u root -p'R00t@Mysql#2024' -e "GRANT FILE ON *.* TO 'cmsuser'@'localhost';"
    mysql -u root -p'R00t@Mysql#2024' -e "FLUSH PRIVILEGES;"
fi

# Allow remote connections from VM-A1
sed -i 's/bind-address.*=.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf

# Allow LOAD_FILE from any directory (required for data management)
grep -q '^secure_file_priv' /etc/mysql/mysql.conf.d/mysqld.cnf || \
    echo 'secure_file_priv = ""' >> /etc/mysql/mysql.conf.d/mysqld.cnf

systemctl restart mysql

echo "[+] Configuring Redis..."
sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
systemctl enable redis-server --now

echo "[+] Setting up Confluence 7.13.6 (播控发布支撑知识库)..."
useradd -m -s /bin/bash confluence 2>/dev/null || true
mkdir -p /opt/atlassian/confluence

# Try pre-downloaded tarball first
if [ -f /opt/deploy/files/confluence.tar.gz ]; then
    echo "[+] Extracting Confluence from pre-downloaded archive..."
    tar xzf /opt/deploy/files/confluence.tar.gz -C /tmp/
    mv /tmp/atlassian-confluence-7.13.6/* /opt/atlassian/confluence/
    rm -rf /tmp/atlassian-confluence-7.13.6
else
    echo "[!] confluence.tar.gz not found. Manual download required."
    cat > /opt/atlassian/INSTALL.txt << 'INSTEOF'
Confluence 7.13.6 Setup — 播控发布支撑知识库

1. Download Confluence 7.13.6:
   wget https://product-downloads.atlassian.com/software/confluence/downloads/atlassian-confluence-7.13.6.tar.gz

2. Extract:
   tar xzf atlassian-confluence-7.13.6.tar.gz -C /opt/atlassian/

3. Set Confluence home:
   mkdir -p /var/atlassian/confluence
   echo "confluence.home=/var/atlassian/confluence" > /opt/atlassian/confluence/confluence/WEB-INF/classes/confluence-init.properties

4. Configure systemd service (see confluence.service)

5. Start: systemctl start confluence

6. 访问: http://192.168.100.2:8090
   管理员账号与SSH运维账号相同 (operator)
   Space: IPTV播控运行手册
INSTEOF
fi

# Set Confluence home directory
mkdir -p /var/atlassian/confluence
chown -R confluence:confluence /opt/atlassian /var/atlassian

# Confluence systemd service
cat > /etc/systemd/system/confluence.service << 'EOF'
[Unit]
Description=Atlassian Confluence
After=network.target

[Service]
Type=forking
User=confluence
ExecStart=/opt/atlassian/confluence/bin/start-confluence.sh
ExecStop=/opt/atlassian/confluence/bin/stop-confluence.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable confluence
systemctl start confluence

echo "[+] Creating SSH user (operator)..."
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
usermod -aG sudo operator

# Set up sudo for operator (no password for specific commands)
cat > /etc/sudoers.d/operator << 'EOF'
operator ALL=(ALL) NOPASSWD: /usr/bin/apt, /usr/bin/systemctl, /usr/sbin/service
EOF

echo "[+] Configuring iptables (network isolation)..."
cat > /etc/iptables/rules.v4 << 'EOF'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]

# Allow loopback
-A INPUT -i lo -j ACCEPT

# Allow established connections
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow from VM-A1: MySQL (3306)
-A INPUT -s 192.168.100.1/32 -p tcp --dport 3306 -j ACCEPT

# Allow from VM-A1: Redis (6379)
-A INPUT -s 192.168.100.1/32 -p tcp --dport 6379 -j ACCEPT

# Allow from VM-A1: Confluence (8090) — internal knowledge base
-A INPUT -s 192.168.100.1/32 -p tcp --dport 8090 -j ACCEPT

# SSH is BLOCKED from VM-A1 (access through knowledge base first)
# If you want to allow SSH (alternate path): uncomment below
# -A INPUT -s 192.168.100.1/32 -p tcp --dport 22 -j ACCEPT

# Allow internal traffic
-A INPUT -s 192.168.100.0/24 -j ACCEPT
-A INPUT -s 127.0.0.0/8 -j ACCEPT

# Allow ICMP for discovery
-A INPUT -p icmp -j ACCEPT

COMMIT
EOF

# Install iptables-persistent for reboot-safe rules
echo iptables-persistent iptables-persistent/autosave_v4 boolean true | debconf-set-selections
echo iptables-persistent iptables-persistent/autosave_v6 boolean true | debconf-set-selections
apt install -y iptables-persistent
iptables-restore < /etc/iptables/rules.v4
netfilter-persistent save

echo "[+] Setting up internal network..."
cat >> /etc/netplan/00-installer-config.yaml << 'EOF'
    eth0:
      dhcp4: no
      addresses: [192.168.100.2/24]
EOF

echo "[+] Configuring service health check..."
# Health check script for internal services
cat > /opt/confluence_health_check.sh << 'EOF'
#!/bin/bash
# 播控知识库服务健康检查 — 由计划任务定时执行
systemctl status confluence > /dev/null 2>&1 || systemctl restart confluence
EOF
chmod 777 /opt/confluence_health_check.sh

# Add cron job running as root
echo "*/10 * * * * root /opt/confluence_health_check.sh" > /etc/cron.d/confluence-health

echo "[+] Cleaning up..."
rm -rf /tmp/* /var/cache/apt/archives/*.deb

echo "[✓] VM-A2 setup complete."
echo "    Internal IP: 192.168.100.2"
echo "    MySQL:       192.168.100.2:3306"
echo "    Redis:       192.168.100.2:6379"
echo "    Knowledge:   http://192.168.100.2:8090"
echo "    SSH (op.):   operator@192.168.100.2"
echo "    iptables:    Only 3306/6379/8090 from VM-A1"
