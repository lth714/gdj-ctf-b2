#!/usr/bin/env python3
"""Fix and verify A2 (192.168.100.2) and B2 (192.168.110.2)"""
import paramiko, time

user = 'gdadmin'
pwd = 'Gdadmin@123'

def connect(host):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username=user, password=pwd, timeout=10)
    return c

def run(c, cmd, sudo=False, timeout=30):
    if sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:150]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:1000]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:300]}")
    return out, err, ec

# ============================================================
# FIX A2
# ============================================================
print("="*70)
print("FIXING A2 (192.168.100.2)")
print("="*70)
c2 = connect('192.168.100.2')

# 1. Fix iptables persistence
print("\n--- Fix iptables persistence ---")
run(c2, "echo 'Gdadmin@123' | sudo -S apt-get install -y iptables-persistent 2>&1 | tail -5", timeout=60)
run(c2, "echo 'Gdadmin@123' | sudo -S bash -c 'iptables-save > /etc/iptables/rules.v4 && netfilter-persistent save' && echo 'IPTABLES_SAVED'")
run(c2, "systemctl is-enabled netfilter-persistent 2>&1 || systemctl enable netfilter-persistent")

# 2. Enable and start Confluence
print("\n--- Start Confluence ---")
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl enable confluence 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl start confluence 2>&1")
print("Waiting 30s for Confluence to start...")
time.sleep(30)

# 3. Verify Confluence
print("\n--- Verify Confluence ---")
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl is-active confluence 2>&1")
run(c2, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8090/ 2>&1")
run(c2, "curl -s http://localhost:8090/ 2>&1 | head -3")

# 4. Verify all auto-start services
print("\n--- Auto-start verification ---")
for svc in ['mysql', 'redis-server', 'confluence', 'netfilter-persistent', 'ssh']:
    out, err, ec = run(c2, f"systemctl is-enabled {svc} 2>&1 || echo 'NOT_ENABLED'")
    run(c2, f"systemctl is-active {svc} 2>&1 || echo 'NOT_ACTIVE'")

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
print("Waiting 45s for Jenkins to start (Java WAR is slow)...")
time.sleep(45)

# 2. Verify Jenkins
print("\n--- Verify Jenkins ---")
run(cb, "echo 'Gdadmin@123' | sudo -S systemctl is-active jenkins 2>&1")
run(cb, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8081/ 2>&1")
run(cb, "curl -s http://localhost:8081/login 2>&1 | grep -o '<title>[^<]*</title>'")

# 3. Check jenkins_backup.sh and cron
print("\n--- Privilege escalation vector ---")
run(cb, "ls -la /opt/jenkins_backup.sh 2>/dev/null")
run(cb, "cat /opt/jenkins_backup.sh 2>/dev/null")
run(cb, "cat /etc/cron.d/jenkins-backup 2>/dev/null")

# 4. Check operator sudo
print("\n--- Operator check ---")
run(cb, "id operator 2>&1")
run(cb, "echo 'Gdadmin@123' | sudo -S grep operator /etc/shadow | head -1")

# 5. Verify all auto-start services
print("\n--- Auto-start verification ---")
for svc in ['postgresql', 'api-gateway', 'jenkins', 'netfilter-persistent', 'ssh']:
    run(cb, f"systemctl is-enabled {svc} 2>&1 || echo 'NOT_ENABLED'")
    run(cb, f"systemctl is-active {svc} 2>&1 || echo 'NOT_ACTIVE'")

# 6. Check api-gateway source code for secrets
print("\n--- API Gateway config/secrets ---")
run(cb, "cat /opt/api-gateway/main.go 2>/dev/null | head -100")

cb.close()

print("\n" + "="*70)
print("ALL DONE!")
print("="*70)
