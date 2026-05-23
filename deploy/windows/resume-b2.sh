#!/bin/bash
# VM-B2 Resume — Complete remaining setup after partial deploy
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== Fix DNS ==="
echo "nameserver 114.114.114.114" > /etc/resolv.conf
echo "nameserver 223.5.5.5" >> /etc/resolv.conf

echo "=== Fix apt source (aliyun) ==="
sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
apt update

echo "=== Install any missing packages ==="
apt install -y postgresql-12 golang-go python3-pip openssh-server curl wget openjdk-11-jdk iptables-persistent 2>&1 | tail -3

echo "=== PostgreSQL: fix listen address + pg_hba ==="
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/12/main/postgresql.conf

# Check if pg_hba entries already exist
if ! grep -q "192.168.110.1/32" /etc/postgresql/12/main/pg_hba.conf; then
  echo "host all all 192.168.110.1/32 md5" >> /etc/postgresql/12/main/pg_hba.conf
fi
if ! grep -q "127.0.0.1/32" /etc/postgresql/12/main/pg_hba.conf; then
  echo "host all all 127.0.0.1/32 md5" >> /etc/postgresql/12/main/pg_hba.conf
fi

systemctl restart postgresql
echo "PostgreSQL: $(systemctl is-active postgresql)"

echo "=== PostgreSQL: create users + database (if not exist) ==="
sudo -u postgres psql << 'SQLEOF'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'monitor_ro') THEN
    CREATE USER monitor_ro WITH PASSWORD 'M0n1t0rR0@2024!';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'monitor') THEN
    CREATE USER monitor WITH SUPERUSER PASSWORD 'M0n1t0r@DB#2024';
  END IF;
END
$$;
SELECT 1;
SQLEOF

# Create database if not exists
sudo -u postgres psql << 'SQLEOF'
SELECT 1 FROM pg_database WHERE datname = 'monitor' \gset
\if :{1}
  \echo 'DB exists'
\else
  CREATE DATABASE monitor OWNER monitor;
\endif
SQLEOF

sudo -u postgres psql << 'SQLEOF'
GRANT CONNECT ON DATABASE monitor TO monitor_ro;
GRANT USAGE ON SCHEMA public TO monitor_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO monitor_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO monitor_ro;
SQLEOF
echo "PG users/db: OK"

echo "=== Build Go API Gateway ==="
mkdir -p /opt/api-gateway
if [ -f /tmp/api-gateway-main.go ]; then
  cp /tmp/api-gateway-main.go /opt/api-gateway/main.go
fi
cd /opt/api-gateway
go mod init api-gateway 2>/dev/null || true
go build -o api-gateway main.go
echo "Go build exit: $?"

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
echo "API Gateway: $(systemctl is-active api-gateway)"

echo "=== Download Jenkins 2.441 ==="
mkdir -p /opt/jenkins
if [ ! -f /opt/jenkins/jenkins.war ]; then
  wget -q --timeout=120 -O /opt/jenkins/jenkins.war "https://get.jenkins.io/war-stable/2.441.1/jenkins.war" 2>&1 || echo "JENKINS_DOWNLOAD_FAILED"
fi
ls -lh /opt/jenkins/jenkins.war 2>/dev/null || echo "JENKINS_WAR_MISSING"

mkdir -p /var/lib/jenkins
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
if [ -f /opt/jenkins/jenkins.war ]; then
  systemctl enable jenkins --now
  echo "Jenkins: $(systemctl is-active jenkins)"
else
  echo "Jenkins war missing, service not started"
fi

echo "=== Create operator user ==="
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
usermod -aG sudo operator
echo "operator: $(id operator 2>&1)"

echo "=== iptables ==="
mkdir -p /etc/iptables
cat > /etc/iptables/rules.v4 << 'IPTEOF'
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
IPTEOF

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
mkdir -p /var/backups
echo "0 2 * * * root /opt/jenkins_backup.sh" > /etc/cron.d/jenkins-backup

echo "=== SSH config ==="
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config 2>/dev/null || true
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true

echo "=== Cleanup ==="
rm -f /tmp/api-gateway-main.go /tmp/deploy-b2.sh

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
