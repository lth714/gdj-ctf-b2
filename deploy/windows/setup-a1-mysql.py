#!/usr/bin/env python3
"""Setup MySQL on A1: set root password, import database, verify."""
import paramiko
import base64

HOST = '192.168.100.10'
USER = 'gdadmin'
PASS = 'Gdadmin@123'
MYSQL_ROOT_PASS = 'R00t@Mysql#2024'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS,
          timeout=10, look_for_keys=False, allow_agent=False)

def sudo(cmd, timeout=30):
    full = f'echo "{PASS}" | sudo -S bash -c "{cmd}"'
    stdin, stdout, stderr = c.exec_command(full, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

def sudomysql(sql, timeout=30):
    """Run MySQL via sudo socket auth, using base64 to avoid quoting hell."""
    b64 = base64.b64encode(sql.encode()).decode()
    sudo(f'echo {b64} | base64 -d > /tmp/_sql.sql')
    stdin, stdout, stderr = c.exec_command(
        f'echo "{PASS}" | sudo -S mysql -u root < /tmp/_sql.sql 2>/dev/null',
        timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    sudo('rm -f /tmp/_sql.sql')
    return out, err

# ========== 1. Check current auth ==========
print("=== 1. Check root auth plugin ===")
out, err = sudomysql("SELECT user, host, plugin FROM mysql.user;")
print(f"Result: {out}")

# ========== 2. Set mysql_native_password ==========
print("\n=== 2. Setting mysql_native_password for root ===")
sql = f"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '{MYSQL_ROOT_PASS}'; FLUSH PRIVILEGES;"
out, err = sudomysql(sql)
if err:
    print(f"ALTER USER stderr: {err}")
else:
    print("ALTER USER: OK")

# ========== 3. Verify ==========
print("\n=== 3. Verify auth ===")
out, err = sudomysql("SELECT user, host, plugin FROM mysql.user;")
print(f"Result: {out}")

# ========== 4. Test password login ==========
print("\n=== 4. Test password login ===")
stdin, stdout, stderr = c.exec_command(
    f'mysql -u root -p{MYSQL_ROOT_PASS} -e "SELECT 1 AS pw_test;" 2>&1',
    timeout=10)
out = stdout.read().decode('utf-8', errors='replace').strip()
err = stderr.read().decode('utf-8', errors='replace').strip()
print(f"Password login: {out}")

# ========== 5. PHP connection test ==========
print("\n=== 5. PHP connection test ===")
php_code = """<?php
error_reporting(E_ALL);
require '/var/www/html/baixiu/config.php';
$conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS, DB_NAME);
if ($conn) {
    echo "PHP_CONNECT_OK\n";
    $r = mysqli_query($conn, "SELECT id, email, password FROM users");
    while ($row = mysqli_fetch_assoc($r)) {
        echo "User {$row['id']}: {$row['email']} / {$row['password']}\n";
    }
} else {
    echo "FAIL: " . mysqli_connect_error() . "\n";
}
"""
b64_php = base64.b64encode(php_code.encode()).decode()
sudo(f'echo {b64_php} | base64 -d > /tmp/test.php')
stdin, stdout, stderr = c.exec_command(
    f'echo "{PASS}" | sudo -S php8.1 /tmp/test.php 2>&1',
    timeout=10)
out = stdout.read().decode('utf-8', errors='replace').strip()
err = stderr.read().decode('utf-8', errors='replace').strip()
print(f"PHP output: {out}")
if err:
    # Filter out password prompt noise
    err_lines = [l for l in err.split('\n') if 'password for gdadmin' not in l]
    if err_lines:
        print(f"PHP stderr: {' | '.join(err_lines[:5])}")

# ========== 6. Verify database content ==========
print("\n=== 6. Verify database content ===")
out, err = sudomysql("USE baixiu; SELECT COUNT(*) AS users FROM users;")
print(f"Users: {out}")
out, err = sudomysql("USE baixiu; SELECT COUNT(*) AS posts FROM posts;")
print(f"Posts: {out}")
out, err = sudomysql("USE baixiu; SELECT COUNT(*) AS categories FROM categories;")
print(f"Categories: {out}")

c.close()
print("\n=== DONE ===")
