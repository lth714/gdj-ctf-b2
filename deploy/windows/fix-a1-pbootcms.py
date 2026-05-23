#!/usr/bin/env python3
"""Fix A1 PbootCMS: import missing SQL tables into cms database on A2"""
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
# Step 1: Check A1 backup SQL files
# ============================================================
print("="*60)
print("1. LIST BACKUP SQL FILES ON A1")
print("="*60)
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

run(c1, "ls -la /var/www/cms/static/backup/sql/")
run(c1, "wc -l /var/www/cms/static/backup/sql/pbootcms_v324.sql")
run(c1, "head -30 /var/www/cms/static/backup/sql/pbootcms_v324.sql")

# ============================================================
# Step 2: Import the SQL schema from A1 into A2 MySQL
# ============================================================
print("\n" + "="*60)
print("2. IMPORT SQL INTO CMS DATABASE ON A2")
print("="*60)
# Pipe the SQL file from A1 directly to MySQL on A2
cmd = "mysql -h 192.168.100.2 -u root -p'R00t@Mysql#2024' cms < /var/www/cms/static/backup/sql/pbootcms_v324.sql 2>&1"
out, err, ec = run(c1, cmd, timeout=30)
print(f"\nImport exit code: {ec}")

# ============================================================
# Step 3: Verify tables after import
# ============================================================
print("\n" + "="*60)
print("3. VERIFY CMS TABLES AFTER IMPORT")
print("="*60)
c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

run(c2, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM cms;' 2>&1")
run(c2, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema=\"cms\";' 2>&1")
run(c2, "mysql -u root -p'R00t@Mysql#2024' -e 'DESCRIBE cms.ay_config;' 2>&1 | head -30")

# ============================================================
# Step 4: Set domain in ay_site table
# ============================================================
print("\n" + "="*60)
print("4. FIX ay_site DOMAIN")
print("="*60)
run(c2, "mysql -u root -p'R00t@Mysql#2024' -e \"SELECT * FROM cms.ay_site;\" 2>&1")
run(c2, "mysql -u root -p'R00t@Mysql#2024' -e \"UPDATE cms.ay_site SET domain='192.168.100.1' WHERE id=1;\" 2>&1")
run(c2, "mysql -u root -p'R00t@Mysql#2024' -e \"SELECT id, domain FROM cms.ay_site;\" 2>&1")

# ============================================================
# Step 5: Test PbootCMS on A1
# ============================================================
print("\n" + "="*60)
print("5. TEST PBOOTCMS")
print("="*60)
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c1, "curl -s http://localhost/ | head -30")
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/backup/")
run(c1, "curl -s http://localhost/?p=1 | head -30")

c1.close()
c2.close()
print("\nDone!")
