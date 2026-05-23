#!/usr/bin/env python3
"""Setup MySQL on A1 - write SQL via SFTP, bypass bash escaping."""
import paramiko
from io import BytesIO

HOST = '192.168.100.10'
USER = 'gdadmin'
PASS = 'Gdadmin@123'
MYSQL_PASS = 'R00t@Mysql#2024'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS,
          timeout=10, look_for_keys=False, allow_agent=False)

sftp = c.open_sftp()

def sudo(cmd, timeout=30):
    full = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = c.exec_command(full, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

# Step 1: Write ALTER USER SQL via SFTP (no bash escaping!)
print("=== 1. Setting root password ===")
sql = f"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '{MYSQL_PASS}';\nFLUSH PRIVILEGES;\n"
sftp.putfo(BytesIO(sql.encode()), '/tmp/setpass.sql')

out, err, code = sudo('mysql -u root < /tmp/setpass.sql 2>&1')
print(f"ALTER USER: out=[{out}], err=[{err}], code={code}")

# Step 2: Check auth
print("\n=== 2. Check auth ===")
out, err, code = sudo("mysql -u root -e 'SELECT user, host, plugin FROM mysql.user;' 2>&1")
print(f"Result:\n{out}")

# Step 3: Upload init_db.sql via SFTP
print("\n=== 3. Importing init_db.sql ===")
with open(r'E:\vibecoding\gdj_ctf\q1\news_dev-master\init_db.sql', 'r', encoding='utf-8') as f:
    init_sql = f.read()
sftp.putfo(BytesIO(init_sql.encode()), '/tmp/init_db.sql')

out, err, code = sudo('mysql -u root < /tmp/init_db.sql 2>&1')
print(f"Import: out=[{out}], err=[{err}], code={code}")

# Step 4: Test password login
print("\n=== 4. Test password login ===")
sql2 = f"SELECT 1 AS password_test;"
sftp.putfo(BytesIO(sql2.encode()), '/tmp/test_pw.sql')
out, err, code = sudo(f"mysql -u root -p'{MYSQL_PASS}' < /tmp/test_pw.sql 2>&1")
print(f"Password login: out=[{out}], err=[{err}]")

# Step 5: PHP test - write via SFTP
print("\n=== 5. PHP connection test ===")
php = """<?php
error_reporting(E_ALL);
$conn = mysqli_connect('127.0.0.1', 'root', 'R00t@Mysql#2024', 'baixiu');
if ($conn) {
    echo "PHP_OK\\n";
    $r = mysqli_query($conn, "SELECT id, email FROM users");
    while ($row = mysqli_fetch_assoc($r)) {
        echo "User: {$row['id']} {$row['email']}\\n";
    }
} else {
    echo "FAIL: " . mysqli_connect_error() . "\\n";
}
"""
sftp.putfo(BytesIO(php.encode()), '/tmp/test.php')
out, err, code = sudo('php8.1 /tmp/test.php 2>&1')
print(f"PHP: {out}")
if err:
    errs = [l for l in err.split('\n') if 'password for gdadmin' not in l]
    if errs:
        print(f"  stderr: {' | '.join(errs[:3])}")

# Step 6: Verify data
print("\n=== 6. Verify database ===")
for q, label in [
    ('SELECT COUNT(*) AS cnt FROM baixiu.users;', 'users'),
    ('SELECT COUNT(*) AS cnt FROM baixiu.posts;', 'posts'),
    ('SELECT COUNT(*) AS cnt FROM baixiu.categories;', 'categories'),
]:
    sftp.putfo(BytesIO(q.encode()), '/tmp/_q.sql')
    out, err, code = sudo('mysql -u root < /tmp/_q.sql 2>&1')
    # Parse number from output
    lines = [l for l in out.split('\n') if l.strip().isdigit()]
    val = lines[0] if lines else 'unknown'
    print(f"{label}: {val}")

# Cleanup
sudo('rm -f /tmp/setpass.sql /tmp/init_db.sql /tmp/test.php /tmp/test_pw.sql /tmp/_q.sql')
sftp.close()
c.close()
print("\n=== DONE ===")
