#!/usr/bin/env python3
"""Fix A1 PbootCMS: Transfer SQL via SFTP, import on A2 via sudo mysql"""
import paramiko
import io

user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(ssh, cmd, sudo=False, timeout=30):
    if sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:150]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:2000]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:500]}")
    return out, err, ec

# ============================================================
# Step 1: Read SQL file from A1 via SFTP
# ============================================================
print("="*60)
print("1. READ SQL FILE FROM A1 VIA SFTP")
print("="*60)
t1 = paramiko.Transport(('192.168.100.1', 22))
t1.connect(username=user, password=pwd)
sftp1 = paramiko.SFTPClient.from_transport(t1)

with sftp1.open('/var/www/cms/static/backup/sql/pbootcms_v324.sql', 'r') as f:
    sql_content = f.read()
print(f"Read {len(sql_content)} bytes from A1 pbootcms_v324.sql")

# Also read the update SQL
with sftp1.open('/var/www/cms/static/backup/sql/mysql-3.2.4-update.sql', 'r') as f:
    update_sql = f.read()
print(f"Read {len(update_sql)} bytes from A1 mysql-3.2.4-update.sql")

sftp1.close()
t1.close()

# ============================================================
# Step 2: Write SQL file to A2 via SFTP
# ============================================================
print("\n" + "="*60)
print("2. WRITE SQL FILE TO A2 VIA SFTP")
print("="*60)
t2 = paramiko.Transport(('192.168.100.2', 22))
t2.connect(username=user, password=pwd)
sftp2 = paramiko.SFTPClient.from_transport(t2)

with sftp2.open('/tmp/pbootcms_v324.sql', 'w') as f:
    f.write(sql_content)
print("Written pbootcms_v324.sql to A2 /tmp/")

with sftp2.open('/tmp/mysql-update.sql', 'w') as f:
    f.write(update_sql)
print("Written mysql-update.sql to A2 /tmp/")

# Verify
run_dict = {}
c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

run(c2, "ls -la /tmp/pbootcms_v324.sql /tmp/mysql-update.sql")
run(c2, "head -5 /tmp/pbootcms_v324.sql")

# ============================================================
# Step 3: Import SQL on A2 using different methods
# ============================================================
print("\n" + "="*60)
print("3. IMPORT SQL ON A2")
print("="*60)

# Method 1: sudo -i to get root shell, then mysql
print("\n--- Method 1: sudo -i + mysql ---")
out, err, ec = run(c2, "echo 'Gdadmin@123' | sudo -S -i mysql cms < /tmp/pbootcms_v324.sql 2>&1; echo EXIT:$?")
print(f"Method 1 exit: {ec}")

# Method 2: Check if we can use sudo mysql directly with socket auth
print("\n--- Check MySQL auth method ---")
run(c2, "echo 'Gdadmin@123' | sudo -S head -5 /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null")
run(c2, "echo 'Gdadmin@123' | sudo -S grep -E 'user|password|socket|auth' /root/.my.cnf 2>/dev/null; echo '---'")
run(c2, "echo 'Gdadmin@123' | sudo -S cat /root/.my.cnf 2>/dev/null || echo 'NO_ROOT_MYCNF'")

# Method 3: Use python to import via MySQL connector if installed
print("\n--- Method 3: Check mysql connector ---")
run(c2, "python3 -c 'import mysql.connector; print(\"OK\")' 2>&1 || echo 'NO_CONNECTOR'")

# Method 4: Try su - (but this needs TTY)
# Method 5: Try auth_socket explicitly
print("\n--- Method 5: mysql with --protocol=SOCKET ---")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql --protocol=SOCKET -e 'SHOW TABLES FROM cms;' 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql --defaults-file=/dev/null -e 'SHOW TABLES FROM cms;' 2>&1")

# Try with explicit socket path
print("\n--- Method 6: explicit socket path ---")
run(c2, "echo 'Gdadmin@123' | sudo -S ls /var/run/mysqld/ 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -S /var/run/mysqld/mysqld.sock -e 'SHOW TABLES FROM cms;' 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -S /var/run/mysqld/mysqld.sock cms < /tmp/pbootcms_v324.sql 2>&1; echo IMPORT_EXIT:$?")

sftp2.close()
t2.close()
c2.close()
print("\nDone!")
