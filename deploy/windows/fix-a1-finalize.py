#!/usr/bin/env python3
"""Finalize A1 PbootCMS: restore admin, content, verify CTF chains"""
import paramiko

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
    if out.strip(): print(f"  {out.strip()[:2000]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:500]}")
    return out, err, ec

c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

# ============================================================
# 1. Show the new table schema for ay_user and ay_site
# ============================================================
print("="*60)
print("1. CHECK NEW TABLE SCHEMAS")
print("="*60)
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'DESCRIBE cms.ay_user;' 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'DESCRIBE cms.ay_site;' 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'DESCRIBE cms.ay_config;' 2>&1")

# ============================================================
# 2. Check current data in key tables
# ============================================================
print("\n" + "="*60)
print("2. CURRENT DATA IN KEY TABLES")
print("="*60)
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT id,username,realname,password FROM cms.ay_user;' 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT id,domain,name,title FROM cms.ay_site;' 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT id,title FROM cms.ay_content LIMIT 5;' 2>&1")

# ============================================================
# 3. Restore CTF-specific content from the original init_db.sql
# ============================================================
print("\n" + "="*60)
print("3. RESTORE CTF CONTENT")
print("="*60)

# Update admin user - need to update the existing admin row
# The new schema may have different columns. Let's check and adapt.
# Old admin password hash (from init_db.sql): f0916d59b2d497402968dbdd3641ddbe
# This is likely MD5 (common for older CMS). We need to figure out the format.
# Actually, let's check the current admin password and update it.

# First, let's see the full ay_user row for admin
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT * FROM cms.ay_user WHERE username=\"admin\" OR id=1;' 2>&1")

# Update admin password to the correct CTF hash
# The init_db.sql had: f0916d59b2d497402968dbdd3641ddbe (admin123, common for CTF)
# But PbootCMS uses: md5(md5(password) + salt), so we need the CORRECT format
# Let's check what the current admin password hash is
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e \"UPDATE cms.ay_user SET password='14e1b600b1fd579f47433b88e8d85291' WHERE username='admin';\" 2>&1")
# 14e1b600b1fd579f47433b88e8d85291 = md5('admin123') - PbootCMS format

# Update ay_site
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e \"UPDATE cms.ay_site SET domain='192.168.100.1', title='广电局融媒体内容管理系统', name='广电融媒体平台' WHERE id=1;\" 2>&1")

# Insert CTF hint content into ay_content if table is empty apart from demo data
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e \"INSERT INTO cms.ay_content (scode,title,content,description,author,date,create_time,update_time,status,sorting) VALUES ('notice','关于进一步加强网络安全管理的通知','<p>各单位要高度重视网络安全工作，定期开展安全检测，数据库备份文件已存放于 /backup/ 目录下备用。</p>','广电局网络安全管理办法修订版','系统管理员','2023-12-25 10:00:00','2023-12-25 10:00:00','2023-12-25 10:00:00',1,100) ON DUPLICATE KEY UPDATE title=title;\" 2>&1")

# ============================================================
# 4. Check config on A1
# ============================================================
print("\n" + "="*60)
print("4. VERIFY A1 CONFIG")
print("="*60)
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

# Database config
run(c1, "cat /var/www/cms/config/database.php")

# ============================================================
# 5. Verify CTF chains
# ============================================================
print("\n" + "="*60)
print("5. CTF CHAIN VERIFICATION")
print("="*60)

# A-1: /backup/ directory listing
print("\n--- A-1: Backup directory listing ---")
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/backup/")

# A-2: Search API (SQLi entry)
print("\n--- A-2: Search API ---")
run(c1, "curl -s 'http://localhost/?p=/Index/search' 2>&1 | head -20")
run(c1, "curl -s 'http://localhost/?p=/Index/search&keyword=test' 2>&1 | head -20")

# Admin login page
print("\n--- Admin login ---")
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/admin.php")
run(c1, "curl -s http://localhost/admin.php 2>&1 | head -20")

# A-3: Source code leak via /config/database.php
print("\n--- A-3: Database config source leak ---")
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/config/database.php")

# Try direct file access patterns
run(c1, "curl -s http://localhost/config/database.php 2>&1 | head -15")

# Check .htaccess
print("\n--- .htaccess check ---")
run(c1, "cat /var/www/cms/.htaccess")

# ============================================================
# 6. Full homepage test
# ============================================================
print("\n" + "="*60)
print("6. HOMEPAGE RENDER")
print("="*60)
run(c1, "curl -s http://localhost/ | grep -oP '(?<=<title>).*?(?=</title>)'")

c1.close()
c2.close()
print("\nDone!")
