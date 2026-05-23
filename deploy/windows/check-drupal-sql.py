#!/usr/bin/env python3
"""Import Drupal 7.57 schema into C2 drupal database"""
import paramiko

host = '192.168.101.141'
user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(c, cmd, use_sudo=False):
    if use_sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    exit_code = stdout.channel.recv_exit_status()
    print(f">>> {cmd[:120]}")
    if out.strip(): print(f"  out: {out.strip()[:500]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, exit_code

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Find Drupal SQL files
print("=== Finding SQL files ===")
run(c, "find /var/www/drupal -name '*.sql' -o -name '*.mysql' | head -20", use_sudo=True)
run(c, "find /var/www/drupal -name '*.make' -o -name '*.install' | head -20", use_sudo=True)

# Check the install profile
print("\n=== Install profiles ===")
run(c, "ls /var/www/drupal/profiles/", use_sudo=True)
run(c, "ls /var/www/drupal/profiles/standard/ 2>/dev/null", use_sudo=True)
run(c, "ls /var/www/drupal/profiles/minimal/ 2>/dev/null", use_sudo=True)

# Check the includes directory for install files
print("\n=== Includes ===")
run(c, "ls /var/www/drupal/includes/ | grep -i install", use_sudo=True)

c.close()
