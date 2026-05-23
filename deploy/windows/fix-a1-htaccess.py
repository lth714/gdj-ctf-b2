#!/usr/bin/env python3
"""Fix A1 .htaccess (write via SFTP to avoid bash $1 expansion), then restore all CTF data"""
import paramiko
import hashlib

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

# ============================================================
# 1. FIX .htaccess via SFTP (avoid bash $1 expansion)
# ============================================================
print("="*60)
print("1. FIX .htaccess VIA SFTP")
print("="*60)

htaccess_content = """RewriteEngine On
RewriteBase /
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ index.php?p=$1 [QSA,L]
"""

t1 = paramiko.Transport(('192.168.100.1', 22))
t1.connect(username=user, password=pwd)
sftp = paramiko.SFTPClient.from_transport(t1)

# Write to /tmp first, then sudo cp to destination
with sftp.open('/tmp/htaccess_fixed', 'w') as f:
    f.write(htaccess_content)
print("Written htaccess_fixed to /tmp/")

sftp.close()
t1.close()

# Now move it to the right place
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

run(c1, "echo 'Gdadmin@123' | sudo -S cp /tmp/htaccess_fixed /var/www/cms/.htaccess")
run(c1, "echo 'Gdadmin@123' | sudo -S chown www-data:www-data /var/www/cms/.htaccess")
run(c1, "echo 'Gdadmin@123' | sudo -S chmod 644 /var/www/cms/.htaccess")

# Verify with cat -A (shows all chars including $)
run(c1, "cat -A /var/www/cms/.htaccess")

# ============================================================
# 2. Compute admin password hash and insert user
# ============================================================
print("\n" + "="*60)
print("2. RESTORE ADMIN USER")
print("="*60)

# PbootCMS uses md5(md5(password)) format
# Let's confirm by checking the source or computing
admin_pass = 'admin123'
hash1 = hashlib.md5(admin_pass.encode()).hexdigest()
hash2 = hashlib.md5(hash1.encode()).hexdigest()
print(f"md5('admin123') = {hash1}")
print(f"md5(md5('admin123')) = {hash2}")

# Also compute the init_db.sql hash format to compare
# f0916d59b2d497402968dbdd3641ddbe - what is this?
# Let's try: plain md5 or md5(md5) or sha256

# Insert admin user with proper hash
c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

# Check ay_user schema more carefully
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE table_schema=\"cms\" AND table_name=\"ay_user\" ORDER BY ORDINAL_POSITION;' 2>&1")

# Insert admin user - need all NOT NULL columns without defaults
# From schema: id(AI), ucode, username, realname, password, status, login_count, last_login_ip, create_user, update_user, create_time, update_time
sql = f"""INSERT INTO cms.ay_user (ucode, username, realname, password, status, login_count, last_login_ip, create_user, update_user, create_time, update_time)
VALUES ('10001', 'admin', '系统管理员', '{hash2}', '1', 0, '0', 'admin', 'admin', NOW(), NOW())
ON DUPLICATE KEY UPDATE password='{hash2}'"""

# Build the mysql command - use heredoc to avoid bash escaping issues
cmd = f"mysql -u {cms_user} -p'{cms_pass}' -h localhost << 'SQLEOF'\nDELETE FROM cms.ay_user WHERE username='admin';\nINSERT INTO cms.ay_user (ucode, username, realname, password, status, login_count, last_login_ip, create_user, update_user, create_time, update_time) VALUES ('10001', 'admin', '系统管理员', '{hash2}', '1', 0, '0', 'admin', 'admin', NOW(), NOW());\nSQLEOF"
run(c2, cmd)

# Verify
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT id,username,realname,password FROM cms.ay_user;' 2>&1")

# ============================================================
# 3. Fix ay_site domain and title
# ============================================================
print("\n" + "="*60)
print("3. FIX AY_SITE")
print("="*60)
# New schema columns: id, acode, title, subtitle, domain, logo, keywords, description, icp, theme, statistical, copyright
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT * FROM cms.ay_site;' 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e \"UPDATE cms.ay_site SET domain='192.168.100.1', title='广电局融媒体内容管理系统', subtitle='广电融媒体平台' WHERE id=1;\" 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT id,acode,title,domain FROM cms.ay_site;' 2>&1")

# ============================================================
# 4. Insert CTF-specific content
# ============================================================
print("\n" + "="*60)
print("4. INSERT CTF CONTENT")
print("="*60)

# Check ay_content columns
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE table_schema=\"cms\" AND table_name=\"ay_content\" ORDER BY ORDINAL_POSITION;' 2>&1")

# The new schema has acode field. Let's insert with all required fields.
# We'll try a simple insert to see what's required
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost << 'SQLEOF2'\nINSERT INTO cms.ay_content (acode, scode, title, content, description, author, date, create_time, update_time, status, sorting, visits, likes, oppose, istop, isrecommend, isheadline, create_user, update_user)\nVALUES ('1', 'notice', '关于进一步加强网络安全管理的通知', '<p>各单位要高度重视网络安全工作，定期开展安全检测，数据库备份文件已存放于 /backup/ 目录下备用。</p>', '广电局网络安全管理办法修订版', '系统管理员', '2023-12-25 10:00:00', '2023-12-25 10:00:00', '2023-12-25 10:00:00', '1', '100', '380', '8', '1', '0', '1', '1', 'admin', 'admin');\nSQLEOF2")

# ============================================================
# 5. VERIFY ALL CTF ENDPOINTS
# ============================================================
print("\n" + "="*60)
print("5. VERIFY CTF ENDPOINTS")
print("="*60)

# Homepage
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c1, "curl -s http://localhost/ | grep -oP '(?<=<title>).*?(?=</title>)'")

# Inner pages (should work now with fixed .htaccess)
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/?p=/Index/search")

# Admin login
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/admin.php")

# A-1: Backup listing
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/backup/")

# A-3: Source code leak (config/database.php)
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/config/database.php")

# Test admin login
print("\n--- Test admin login ---")
run(c1, "curl -s -X POST http://localhost/admin.php -d 'username=admin&password=admin123&submit=1' -o /dev/null -w '%{http_code}\n%{redirect_url}' 2>&1")

c1.close()
c2.close()
print("\nDone!")
