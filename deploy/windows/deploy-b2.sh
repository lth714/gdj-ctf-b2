#!/bin/bash
# VM-B2 Internal — PostgreSQL + Go API Gateway + Jenkins
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== Fix DNS ==="
echo "nameserver 114.114.114.114" > /etc/resolv.conf
echo "nameserver 223.5.5.5" >> /etc/resolv.conf

echo "=== Fix apt source (aliyun) ==="
sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
apt update

echo "=== Install packages ==="
apt install -y postgresql-12 golang-go python3-pip openssh-server curl wget openjdk-11-jdk iptables-persistent

echo "=== PostgreSQL: create users + database ==="
sudo -u postgres psql << 'SQLEOF'
CREATE USER monitor_ro WITH PASSWORD 'M0n1t0rR0@2024!';
CREATE USER monitor WITH SUPERUSER PASSWORD 'M0n1t0r@DB#2024';
CREATE DATABASE monitor OWNER monitor;
GRANT CONNECT ON DATABASE monitor TO monitor_ro;
GRANT USAGE ON SCHEMA public TO monitor_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO monitor_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO monitor_ro;
SQLEOF

sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/12/main/postgresql.conf
echo "host all all 192.168.110.1/32 md5" >> /etc/postgresql/12/main/pg_hba.conf
echo "host all all 127.0.0.1/32 md5" >> /etc/postgresql/12/main/pg_hba.conf
systemctl restart postgresql

echo "=== Build Go API Gateway ==="
mkdir -p /opt/api-gateway
cp /tmp/api-gateway-main.go /opt/api-gateway/main.go
cd /opt/api-gateway
go mod init api-gateway 2>/dev/null || true
go build -o api-gateway main.go

cat > /etc/systemd/system/api-gateway.service << 'EOF'
[Unit]
Description=Internal API Gateway
After=network.target postgresql.service

[Service]
Type=simple
WorkingDirectory=/opt/api-gateway
ExecStart=/opt/api-gateway/api-gateway
Restart=always
Environment=PG_HOST=localhost
Environment=PG_PORT=5432
Environment=PG_USER=monitor
Environment=PG_PASS=M0n1t0r@DB#2024
Environment=PG_DB=monitor

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable api-gateway --now

echo "=== Download Jenkins 2.441 ==="
wget -q --timeout=60 -O /opt/jenkins/jenkins.war "https://get.jenkins.io/war-stable/2.441.1/jenkins.war" 2>&1 || echo "DOWNLOAD_FAILED"
ls -lh /opt/jenkins/jenkins.war 2>/dev/null || echo "JENKINS_WAR_MISSING"

mkdir -p /var/lib/jenkins /opt/jenkins
useradd -m -s /bin/bash jenkins 2>/dev/null || true
chown -R jenkins:jenkins /var/lib/jenkins /opt/jenkins

cat > /etc/systemd/system/jenkins.service << 'EOF'
[Unit]
Description=Jenkins CI Server
After=network.target

[Service]
User=jenkins
WorkingDirectory=/opt/jenkins
ExecStart=/usr/bin/java -jar /opt/jenkins/jenkins.war --httpPort=8081 --httpListenAddress=0.0.0.0
Restart=on-failure
Environment=JENKINS_HOME=/var/lib/jenkins

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
[ -f /opt/jenkins/jenkins.war ] && systemctl enable jenkins --now || echo "Jenkins war missing, service not started"

echo "=== Create operator user ==="
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
usermod -aG sudo operator

echo "=== iptables ==="
mkdir -p /etc/iptables
cat > /etc/iptables/rules.v4 << 'EOF'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -s 192.168.110.1/32 -p tcp --dport 5432 -j ACCEPT
-A INPUT -s 192.168.110.1/32 -p tcp --dport 8080 -j ACCEPT
-A INPUT -s 192.168.110.1/32 -p tcp --dport 8081 -j ACCEPT
-A INPUT -s 192.168.110.0/24 -j ACCEPT
-A INPUT -s 127.0.0.0/8 -j ACCEPT
-A INPUT -p icmp -j ACCEPT
COMMIT
EOF

iptables-restore < /etc/iptables/rules.v4

cat > /etc/rc.local << 'EOF'
#!/bin/bash
/sbin/iptables-restore < /etc/iptables/rules.v4
exit 0
EOF
chmod +x /etc/rc.local

echo "=== Cron privesc vector ==="
cat > /opt/jenkins_backup.sh << 'EOF'
#!/bin/bash
# Jenkins backup script — runs as root via cron
tar czf /var/backups/jenkins-$(date +%Y%m%d).tar.gz /var/lib/jenkins 2>/dev/null
EOF
chmod 777 /opt/jenkins_backup.sh
echo "0 2 * * * root /opt/jenkins_backup.sh" > /etc/cron.d/jenkins-backup

echo "=== Cleanup ==="
rm -f /tmp/api-gateway-main.go

echo ""
echo "=== VERIFICATION ==="
echo "PostgreSQL: $(systemctl is-active postgresql)"
echo "API Gateway: $(systemctl is-active api-gateway)"
echo "Jenkins: $(systemctl is-active jenkins 2>/dev/null || echo 'not-installed')"
echo "operator: $(id operator 2>&1)"
echo "iptables: $(iptables -L INPUT -n | head -1)"
echo "Port 5432: $(ss -tlnp | grep 5432 | wc -l) listening"
echo "Port 8080: $(ss -tlnp | grep 8080 | wc -l) listening"
echo "Port 8081: $(ss -tlnp | grep 8081 | wc -l) listening"
echo ""
echo "[✓] VM-B2 setup complete."
