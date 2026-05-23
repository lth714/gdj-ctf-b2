#!/usr/bin/env python3
"""Fix C2 operator user creation - group already exists"""
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

# Delete existing group if it exists, then create user with that group
print("=== Fix operator group/user ===")
run(c, "echo 'Gdadmin@123' | sudo -S groupdel operator 2>/dev/null; echo 'group_cleaned'")

# Now create user with the operator group
run(c, "echo 'Gdadmin@123' | sudo -S useradd -m -s /bin/bash -U operator && echo 'USER_CREATED'")

# Set password
run(c, "echo 'Gdadmin@123' | sudo -S bash -c \"echo 'operator:0p3rat0r@GDJ' | chpasswd\" && echo 'PASSWORD_SET'")

# Verify
print("\n=== Verify operator ===")
run(c, "id operator")
run(c, "grep operator /etc/passwd")

# Test sudo -l as operator using su
print("\n=== Test operator sudo -l ===")
out, err, ec = run(c, "su - operator -c 'echo 0p3rat0r@GDJ | sudo -S -l' 2>&1")

# Test sudo find privilege escalation
print("\n=== Test sudo find escalation (run whoami as root) ===")
out, err, ec = run(c,
    "su - operator -c 'echo 0p3rat0r@GDJ | sudo -S find /etc -name hostname -exec whoami \\; -quit' 2>&1")

# Comprehensive service verification
print("\n" + "="*60)
print("C2 FINAL VERIFICATION")
print("="*60)

# Drupal
print("\n--- Drupal ---")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c, "curl -s http://localhost/ | grep -o '<title>[^<]*</title>'")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/user/register")

# LDAP
print("\n--- LDAP ---")
run(c, "ldapsearch -x -H ldap://localhost -D 'cn=admin,dc=gdj,dc=local' -w 'Ldap@Admin#2024' -b 'dc=gdj,dc=local' dn 2>&1 | grep '^dn:' | wc -l")

# Samba
print("\n--- Samba ---")
run(c, "smbclient //localhost/public -N -c 'ls' 2>&1 | head -5")

# MySQL
print("\n--- MySQL ---")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT COUNT(*) AS tables FROM information_schema.TABLES WHERE TABLE_SCHEMA=\"drupal\";' 2>/dev/null")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT username FROM oa.users;' 2>/dev/null")

# iptables
print("\n--- iptables ---")
run(c, "echo 'Gdadmin@123' | sudo -S iptables -L INPUT -n 2>/dev/null | head -15")

# operator escalation
print("\n--- Operator priv esc ---")
run(c, "echo '0p3rat0r@GDJ' | su - operator -c 'sudo -S find /etc -name passwd -exec head -1 {} \\; -quit' 2>&1 | grep -v '^su:' | head -3")

c.close()
print("\nDone!")
