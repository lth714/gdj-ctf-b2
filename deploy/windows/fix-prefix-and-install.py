#!/usr/bin/env python3
"""Fix Drupal 7 prefixTables to backtick-quote table names, then install"""
import paramiko

host = '192.168.101.141'
user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(c, cmd, use_sudo=False, timeout=60):
    if use_sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:150]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  out: {out.strip()[:2000]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, ec

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Find where prefixSearch and prefixReplace are set
print("=== Find prefixSearch/prefixReplace setup ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n 'prefixSearch\|prefixReplace' /var/www/drupal/includes/database/database.inc")

# Also check the MySQL-specific constructor
print("\n=== MySQL connection constructor (full) ===")
run(c, "echo 'Gdadmin@123' | sudo -S sed -n '/function __construct/,/^  }/p' /var/www/drupal/includes/database/mysql/database.inc")

c.close()
