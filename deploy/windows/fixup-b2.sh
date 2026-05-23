#!/bin/bash
# B2 Fixup: Jenkins war install + operator fix + iptables + cron
set -e

echo "=== Move Jenkins war ==="
mv /tmp/jenkins.war /opt/jenkins/jenkins.war
chown jenkins:jenkins /opt/jenkins/jenkins.war
ls -lh /opt/jenkins/jenkins.war

echo "=== Restart Jenkins ==="
systemctl restart jenkins
echo "Jenkins: $(systemctl is-active jenkins)"

echo "=== Fix operator user ==="
# Delete first in case of pam corruption from previous run
userdel -r operator 2>/dev/null || true
rm -rf /home/operator
useradd -m -s /bin/bash operator
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
# Jenkins backup script - runs as root via cron
tar czf /var/backups/jenkins-$(date +%Y%m%d).tar.gz /var/lib/jenkins 2>/dev/null
EOF
chmod 777 /opt/jenkins_backup.sh
mkdir -p /var/backups
echo "0 2 * * * root /opt/jenkins_backup.sh" > /etc/cron.d/jenkins-backup

echo "=== SSH config ==="
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config 2>/dev/null || true
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true

echo ""
echo "=== FINAL VERIFICATION ==="
echo "PostgreSQL: $(systemctl is-active postgresql)"
echo "API Gateway: $(systemctl is-active api-gateway)"
echo "Jenkins: $(systemctl is-active jenkins)"
echo "operator: $(id operator 2>&1)"
echo "iptables: $(iptables -L INPUT -n 2>/dev/null | head -1)"
echo "Port 5432: $(ss -tlnp | grep 5432 | wc -l) listening"
echo "Port 8080: $(ss -tlnp | grep 8080 | wc -l) listening"
echo "Port 8081: $(ss -tlnp | grep 8081 | wc -l) listening"
echo "jenkins_backup.sh: $(ls -la /opt/jenkins_backup.sh 2>&1)"
echo "Cron: $(cat /etc/cron.d/jenkins-backup 2>&1)"
echo "[✓] VM-B2 fixup complete."
