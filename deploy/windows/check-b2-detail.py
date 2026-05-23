#!/usr/bin/env python3
"""Check B2 deployment state in detail"""
import paramiko

host = '192.168.110.2'
user = 'gdadmin'
pwd = 'Gdadmin@123'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected to B2.\n")

def run(cmd, sudo=False, timeout=15):
    if sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:120]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:800]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:300]}")
    return out, err, ec

# 1. Check if Jenkins is installed
print("="*60)
print("1. Jenkins installation state")
print("="*60)
run("ls -la /opt/jenkins/ 2>/dev/null | head -5")
run("ls -la /var/lib/jenkins/ 2>/dev/null | head -5")
run("cat /etc/systemd/system/jenkins.service 2>/dev/null")
run("id jenkins 2>&1")
run("which java && java -version 2>&1")

# 2. Check PostgreSQL databases
print("\n" + "="*60)
print("2. PostgreSQL databases")
print("="*60)
run("echo 'Gdadmin@123' | sudo -S -u postgres psql -c '\\l' 2>/dev/null")
run("echo 'Gdadmin@123' | sudo -S -u postgres psql -c '\\du' 2>/dev/null")

# 3. Check API gateway
print("\n" + "="*60)
print("3. API Gateway")
print("="*60)
run("ls -la /opt/api-gateway/ 2>/dev/null")
run("cat /etc/systemd/system/api-gateway.service 2>/dev/null")
run("curl -s http://localhost:8080/ 2>/dev/null | head -5")

# 4. Check iptables persistence
print("\n" + "="*60)
print("4. iptables persistence")
print("="*60)
run("ls -la /etc/iptables/rules.v4 2>/dev/null")
run("systemctl is-enabled netfilter-persistent 2>&1 || echo 'NOT_INSTALLED'")
run("dpkg -l | grep iptables-persistent")

# 5. Check sudoers
print("\n" + "="*60)
print("5. Privilege escalation")
print("="*60)
run("cat /etc/sudoers.d/* 2>/dev/null", sudo=True)

# 6. Check if /opt/deploy exists (not seen earlier)
print("\n" + "="*60)
print("6. /opt/deploy directory")
print("="*60)
run("ls -laR /opt/deploy/ 2>/dev/null || echo 'DIRECTORY_NOT_FOUND'")
run("find /opt -maxdepth 2 -type d 2>/dev/null")

# 7. Check go and api-gateway binary
print("\n" + "="*60)
print("7. Go and API gateway binary")
print("="*60)
run("ls -la /opt/api-gateway/api-gateway 2>/dev/null")
run("file /opt/api-gateway/api-gateway 2>/dev/null")
run("cat /opt/api-gateway/api_config.yaml 2>/dev/null")

c.close()
print("\nDone!")
