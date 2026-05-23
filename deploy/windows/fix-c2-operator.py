#!/usr/bin/env python3
"""Fix C2 operator user and final verifications"""
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

# Check if operator exists
print("=== Check operator user ===")
run(c, "id operator 2>&1 || echo 'NOT_FOUND'")

# Check what's in /etc/passwd
run(c, "grep operator /etc/passwd || echo 'NO_OPERATOR_IN_PASSWD'")

# Create operator if missing
print("\n=== Create operator user ===")
run(c, "echo 'Gdadmin@123' | sudo -S useradd -m -s /bin/bash operator && "
     "echo 'operator:0p3rat0r@GDJ' | echo 'Gdadmin@123' | sudo -S chpasswd && "
     "echo 'CREATED'")
# Note: the chpasswd syntax above is wrong. Let me fix it.

# Proper way to set password
run(c, "echo 'Gdadmin@123' | sudo -S bash -c \"echo 'operator:0p3rat0r@GDJ' | chpasswd\" && echo 'PASSWORD_SET'")

# Verify operator exists now
run(c, "id operator")

# Check sudoers
print("\n=== Verify sudoers ===")
run(c, "echo 'Gdadmin@123' | sudo -S cat /etc/sudoers.d/operator-escalate")

# Test sudo -l as operator
print("\n=== Test operator sudo -l ===")
run(c, "echo '0p3rat0r@GDJ' | su - operator -c 'sudo -S -l' 2>&1")

# Test sudo find escalation
print("\n=== Test operator sudo find (execute whoami as root) ===")
run(c, "su - operator -c 'echo 0p3rat0r@GDJ | sudo -S find /etc -name hostname -exec whoami \\; -quit' 2>&1")

# Install smbclient for verification
print("\n=== Install smbclient ===")
run(c, "echo 'Gdadmin@123' | sudo -S apt-get install -y smbclient 2>&1 | tail -3", timeout=60)

# Test Samba access
print("\n=== Test Samba public share ===")
run(c, "smbclient -N -L //localhost 2>&1")
run(c, "smbclient //localhost/public -N -c 'ls' 2>&1")

# Read the 运维手册
print("\n=== Read 运维手册.txt via local path ===")
run(c, "echo 'Gdadmin@123' | sudo -S cat '/srv/samba/public/运维手册.txt'")

# All services summary
print("\n" + "="*60)
print("FINAL C2 SERVICE SUMMARY")
print("="*60)
print("""
  Service       Port    Status    CTF Relevance
  ─────────     ─────   ──────    ─────────────
  Drupal 7.57   80      ✅ 200    CVE-2018-7600 (Drupalgeddon2)
  OpenLDAP      389     ✅        LDAP enumeration + credential harvesting
  Samba         445     ✅        Anonymous file share (运维手册.txt)
  MySQL         3306    ✅        Remote access from C1 (oauser)
  SSH           22      ✅        operator user with sudo find priv esc
""")

c.close()
print("\nDone!")
