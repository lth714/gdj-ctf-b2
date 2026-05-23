#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix A1: Enable API, fix admin login, verify SQLi"""
import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user = 'gdadmin'
pwd = 'Gdadmin@123'
cms_user = 'cmsuser'
cms_pass = 'Cm5Us3r@2024!'

def run(ssh, cmd, timeout=30):
    print(f">>> {cmd[:150]}")
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

# ============================================================
# 1. Read full API SearchController (was cut off)
# ============================================================
print("="*60)
print("1. FULL API SEARCH CONTROLLER")
print("="*60)
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

run(c1, "cat /var/www/cms/apps/api/controller/SearchController.php")

# ============================================================
# 2. Enable API via database (set api_enable in ay_config)
# ============================================================
print("\n" + "="*60)
print("2. ENABLE API VIA DB")
print("="*60)
c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

# Check current API config
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost --default-character-set=utf8mb4 -e \"SELECT * FROM cms.ay_config WHERE name LIKE '%api%';\" 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost --default-character-set=utf8mb4 -e \"SELECT name, value FROM cms.ay_config WHERE name LIKE '%api%' OR name LIKE '%open%' OR name='api_open';\" 2>&1")

# List all config items to understand the config structure
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost --default-character-set=utf8mb4 -e \"SELECT name, value, type FROM cms.ay_config LIMIT 60;\" 2>&1")

# ============================================================
# 3. Get the correct admin login formcheck value
# ============================================================
print("\n" + "="*60)
print("3. CORRECT ADMIN LOGIN")
print("="*60)

# Fetch the login page, get formcheck value
out, _, _ = run(c1, "curl -s http://localhost/admin.php | grep -oP 'name=\"formcheck\"[^>]*value=\"[^\"]+' | head -1")
# Also check for formcheck in hidden input
run(c1, "curl -s http://localhost/admin.php | grep -i 'formcheck\|PbootSystem\|checkcode' | head -5")
# Get cookie first
run(c1, "curl -s -c /tmp/cookie1 http://localhost/admin.php -o /dev/null -w '%{http_code}'")
run(c1, "cat /tmp/cookie1")
# Get the formcheck from the page using cookie
run(c1, "curl -s -b /tmp/cookie1 http://localhost/admin.php | grep -oP 'value=\"[a-f0-9]{32}\"' | head -3")
run(c1, "curl -s -b /tmp/cookie1 http://localhost/admin.php 2>&1 | grep -B2 -A2 'formcheck' | head -10")

# ============================================================
# 4. Try to find how PbootCMS validates login
# ============================================================
print("\n" + "="*60)
print("4. CHECK PBootCMS LOGIN MODEL")
print("="*60)
run(c1, "cat /var/www/cms/apps/admin/model/system/UserModel.php 2>/dev/null | head -80")
# Also check the login controller
run(c1, "grep -rn 'login\|formcheck\|password' /var/www/cms/apps/admin/controller/system/ 2>/dev/null | head -20")

# ============================================================
# 5. Direct password hash check - test if our hash is correct
# ============================================================
print("\n" + "="*60)
print("5. PASSWORD HASH VERIFICATION")
print("="*60)
# Check what the actual login controller does
run(c1, "find /var/www/cms/apps/admin -name '*ogin*' -o -name '*Index*' 2>/dev/null")
run(c1, "cat /var/www/cms/apps/admin/controller/IndexController.php 2>/dev/null | head -80")

c1.close()
c2.close()
print("\nDone!")
