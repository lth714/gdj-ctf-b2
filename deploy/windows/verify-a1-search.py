#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug A1 PbootCMS: check routing, search endpoint, and admin login"""
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
            print(f"  [output suppressed, encoding]")
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
# 1. Check PbootCMS file structure
# ============================================================
print("="*60)
print("1. PBOOTCMS FILE STRUCTURE")
print("="*60)
run(c1, "ls /var/www/cms/apps/")
run(c1, "ls /var/www/cms/apps/home/controller/")
run(c1, "ls /var/www/cms/apps/api/controller/ 2>/dev/null || echo 'no api'")

# ============================================================
# 2. Check IndexController for search method
# ============================================================
print("\n" + "="*60)
print("2. SEARCH FUNCTIONALITY")
print("="*60)
run(c1, "grep -n 'function search\|search\|keyword' /var/www/cms/apps/home/controller/IndexController.php 2>/dev/null | head -20")
run(c1, "grep -rn 'keyword\|search' /var/www/cms/apps/home/controller/ 2>/dev/null | head -20")

# Check if SearchController exists
run(c1, "find /var/www/cms/apps -name '*earch*' -type f 2>/dev/null")

# ============================================================
# 3. Check the PbootCMS database config on A1
# ============================================================
print("\n" + "="*60)
print("3. DATABASE CONFIG")
print("="*60)
out, _, _ = run(c1, "cat /var/www/cms/config/database.php")

# ============================================================
# 4. Check Nginx configuration
# ============================================================
print("\n" + "="*60)
print("4. NGINX CONFIGURATION")
print("="*60)
run(c1, "cat /etc/nginx/sites-available/cms")
run(c1, "cat /etc/nginx/nginx.conf 2>/dev/null | head -20")

# ============================================================
# 5. Test different URL patterns
# ============================================================
print("\n" + "="*60)
print("5. URL PATTERN TESTS")
print("="*60)
urls = [
    "/",
    "/admin.php",
    "/index.php",
    "/index.php?p=/Index/search",
    "/?keyword=test",
    "/api.php/search",
    "/index.php?keyword=test",
    "/search",
    "/?search=test",
]
for url in urls:
    out, _, _ = run(c1, f"curl -s -o /dev/null -w '%{{http_code}}' 'http://localhost{url}'")
    print(f"  HTTP {out.strip():>3}  {url}")

# ============================================================
# 6. Check apache mod_rewrite
# ============================================================
print("\n" + "="*60)
print("6. APACHE REWRITE DEBUG")
print("="*60)
run(c1, "echo 'Gdadmin@123' | sudo -S a2enmod rewrite 2>&1 | tail -3")
run(c1, "echo 'Gdadmin@123' | sudo -S apache2ctl -M 2>&1 | grep rewrite")

# ============================================================
# 7. Test admin login more carefully
# ============================================================
print("\n" + "="*60)
print("7. ADMIN LOGIN DEBUG")
print("="*60)
# Get the actual login form to see field names
run(c1, "curl -s http://localhost/admin.php | grep -oP 'name=\"[^\"]+' | head -10")

# Try login with correct field names
run(c1, "curl -s -X POST 'http://localhost/admin.php?action=login' -d 'username=admin&password=admin123&formcheck=1' -D - 2>&1 | head -10")

# ============================================================
# 8. Check if there's a .htaccess file that's breaking things
# ============================================================
print("\n" + "="*60)
print("8. VERIFY APACHE vhost")
print("="*60)
run(c1, "echo 'Gdadmin@123' | sudo -S cat /etc/apache2/sites-available/cms.conf")
run(c1, "echo 'Gdadmin@123' | sudo -S apache2ctl -S 2>&1 | head -15")

# Try hitting Apache directly on port 8080
print("\n--- Direct Apache access on port 8080 ---")
run(c1, "curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8080/'")
run(c1, "curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8080/?p=/Index/search'")
run(c1, "curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8080/?p=/Index/search&keyword=test'")
run(c1, "curl -s 'http://localhost:8080/?p=/Index/search&keyword=test' 2>&1 | head -20")
run(c1, "curl -s 'http://localhost:8080/?p=/Index/search' 2>&1 | head -20")

c1.close()
print("\nDone!")
