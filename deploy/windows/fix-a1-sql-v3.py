#!/usr/bin/env python3
"""Fix A1 PbootCMS: Import SQL on A2 using mysql root password"""
import paramiko

user = 'gdadmin'
pwd = 'Gdadmin@123'
mysql_pwd = 'R00t@Mysql#2024'

def run(ssh, cmd, timeout=30):
    print(f">>> {cmd[:150]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:2000]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:500]}")
    return out, err, ec

c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

# Check if SQL file exists from previous SFTP transfer
print("="*60)
print("1. CHECK SQL FILE ON A2")
print("="*60)
run(c2, "ls -la /tmp/pbootcms_v324.sql")

# Try different MySQL auth approaches
print("\n" + "="*60)
print("2. TEST MYSQL ROOT AUTH")
print("="*60)

# Check MySQL plugin for root
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -e \"SELECT user, host, plugin FROM mysql.user WHERE user='root';\" 2>&1")

# Try direct mysql with password - careful with special chars
# Use a heredoc approach or write to .my.cnf
print("\n--- Create temp my.cnf ---")
run(c2, f"cat > /tmp/.my.cnf << 'MYEOF'\n[client]\nuser=root\npassword={mysql_pwd}\nMYEOF")
run(c2, "chmod 600 /tmp/.my.cnf")
run(c2, "cat /tmp/.my.cnf")

# Now try mysql with defaults-file
print("\n--- mysql with defaults-file ---")
run(c2, "mysql --defaults-file=/tmp/.my.cnf -e 'SHOW TABLES FROM cms;' 2>&1")
run(c2, "mysql --defaults-file=/tmp/.my.cnf -e 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=\"cms\";' 2>&1")

# Import the SQL
print("\n" + "="*60)
print("3. IMPORT SQL")
print("="*60)
run(c2, "mysql --defaults-file=/tmp/.my.cnf cms < /tmp/pbootcms_v324.sql 2>&1; echo IMPORT_EXIT:$?")

# Verify
print("\n" + "="*60)
print("4. VERIFY TABLES")
print("="*60)
run(c2, "mysql --defaults-file=/tmp/.my.cnf -e 'SHOW TABLES FROM cms;' 2>&1")
run(c2, "mysql --defaults-file=/tmp/.my.cnf -e 'SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_schema=\"cms\";' 2>&1")

# Clean up
run(c2, "rm -f /tmp/.my.cnf")

# Test from A1
print("\n" + "="*60)
print("5. TEST PBOOTCMS ON A1")
print("="*60)
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c1, "curl -s http://localhost/ | head -25")

c1.close()
c2.close()
print("\nDone!")
