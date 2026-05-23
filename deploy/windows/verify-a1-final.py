#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify A1 PbootCMS after fixes - handle Unicode output properly"""
import paramiko
import sys

# Force UTF-8 for print
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
        # Truncate and encode safely
        text = out.strip()[:2000]
        try:
            print(f"  {text}")
        except UnicodeEncodeError:
            print(f"  [binary/unprintable output, {len(text)} chars]")
    if err.strip() and ec != 0:
        try:
            print(f"  [err] {err.strip()[:500]}")
        except:
            print(f"  [err - encoding issue]")
    return out, err, ec

# ============================================================
# 1. Verify .htaccess
# ============================================================
print("="*60)
print("1. VERIFY .htaccess")
print("="*60)
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

out, _, _ = run(c1, "cat -A /var/www/cms/.htaccess")
# Check for $1
if '$1' in out:
    print("  >>> .htaccess HAS $1 - FIXED!")
else:
    print("  >>> .htaccess MISSING $1 - STILL BROKEN!")

# ============================================================
# 2. Verify admin user
# ============================================================
print("\n" + "="*60)
print("2. VERIFY ADMIN USER")
print("="*60)
c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

out, _, _ = run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost --default-character-set=utf8mb4 -e 'SELECT id,username,password FROM cms.ay_user;' 2>&1")

# ============================================================
# 3. Fix ay_site domain
# ============================================================
print("\n" + "="*60)
print("3. FIX AY_SITE DOMAIN")
print("="*60)
out, _, _ = run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost --default-character-set=utf8mb4 -e 'SELECT id,acode,title,domain FROM cms.ay_site;' 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost --default-character-set=utf8mb4 -e \"UPDATE cms.ay_site SET domain='192.168.100.1' WHERE id=1;\" 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost --default-character-set=utf8mb4 -e 'SELECT id,domain FROM cms.ay_site;' 2>&1")

# ============================================================
# 4. Insert CTF content
# ============================================================
print("\n" + "="*60)
print("4. INSERT CTF CONTENT")
print("="*60)
# Check columns
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SHOW COLUMNS FROM cms.ay_content;' 2>&1 | head -25")

# Insert with proper character set
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost --default-character-set=utf8mb4 cms -e \"INSERT INTO ay_content (acode, scode, title, content, description, author, date, create_time, update_time, status, sorting, visits, likes, oppose, istop, isrecommend, isheadline, create_user, update_user) VALUES ('2', 'notice', '关于进一步加强网络安全管理的通知', '<p>各单位要高度重视网络安全工作，定期开展安全检测，数据库备份文件已存放于 /backup/ 目录下备用。</p>', '广电局网络安全管理办法修订版', '系统管理员', '2023-12-25 10:00:00', '2023-12-25 10:00:00', '2023-12-25 10:00:00', '1', '100', '380', '8', '1', '0', '1', '1', 'admin', 'admin');\" 2>&1")

# ============================================================
# 5. VERIFY ALL CTF ENDPOINTS ON A1
# ============================================================
print("\n" + "="*60)
print("5. CTF ENDPOINT VERIFICATION")
print("="*60)

tests = [
    ("Homepage", "http://localhost/"),
    ("Admin login", "http://localhost/admin.php"),
    ("A-1: /backup/", "http://localhost/backup/"),
    ("A-3: /config/database.php", "http://localhost/config/database.php"),
    ("Search page", "http://localhost/?p=/Index/search"),
    ("Search with keyword", "http://localhost/?p=/Index/search&keyword=test"),
    ("Content page", "http://localhost/?p=/Index/index&scode=notice"),
]

for name, url in tests:
    out, _, _ = run(c1, f"curl -s -o /dev/null -w '%{{http_code}}' '{url}'")
    status = out.strip()
    marker = "OK" if status == "200" else "WARN" if status in ["301","302"] else "FAIL"
    print(f"  [{marker}] {name}: HTTP {status}")

# Deep check: search page content
print("\n--- Search page body ---")
run(c1, "curl -s 'http://localhost/?p=/Index/search' | head -10")
print("\n--- Search results ---")
run(c1, "curl -s 'http://localhost/?p=/Index/search&keyword=安全' | head -20")

# Admin login test
print("\n--- Admin login test ---")
run(c1, "curl -s -X POST 'http://localhost/admin.php' -d 'username=admin&password=admin123&submit=1' -D - -o /dev/null 2>&1 | head -5")

# ============================================================
# 6. Check content listing
# ============================================================
print("\n" + "="*60)
print("6. CONTENT LISTING")
print("="*60)
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost --default-character-set=utf8mb4 -e 'SELECT id,scode,title FROM cms.ay_content;' 2>&1 | head -20")

c1.close()
c2.close()
print("\nDone!")
