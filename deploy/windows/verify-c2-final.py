#!/usr/bin/env python3
"""Final C2 verification: fix Samba if needed, verify operator escalation"""
import paramiko

host = '192.168.101.141'
user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(c, cmd, use_sudo=False, timeout=30):
    if use_sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:150]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  out: {out.strip()[:1000]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, ec

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# 1. Check Samba config
print("=== Samba config ===")
run(c, "echo 'Gdadmin@123' | sudo -S cat /etc/samba/smb.conf")

# 2. Check if public share directory exists and has content
print("\n=== Samba share content ===")
run(c, "echo 'Gdadmin@123' | sudo -S ls -la /srv/samba/public/")

# 3. Try smbclient with different options
print("\n=== Samba access test ===")
run(c, "smbclient -N -L //localhost 2>&1")

# 4. Check operator escalation
print("\n=== Operator sudo find escalation ===")
run(c, "echo 'Gdadmin@123' | sudo -S cat /etc/sudoers.d/operator-escalate")

# 5. Verify operator can use sudo find
print("\n=== Test operator sudo find ===")
run(c, "echo '0p3rat0r@GDJ' | sudo -S -u operator sudo -S -l 2>&1")

# 6. Also verify C2 web page has Drupal version info (for CVE-2018-7600 identification)
print("\n=== Drupal version in HTML ===")
run(c, "curl -s http://localhost/ | grep -i 'meta.*generator\|drupal.*version' | head -3")

# 7. Verify CHANGELOG.txt (info disclosure - version)
print("\n=== Drupal version from CHANGELOG ===")
run(c, "head -5 /var/www/drupal/CHANGELOG.txt")

c.close()
print("\nDone!")
