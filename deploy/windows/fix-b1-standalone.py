#!/usr/bin/env python3
"""Fix and verify B1 (192.168.110.1) - standalone"""
import paramiko

host = '192.168.110.1'
user = 'gdadmin'
pwd = 'Gdadmin@123'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected to B1.\n")

def run(ssh, cmd, sudo=False, timeout=20):
    if sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:140]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:1000]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:300]}")
    return out, err, ec

# 1. Monitor app code
print("="*60)
print("1. MONITOR APP CODE + SECRETS")
print("="*60)
run(c, "cat /opt/monitor/app.py")

# 2. Nginx config
print("\n" + "="*60)
print("2. NGINX CONFIG")
print("="*60)
run(c, "cat /etc/nginx/sites-available/monitor.conf 2>/dev/null")
run(c, "cat /etc/nginx/nginx.conf 2>/dev/null | head -20")

# 3. Operator user
print("\n" + "="*60)
print("3. OPERATOR USER")
print("="*60)
run(c, "id operator 2>&1 || echo 'NOT_FOUND'")
run(c, "echo 'Gdadmin@123' | sudo -S grep operator /etc/shadow 2>/dev/null | cut -d: -f1-2")

# 4. Check sudoers
print("\n" + "="*60)
print("4. SUDOERS")
print("="*60)
run(c, "echo 'Gdadmin@123' | sudo -S ls /etc/sudoers.d/")
run(c, "echo 'Gdadmin@123' | sudo -S cat /etc/sudoers.d/* 2>/dev/null")

# 5. Cron / escalation vectors
print("\n" + "="*60)
print("5. CRON + ESCALATION")
print("="*60)
run(c, "cat /opt/monitor/cleanup.sh 2>/dev/null")
run(c, "echo 'Gdadmin@123' | sudo -S cat /etc/cron.d/* 2>/dev/null")
run(c, "echo 'Gdadmin@123' | sudo -S crontab -l 2>/dev/null")

# 6. Auto-start check
print("\n" + "="*60)
print("6. AUTO-START")
print("="*60)
for svc in ['nginx', 'monitor-dashboard', 'ssh', 'cron', 'netfilter-persistent']:
    run(c, f"systemctl is-enabled {svc} 2>&1 || echo 'N/A'")
    run(c, f"systemctl is-active {svc} 2>&1 || echo 'N/A'")

# 7. iptables persistence
print("\n" + "="*60)
print("7. IPTABLES PERSISTENCE")
print("="*60)
run(c, "dpkg -l | grep iptables-persistent")
run(c, "ls -la /etc/iptables/rules.v4 2>/dev/null || echo 'NO_RULES_FILE'")
run(c, "systemctl is-enabled netfilter-persistent 2>&1 || echo 'NOT_ENABLED'")

# 8. Test web app endpoints
print("\n" + "="*60)
print("8. WEB ENDPOINTS")
print("="*60)
run(c, "curl -s http://localhost/ | head -30")
run(c, "curl -s http://localhost:5000/ | head -30")
run(c, "curl -s http://localhost/api/admin/token 2>&1")

# 9. Check if there are other files in /opt
print("\n" + "="*60)
print("9. /opt STRUCTURE")
print("="*60)
run(c, "find /opt -type f 2>/dev/null")
run(c, "find /opt -type d 2>/dev/null")

c.close()
print("\nDone!")
