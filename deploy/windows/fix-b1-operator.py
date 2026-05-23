#!/usr/bin/env python3
"""Fix B1 operator user and read full app.py"""
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
    print(f">>> {cmd[:140]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:1200]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:300]}")
    return out, err, ec

# Fix operator: delete orphan group, recreate
print("="*60)
print("FIX OPERATOR USER")
print("="*60)
run("echo 'Gdadmin@123' | sudo -S groupdel operator 2>&1; echo 'GROUP_CLEANED'", timeout=10)
run("echo 'Gdadmin@123' | sudo -S useradd -m -s /bin/bash -U operator && echo 'USER_CREATED'", timeout=10)
run("echo 'Gdadmin@123' | sudo -S bash -c \"echo 'operator:0p3rat0r@GDJ' | chpasswd\" && echo 'PASSWORD_SET'", timeout=10)
run("echo 'Gdadmin@123' | sudo -S usermod -aG sudo operator && echo 'SUDO_GROUP_ADDED'", timeout=10)
run("id operator")

# Test operator sudo
print("\n" + "="*60)
print("TEST OPERATOR SUDO")
print("="*60)
run("echo 'Gdadmin@123' | sudo -S -u operator sudo -S -k whoami <<< '0p3rat0r@GDJ' 2>&1 | tail -1", timeout=10)
run('echo "0p3rat0r@GDJ" | sudo -S -u operator bash -c "echo 0p3rat0r@GDJ | sudo -S whoami" 2>&1', timeout=10)

# Read full app.py (use head/tail to get everything)
print("\n" + "="*60)
print("FULL APP.PY")
print("="*60)
run("wc -l /opt/monitor/app.py")
run("cat /opt/monitor/app.py", timeout=10)

# Check cleanup.sh write perms
print("\n" + "="*60)
print("CLEANUP.SH PERMS")
print("="*60)
run("ls -la /opt/monitor/cleanup.sh")

c.close()
print("\nDone!")
