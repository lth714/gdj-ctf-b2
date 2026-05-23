#!/usr/bin/env python3
"""Check Drupal 7 schema code to understand MySQL 8 system table issue"""
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
    if out.strip(): print(f"  out: {out.strip()[:2000]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, ec

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Check the MySQL schema.inc for createTableSql
print("=== MySQL schema.inc createTableSql ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n -A30 'function createTableSql' /var/www/drupal/includes/database/mysql/schema.inc")

# Check how table names are quoted
print("\n=== Check table name quoting ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n 'prefixTable\|{.*}\|backtick\|quote' /var/www/drupal/includes/database/mysql/schema.inc | head -20")

# Check the schema.inc in the database directory
print("\n=== database/schema.inc createTable ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n -A10 'function createTable' /var/www/drupal/includes/database/schema.inc | head -20")

# Check how prefixTables works
print("\n=== prefixTables ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n -B2 -A5 'function prefixTables' /var/www/drupal/includes/database/database.inc")

# Actually, the key question: does Drupal 7 use {table} syntax?
# Let me search for how CREATE TABLE is formatted
print("\n=== CREATE TABLE in schema.inc ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n 'CREATE TABLE' /var/www/drupal/includes/database/mysql/schema.inc")

c.close()
