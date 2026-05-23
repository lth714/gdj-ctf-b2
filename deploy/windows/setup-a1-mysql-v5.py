#!/usr/bin/env python3
"""Setup MySQL on A1 - clean approach."""
import paramiko
import base64

HOST = '192.168.100.10'
USER = 'gdadmin'
PASS = 'Gdadmin@123'
MYSQL_PASS = 'R00t@Mysql#2024'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS,
          timeout=10, look_for_keys=False, allow_agent=False)

def write_remote_file(path, content):
    """Write content to remote file using base64 to avoid ANY quoting issues."""
    b64 = base64.b64encode(content.encode()).decode()
    # Use sudo tee, feeding password via stdin, content via base64 pipe
    # The trick: { echo pass; echo b64 | base64 -d; } sends both to sudo -S tee
    cmd = f'{{ echo "{PASS}"; echo {b64} | base64 -d; }} | sudo -S tee "{path}" > /dev/null 2>&1'
    stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
    code = stdout.channel.recv_exit_status()
    return code

def sudorun(cmd, timeout=30):
    """Run a command with sudo, password on stdin."""
    full = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = c.exec_command(full, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

# ====== Step 1: Set root password ======
print("=== 1. Set root password ===")
sql1 = "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024';\nFLUSH PRIVILEGES;\n"
write_remote_file('/tmp/step1.sql', sql1)
out, err, code = sudorun('mysql -u root < /tmp/step1.sql 2>&1')
print(f"Result: out=[{out}], err=[{err}], code={code}")

# ====== Step 2: Check ======
print("\n=== 2. Check auth plugin ===")
sql2 = 'SELECT user, host, plugin FROM mysql.user;'
write_remote_file('/tmp/step2.sql', sql2)
out, err, code = sudorun('mysql -u root < /tmp/step2.sql 2>&1')
print(f"Auth:\n{out}")

# ====== Step 3: Import init_db ======
print("\n=== 3. Import database ===")
with open(r'E:\vibecoding\gdj_ctf\q1\news_dev-master\init_db.sql', 'r', encoding='utf-8') as f:
    init_sql = f.read()
print(f"SQL size: {len(init_sql)} bytes")
write_remote_file('/tmp/init.sql', init_sql)
out, err, code = sudorun('mysql -u root < /tmp/init.sql 2>&1')
print(f"Import: out=[{out}], err=[{err}], code={code}")

# ====== Step 4: Verify data ======
print("\n=== 4. Verify data ===")
for q, label in [
    ('SELECT COUNT(*) AS cnt FROM baixiu.users;', 'users'),
    ('SELECT COUNT(*) AS cnt FROM baixiu.posts;', 'posts'),
    ('SELECT COUNT(*) AS cnt FROM baixiu.categories;', 'categories'),
]:
    write_remote_file('/tmp/v.sql', q)
    out, err, code = sudorun('mysql -u root < /tmp/v.sql 2>&1')
    for line in out.split('\n'):
        line = line.strip()
        if line.isdigit():
            print(f"  {label}: {line}")
            break
    else:
        print(f"  {label}: NO DATA (raw={out[:60]})")

# ====== Step 5: Test PHP ======
print("\n=== 5. PHP connect test ===")
php_code = """<?php
$c = mysqli_connect('127.0.0.1', 'root', 'R00t@Mysql#2024', 'baixiu');
if ($c) { echo "PHP_OK\\n"; }
else { echo "FAIL: " . mysqli_connect_error() . "\\n"; }
"""
write_remote_file('/tmp/test.php', php_code)
out, err, code = sudorun('php8.1 /tmp/test.php 2>&1')
print(f"PHP: {out}")
if err:
    errs = [l for l in err.split('\n') if 'password for gdadmin' not in l and 'PHP Startup' not in l]
    if errs:
        print(f"  stderr: {' | '.join(errs[:3])}")

# Cleanup
sudorun('rm -f /tmp/step1.sql /tmp/step2.sql /tmp/init.sql /tmp/v.sql /tmp/test.php')
c.close()
print("\n=== DONE ===")
