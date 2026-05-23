#!/usr/bin/env python3
"""Setup MySQL on A1 - use sudo tee to write SQL files."""
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

def write_file(path, content):
    """Write file via base64 + sudo tee. Avoids all bash quoting issues."""
    b64 = base64.b64encode(content.encode()).decode()
    cmd = f'echo {b64} | base64 -d | echo "{PASS}" | sudo -S tee {path} > /dev/null'
    stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
    # tee should succeed
    return stdout.channel.recv_exit_status()

def sudo_exec(cmd, timeout=30):
    """Execute command via sudo with password."""
    full = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = c.exec_command(full, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

# Step 1: Set root password
print("=== 1. Setting root password ===")
sql = f"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '{MYSQL_PASS}';\nFLUSH PRIVILEGES;\n"
write_file('/tmp/setpass.sql', sql)
out, err, code = sudo_exec('mysql -u root < /tmp/setpass.sql 2>&1')
print(f"ALTER USER: out=[{out}], err=[{err}], code={code}")

# Step 2: Check auth
print("\n=== 2. Check auth ===")
sql2 = 'SELECT user, host, plugin FROM mysql.user;'
write_file('/tmp/chk.sql', sql2)
out, err, code = sudo_exec('mysql -u root < /tmp/chk.sql 2>&1')
print(f"Auth:\n{out}")

# Step 3: Import database
print("\n=== 3. Importing init_db.sql ===")
with open(r'E:\vibecoding\gdj_ctf\q1\news_dev-master\init_db.sql', 'r', encoding='utf-8') as f:
    init_sql = f.read()
write_file('/tmp/init_db.sql', init_sql)
out, err, code = sudo_exec('mysql -u root < /tmp/init_db.sql 2>&1')
print(f"Import: out=[{out}], err=[{err}], code={code}")

# Step 4: Test password login
print("\n=== 4. Test password login ===")
# The # in password is a comment in bash. Use a SQL file.
sql3 = 'SELECT 1 AS pw_test;'
write_file('/tmp/pw.sql', sql3)
# Use mysql with password via a wrapper
wrapper = f'mysql -u root -p"{MYSQL_PASS}" < /tmp/pw.sql 2>&1'
write_file('/tmp/pw.sh', wrapper)
out, err, code = sudo_exec('bash /tmp/pw.sh 2>&1')
# Note: # in password causes issues even here. Let me try single quotes.
wrapper2 = f"mysql -u root -p'{MYSQL_PASS}' < /tmp/pw.sql 2>&1"
write_file('/tmp/pw.sh', wrapper2)
out, err, code = sudo_exec('bash /tmp/pw.sh 2>&1')
print(f"Password login: out=[{out}], err=[{err}]")

# Step 5: Test PHP
print("\n=== 5. PHP test ===")
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
write_file('/tmp/test.php', php)
out, err, code = sudo_exec('php8.1 /tmp/test.php 2>&1')
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
    write_file('/tmp/q.sql', q)
    out, err, code = sudo_exec('mysql -u root < /tmp/q.sql 2>&1')
    # Find number in output
    for line in out.split('\n'):
        cleaned = line.strip()
        if cleaned.isdigit():
            print(f"{label}: {cleaned}")
            break
    else:
        print(f"{label}: parse fail, raw=[{out[:80]}]")

# Cleanup
sudo_exec('rm -f /tmp/setpass.sql /tmp/chk.sql /tmp/init_db.sql /tmp/pw.sql /tmp/pw.sh /tmp/test.php /tmp/q.sql')
c.close()
print("\n=== DONE ===")
