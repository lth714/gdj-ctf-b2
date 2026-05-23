#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug why API still reports disabled, check api.php entry point"""
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

# ============================================================
# 1. Check api.php entry point
# ============================================================
print("="*60)
print("1. API.PHP ENTRY POINT")
print("="*60)
run(c1, "cat /var/www/cms/api.php")

# ============================================================
# 2. Check the API base controller
# ============================================================
print("\n" + "="*60)
print("2. API CONTROLLER BASE")
print("="*60)
run(c1, "cat /var/www/cms/apps/api/controller/BaseController.php 2>/dev/null || ls /var/www/cms/apps/api/")
run(c1, "ls -la /var/www/cms/apps/api/")

# ============================================================
# 3. Check if there's an init file in api
# ============================================================
print("\n" + "="*60)
print("3. API INIT CHECK")
print("="*60)
run(c1, "find /var/www/cms/apps/api -type f 2>/dev/null")
run(c1, "grep -rn 'api_open\|API.*开启\|尚未开启API' /var/www/cms/apps/ 2>/dev/null | head -10")

# ============================================================
# 4. Check the PbootCMS config check for API
# ============================================================
print("\n" + "="*60)
print("4. API OPEN CHECK IN CODE")
print("="*60)
run(c1, "grep -rn 'api_open\|open_api\|api.*open\|尚未开启API' /var/www/cms/ --include='*.php' 2>/dev/null | head -15")

# ============================================================
# 5. Check SearchController for the API check
# ============================================================
print("\n" + "="*60)
print("5. SEARCH CONTROLLER FULL")
print("="*60)
run(c1, "cat /var/www/cms/apps/api/controller/SearchController.php")

# ============================================================
# 6. Check runtime config cache
# ============================================================
print("\n" + "="*60)
print("6. RUNTIME CONFIG CACHE")
print("="*60)
run(c1, "ls -la /var/www/cms/runtime/config/")
run(c1, "cat /var/www/cms/runtime/config/* 2>/dev/null | head -50")
# Clear config cache
run(c1, "echo 'Gdadmin@123' | sudo -S rm -f /var/www/cms/runtime/config/* 2>&1; echo CLEARED")
# Kill PHP session for api
run(c1, "echo 'Gdadmin@123' | sudo -S rm -f /var/www/cms/runtime/cache/* 2>&1; echo CACHE_CLEARED")

# ============================================================
# 7. Test again
# ============================================================
print("\n" + "="*60)
print("7. TEST API AFTER CACHE CLEAR")
print("="*60)
run(c1, "curl -s 'http://localhost/api.php/search?keyword=test' 2>&1")
run(c1, "curl -s 'http://localhost/api.php/search?keyword=test%27' 2>&1")

c1.close()
print("\nDone!")
