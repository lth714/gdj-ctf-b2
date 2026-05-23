#!/usr/bin/env python3
"""B1 final verification: operator sudo, full app.py, CTF chain check"""
import paramiko

host = '192.168.110.1'
user = 'gdadmin'
pwd = 'Gdadmin@123'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected to B1.\n")

def run(cmd, sudo=False, timeout=20):
    if sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:150]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:1500]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:300]}")
    return out, err, ec

# Test operator sudo (use su to switch user context)
print("="*60)
print("1. OPERATOR SUDO VERIFICATION")
print("="*60)
run("su - operator -c 'echo 0p3rat0r@GDJ | sudo -S whoami' 2>&1", timeout=15)

# Read full app.py in sections
print("\n" + "="*60)
print("2. FULL APP.PY (lines 1-80)")
print("="*60)
run("sed -n '1,80p' /opt/monitor/app.py")

print("\n" + "="*60)
print("3. FULL APP.PY (lines 81-160)")
print("="*60)
run("sed -n '81,160p' /opt/monitor/app.py")

print("\n" + "="*60)
print("4. FULL APP.PY (lines 161-218)")
print("="*60)
run("sed -n '161,218p' /opt/monitor/app.py")

# Check all CTF chain components
print("\n" + "="*60)
print("5. CTF CHAIN SUMMARY")
print("="*60)
print("B-1: admin/admin123 login")
run("python3 -c \"import hashlib; print('admin123 sha256:', hashlib.sha256(b'admin123').hexdigest())\"", timeout=10)

print("\nB-2/B-3: SSRF + RCE endpoints in app.py")
run("grep -n 'def \\|@app.route\\|fetch_url\\|request.args\\|subprocess\\|os.system\\|exec(' /opt/monitor/app.py 2>/dev/null", timeout=10)

print("\nB-4: api_config.yaml PG creds")
run("cat /opt/configs/api_config.yaml")

print("\nB-6: cleanup.sh escalation")
run("ls -la /opt/monitor/cleanup.sh")
run("cat /etc/cron.d/* 2>/dev/null | grep cleanup")

print("\nB-7/B-8: From B1 shell -> B2 Jenkins (requires network)")
run("ping -c 1 -W 2 192.168.110.2 2>&1 | grep -E 'from|loss'")

# Auto-start final check
print("\n" + "="*60)
print("6. AUTO-START FINAL")
print("="*60)
for svc in ['nginx', 'monitor-dashboard', 'ssh', 'cron', 'netfilter-persistent']:
    out, _, _ = run(f"systemctl is-enabled {svc} 2>&1", timeout=5)

c.close()
print("\nDone!")
