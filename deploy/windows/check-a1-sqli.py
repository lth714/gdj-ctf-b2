#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check A1 PbootCMS SQL injection points in search and API controllers"""
import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user = 'gdadmin'
pwd = 'Gdadmin@123'

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
            print(f"  [output suppressed, {len(out.strip())} chars]")
    if err.strip() and ec != 0:
        try:
            print(f"  [err] {err.strip()[:300]}")
        except:
            print(f"  [err suppressed]")
    return out, err, ec

c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

# ============================================================
# 1. Read SearchController for SQLi vulnerability
# ============================================================
print("="*60)
print("1. SEARCH CONTROLLER (HOME)")
print("="*60)
run(c1, "cat /var/www/cms/apps/home/controller/SearchController.php")

# ============================================================
# 2. Read API SearchController for SQLi vulnerability
# ============================================================
print("\n" + "="*60)
print("2. SEARCH CONTROLLER (API)")
print("="*60)
run(c1, "cat /var/www/cms/apps/api/controller/SearchController.php")

# ============================================================
# 3. Read the search model (where the DB query likely happens)
# ============================================================
print("\n" + "="*60)
print("3. SEARCH MODEL")
print("="*60)
run(c1, "find /var/www/cms/apps -name '*earch*' -o -name '*Search*' 2>/dev/null")
run(c1, "cat /var/www/cms/apps/home/model/SearchModel.php 2>/dev/null || echo 'NOT_FOUND'")

# ============================================================
# 4. Check the parser model for SQL queries
# ============================================================
print("\n" + "="*60)
print("4. PARSER MODEL (search queries)")
print("="*60)
run(c1, "grep -rn 'keyword\|like\|SELECT.*keyword\|where.*keyword' /var/www/cms/apps/home/model/ 2>/dev/null | head -20")
run(c1, "grep -rn 'keyword\|like\|SELECT.*keyword' /var/www/cms/apps/api/model/ 2>/dev/null | head -20")

# ============================================================
# 5. Test actual search with SQLi probes
# ============================================================
print("\n" + "="*60)
print("5. SQLi PROBE TESTS")
print("="*60)

# Test normal search
run(c1, "curl -s 'http://localhost/search?keyword=test' 2>&1 | head -20")

# Test SQLi probe
run(c1, "curl -s \"http://localhost/search?keyword=test'\" 2>&1 | head -20")
run(c1, "curl -s -o /dev/null -w '%{http_code}' \"http://localhost/search?keyword=test'\"" )

# Test via API
run(c1, "curl -s 'http://localhost/api.php/search?keyword=test' 2>&1 | head -20")

# Test homepage keyword
run(c1, "curl -s 'http://localhost/?keyword=test' 2>&1 | grep -oP '(?<=<title>).*?(?=</title>)'")

# ============================================================
# 6. Verify admin login success
# ============================================================
print("\n" + "="*60)
print("6. ADMIN LOGIN VERIFICATION")
print("="*60)
# Full login with cookie capture
run(c1, "curl -s -X POST 'http://localhost/admin.php?action=login' -d 'username=admin&password=admin123&formcheck=1' -c /tmp/cookie 2>&1 && cat /tmp/cookie")

# Try accessing admin dashboard with cookie
run(c1, "curl -s -b /tmp/cookie 'http://localhost/admin.php' 2>&1 | head -20")

# ============================================================
# 7. Check PbootCMS password format
# ============================================================
print("\n" + "="*60)
print("7. PASSWORD FORMAT CHECK")
print("="*60)
run(c1, "grep -rn 'md5\|password.*md5\|encrypt' /var/www/cms/apps/admin/model/system/UserModel.php 2>/dev/null | head -10")

c1.close()
print("\nDone!")
