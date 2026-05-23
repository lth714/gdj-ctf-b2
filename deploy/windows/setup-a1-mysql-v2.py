#!/usr/bin/env python3
"""Setup MySQL on A1 - simpler approach without base64."""
import paramiko

HOST = '192.168.100.10'
USER = 'gdadmin'
PASS = 'Gdadmin@123'
MYSQL_PASS = 'R00t@Mysql#2024'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS,
          timeout=10, look_for_keys=False, allow_agent=False)

def sudo(cmd, timeout=30):
    full = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = c.exec_command(full, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

# Step 1: Write SQL file for ALTER USER
print("=== 1. Setting root password ===")
sudo(f"""cat > /tmp/setpass.sql << 'EOF'
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '{MYSQL_PASS}';
FLUSH PRIVILEGES;
EOF""")

out, err, code = sudo('mysql -u root < /tmp/setpass.sql 2>&1')
print(f"ALTER USER: out=[{out}], err=[{err}], code={code}")

# Step 2: Check auth plugin
print("\n=== 2. Check auth plugin ===")
out, err, code = sudo("mysql -u root -e \"SELECT user, host, plugin FROM mysql.user;\" 2>&1")
print(f"Users: {out}")

# Step 3: Re-import database (just in case)
print("\n=== 3. Re-import init_db.sql ===")
with open(r'E:\vibecoding\gdj_ctf\q1\news_dev-master\init_db.sql', 'r') as f:
    sql_content = f.read()

# Write init_db.sql to remote
sftp = c.open_sftp()
with sftp.file('/tmp/init_db.sql', 'w') as f:
    f.write(sql_content)
sftp.close()

out, err, code = sudo('mysql -u root < /tmp/init_db.sql 2>&1')
print(f"Import: out=[{out}], err=[{err}], code={code}")

# Step 4: Test with password
print("\n=== 4. Test password login ===")
escape_pass = MYSQL_PASS.replace('#', '\\#').replace('!', '\\!')
out, err, code = sudo(f"mysql -u root -p'{MYSQL_PASS}' -e 'SELECT 1 AS test;' 2>&1")
print(f"Password login: out=[{out}], err=[{err}]")

# Step 5: PHP test
print("\n=== 5. PHP connection test ===")
sudo("""cat > /tmp/test.php << 'PHPEOF'
<?php
error_reporting(E_ALL);
$conn = mysqli_connect('127.0.0.1', 'root', 'R00t@Mysql#2024', 'baixiu');
if ($conn) {
    echo "PHP_OK\n";
    $r = mysqli_query($conn, "SELECT id, email FROM users");
    while ($row = mysqli_fetch_assoc($r)) {
        echo "User: {$row['id']} {$row['email']}\n";
    }
} else {
    echo "FAIL: " . mysqli_connect_error() . "\n";
}
PHPEOF""")

out, err, code = sudo('php8.1 /tmp/test.php 2>&1')
print(f"PHP: out=[{out}]")
if err:
    errs = [l for l in err.split('\n') if 'password for gdadmin' not in l]
    if errs:
        print(f"  stderr: {' | '.join(errs[:3])}")

# Step 6: Verify data
print("\n=== 6. Verify database content ===")
for q, label in [
    ('SELECT COUNT(*) FROM users;', 'users'),
    ('SELECT COUNT(*) FROM posts;', 'posts'),
    ('SELECT COUNT(*) FROM categories;', 'categories'),
]:
    out, err, code = sudo(f'mysql -u root baixiu -e "{q}" 2>&1')
    print(f"{label}: {out}")

# Cleanup
sudo('rm -f /tmp/setpass.sql /tmp/init_db.sql /tmp/test.php')

c.close()
print("\n=== DONE ===")
