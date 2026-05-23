#!/usr/bin/env python3
"""Fix A1 PbootCMS: Import pbootcms_v324.sql into A2 MySQL via A2 localhost"""
import paramiko

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
# Step 1: SCP the SQL file from A1 to A2
# ============================================================
print("="*60)
print("1. SCP SQL FILE FROM A1 TO A2")
print("="*60)
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

# SCP from A1 to A2: A2 pulls from A1
# Use scp on A2 to pull the file from A1
cmd = "sshpass -p 'Gdadmin@123' scp -o StrictHostKeyChecking=no gdadmin@192.168.100.1:/var/www/cms/static/backup/sql/pbootcms_v324.sql /tmp/pbootcms_v324.sql 2>&1"
out, err, ec = run(c2, cmd, timeout=30)
print(f"SCP exit code: {ec}")

# ============================================================
# Step 2: Import SQL locally on A2 (using sudo mysql)
# ============================================================
print("\n" + "="*60)
print("2. IMPORT SQL INTO CMS DATABASE ON A2 LOCALHOST")
print("="*60)
# Check file arrived
run(c2, "wc -l /tmp/pbootcms_v324.sql 2>/dev/null || echo 'FILE_NOT_FOUND'")

# Pipe with sudo: gdadmin can sudo, so use bash -c with the full pipe
run(c2, "echo 'Gdadmin@123' | sudo -S bash -c 'mysql cms < /tmp/pbootcms_v324.sql' 2>&1", timeout=30)

# Also try the other small update SQL for good measure
run(c2, "sshpass -p 'Gdadmin@123' scp -o StrictHostKeyChecking=no gdadmin@192.168.100.1:/var/www/cms/static/backup/sql/mysql-3.2.4-update.sql /tmp/mysql-update.sql 2>&1", timeout=15)
run(c2, "echo 'Gdadmin@123' | sudo -S bash -c 'mysql cms < /tmp/mysql-update.sql 2>/dev/null; echo OK'", timeout=15)

# ============================================================
# Step 3: Verify tables on A2
# ============================================================
print("\n" + "="*60)
print("3. VERIFY CMS TABLES")
print("="*60)
run(c2, "echo 'Gdadmin@123' | sudo -S bash -c \"mysql -e 'SHOW TABLES FROM cms;'\" 2>&1")
run(c2, "echo 'Gdadmin@123' | sudo -S bash -c \"mysql -e 'SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema=\\\"cms\\\";'\" 2>&1")

# ============================================================
# Step 4: Test PbootCMS on A1 again
# ============================================================
print("\n" + "="*60)
print("4. TEST PBOOTCMS ON A1")
print("="*60)
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c1, "curl -s http://localhost/ | head -20")
run(c1, "curl -s http://localhost/?p=1 | head -20")

c1.close()
c2.close()
print("\nDone!")
