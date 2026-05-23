#!/usr/bin/env python3
"""Check A2 deployment state in detail"""
import paramiko

host = '192.168.100.2'
user = 'gdadmin'
pwd = 'Gdadmin@123'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected to A2.\n")

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

# 1. Check /opt/deploy/ contents
print("="*60)
print("1. /opt/deploy/ contents")
print("="*60)
run("ls -laR /opt/deploy/ 2>/dev/null")

# 2. Check if Confluence is installed
print("\n" + "="*60)
print("2. Confluence installation state")
print("="*60)
run("ls -la /opt/atlassian/confluence/ 2>/dev/null | head -5")
run("ls -la /opt/atlassian/confluence/bin/ 2>/dev/null | head -5")
run("cat /etc/systemd/system/confluence.service 2>/dev/null")
run("id confluence 2>&1")

# 3. Check MySQL databases
print("\n" + "="*60)
print("3. MySQL databases")
print("="*60)
run("mysql -u root -p'R00t@Mysql#2024' -e 'SHOW DATABASES;' 2>/dev/null")
run("mysql -u root -p'R00t@Mysql#2024' -e 'SELECT COUNT(*) AS tables FROM information_schema.TABLES WHERE TABLE_SCHEMA=\"cms\";' 2>/dev/null")

# 4. Check iptables persistence
print("\n" + "="*60)
print("4. iptables persistence")
print("="*60)
run("ls -la /etc/iptables/rules.v4")
run("systemctl is-enabled netfilter-persistent 2>&1")

# 5. Check sudoers
print("\n" + "="*60)
print("5. Privilege escalation")
print("="*60)
run("cat /etc/sudoers.d/* 2>/dev/null", sudo=True)

# 6. Check Confluence download
print("\n" + "="*60)
print("6. Confluence download files")
print("="*60)
run("ls -la /opt/deploy/files/ 2>/dev/null")
run("find /opt -name 'atlassian-confluence*' -o -name 'confluence*.tar.gz' -o -name 'confluence*.bin' 2>/dev/null")

c.close()
print("\nDone!")
