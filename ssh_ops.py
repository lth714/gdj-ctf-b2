#!/usr/bin/env python
"""A2: Fix routing - check 500 error + add routes"""
import paramiko, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HOST = '192.168.100.30'
USER = 'gdadmin'
PASS = 'Gdadmin@123'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS,
          timeout=15, look_for_keys=False, allow_agent=False)

def run(cmd, timeout=30):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout, get_pty=True)
    stdout.channel.settimeout(timeout)
    stderr.channel.settimeout(timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

# Check the 500 error detail
print("=== 500 error for s=index/index/articles ===")
out, _, _ = run("curl -s 'http://localhost/index.php?s=index/index/articles' 2>&1")
for line in out.split('\n'):
    s = line.strip()
    if any(x in s.lower() for x in ['errorexception', 'in /var', 'line ', 'throw', 'fatal']):
        print(f"  {s[:150]}")

# CLI test
print("\n=== CLI PHP trace ===")
out, _, _ = run("cd /var/www/a2-media-cms/public && MYSQL_PASS='R00t@Mysql#2024' php index.php 'index/index/articles' 2>&1 | tail -15")
print(out[:800])

# Check PHP error log
print("\n=== FPM error log (last 10 lines) ===")
out, _, _ = run("echo 'Gdadmin@123' | sudo -S tail -10 /var/log/php7.4-fpm.log 2>/dev/null")
print(out[:500])

# Check Nginx error log
print("\n=== Nginx error log ===")
out, _, _ = run("echo 'Gdadmin@123' | sudo -S tail -5 /var/log/nginx/error.log 2>/dev/null")
print(out[:500])

c.close()
