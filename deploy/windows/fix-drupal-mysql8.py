#!/usr/bin/env python3
"""Patch Drupal 7.57 MySQL driver to remove NO_AUTO_CREATE_USER (MySQL 8 incompatible)"""
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
    exit_code = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  out: {out.strip()[:1000]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, exit_code

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Find the line that sets NO_AUTO_CREATE_USER in Drupal's MySQL driver
print("=== Finding NO_AUTO_CREATE_USER in Drupal source ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -rn 'NO_AUTO_CREATE_USER' /var/www/drupal/includes/", timeout=15)
run(c, "echo 'Gdadmin@123' | sudo -S grep -rn 'NO_AUTO_CREATE_USER' /var/www/drupal/", timeout=15)

# Read the relevant file
print("\n=== Reading database.inc ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n 'sql_mode\|NO_AUTO_CREATE\|init_commands' /var/www/drupal/includes/database/mysql/database.inc", timeout=15)

# The fix: replace NO_AUTO_CREATE_USER with empty string in the sql_mode setting
# Drupal 7 hardcodes this in includes/database/mysql/database.inc
print("\n=== Applying fix ===")
out, err, ec = run(c,
    "echo 'Gdadmin@123' | sudo -S sed -i "
    "'s/NO_AUTO_CREATE_USER,//g; s/,NO_AUTO_CREATE_USER//g; s/NO_AUTO_CREATE_USER//g' "
    "/var/www/drupal/includes/database/mysql/database.inc && "
    "echo 'PATCHED'",
    timeout=15)

# Verify the fix
print("\n=== Verifying fix ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n 'sql_mode' /var/www/drupal/includes/database/mysql/database.inc", timeout=15)

print("\nDone!")
c.close()
