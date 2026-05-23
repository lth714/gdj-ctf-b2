#!/usr/bin/env python3
"""Fix A2 (192.168.100.2) and B2 (192.168.110.2) - v2 without apt"""
import paramiko, time

user = 'gdadmin'
pwd = 'Gdadmin@123'

def connect(host):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username=user, password=pwd, timeout=10)
    return c

def run(c, cmd, sudo=False, timeout=20):
    if sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:150]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:800]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:200]}")
    return out, err, ec

# ============================================================
# FIX A2
# ============================================================
print("="*70)
print("FIXING A2 (192.168.100.2)")
print("="*70)
c2 = connect('192.168.100.2')

# 1. Save iptables manually to /etc/iptables/rules.v4
print("\n--- Save iptables ---")
run(c2, "echo 'Gdadmin@123' | sudo -S mkdir -p /etc/iptables", timeout=10)
run(c2, "echo 'Gdadmin@123' | sudo -S bash -c 'iptables-save > /etc/iptables/rules.v4' && echo 'SAVED'")

# 2. Install netfilter-persistent (non-interactive)
print("\n--- Install iptables-persistent (non-interactive) ---")
run(c2, "echo 'Gdadmin@123' | sudo -S DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent 2>&1 | tail -3", timeout=120)
run(c2, "echo 'Gdadmin@123' | sudo -S netfilter-persistent save 2>&1", timeout=10)
run(c2, "systemctl is-enabled netfilter-persistent 2>&1 || echo 'NOT_ENABLED'")

# 3. Enable and start Confluence
print("\n--- Start Confluence ---")
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl enable confluence 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl start confluence 2>&1")
print("Waiting 30s for Confluence to initialize...")
time.sleep(30)

# 4. Check Confluence status
print("\n--- Confluence status ---")
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl is-active confluence 2>&1")
run(c2, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8090/ 2>&1")
run(c2, "ss -tlnp | grep 8090")

c2.close()

# ============================================================
# FIX B2
# ============================================================
print("\n" + "="*70)
print("FIXING B2 (192.168.110.2)")
print("="*70)
cb = connect('192.168.110.2')

# 1. Enable and start Jenkins
print("\n--- Start Jenkins ---")
run(cb, "echo 'Gdadmin@123' | sudo -S systemctl enable jenkins 2>&1")
run(cb, "echo 'Gdadmin@123' | sudo -S systemctl start jenkins 2>&1")
print("Waiting 45s for Jenkins (Java WAR) to start...")
time.sleep(45)

# 2. Check Jenkins status
print("\n--- Jenkins status ---")
run(cb, "echo 'Gdadmin@123' | sudo -S systemctl is-active jenkins 2>&1")
run(cb, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8081/ 2>&1")
run(cb, "ss -tlnp | grep 8081")

# 3. Check jenkins_backup.sh exists
print("\n--- Escalation vector check ---")
run(cb, "ls -la /opt/jenkins_backup.sh 2>/dev/null")
run(cb, "cat /etc/cron.d/jenkins-backup 2>/dev/null || echo 'CRON_NOT_FOUND'")

# If missing, create them
out, err, ec = run(cb, "ls /opt/jenkins_backup.sh 2>/dev/null")
if ec != 0:
    print("Creating escalation vector...")
    run(cb, "echo 'Gdadmin@123' | sudo -S bash -c 'cat > /opt/jenkins_backup.sh << SCRIPTEOF\n#!/bin/bash\n# Jenkins backup script — runs as root via cron\ntar czf /var/backups/jenkins-\\$(date +%Y%m%d).tar.gz /var/lib/jenkins 2>/dev/null\nSCRIPTEOF\nchmod 777 /opt/jenkins_backup.sh'")
    run(cb, "echo 'Gdadmin@123' | sudo -S bash -c 'echo \"0 2 * * * root /opt/jenkins_backup.sh\" > /etc/cron.d/jenkins-backup'")
    run(cb, "ls -la /opt/jenkins_backup.sh")

# 4. Verify operator user
print("\n--- Operator verification ---")
run(cb, "id operator 2>&1")

# 5. Verify all auto-start
print("\n--- Auto-start summary ---")
for svc in ['postgresql', 'api-gateway', 'jenkins', 'netfilter-persistent', 'ssh', 'cron']:
    out, err, ec = run(cb, f"systemctl is-enabled {svc} 2>&1 || echo 'N/A'")
    run(cb, f"systemctl is-active {svc} 2>&1 || echo 'N/A'")

cb.close()

print("\n" + "="*70)
print("DONE!")
print("="*70)
