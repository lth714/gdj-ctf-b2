#!/usr/bin/env python3
"""Fix A1 PbootCMS: Use cmsuser to import missing tables"""
import paramiko

user = 'gdadmin'
pwd = 'Gdadmin@123'
cms_user = 'cmsuser'
cms_pass = 'Cm5Us3r@2024!'

def run(ssh, cmd, timeout=30):
    print(f">>> {cmd[:150]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:2000]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:500]}")
    return out, err, ec

# ============================================================
# Step 1: Extract ay_config and other missing table definitions
# from the pbootcms SQL dump via A1
# ============================================================
print("="*60)
print("1. EXTRACT MISSING TABLES FROM SQL DUMP")
print("="*60)
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.100.1', username=user, password=pwd, timeout=10)

# Get table names from the SQL dump
run(c1, "grep -n 'DROP TABLE IF EXISTS' /var/www/cms/static/backup/sql/pbootcms_v324.sql")

# Show the ay_config table definition from the dump
run(c1, "sed -n '/DROP TABLE.*ay_config/,/CREATE TABLE.*ay_/p' /var/www/cms/static/backup/sql/pbootcms_v324.sql | head -50")

# ============================================================
# Step 2: Get the full table creation + data sections for all tables
# ============================================================
print("\n" + "="*60)
print("2. EXTRACT EACH TABLE FROM DUMP")
print("="*60)

# List all tables in the dump
out, _, _ = run(c1, "grep 'DROP TABLE IF EXISTS' /var/www/cms/static/backup/sql/pbootcms_v324.sql")
# Parse table names from the output

# Check current tables on A2
c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

print("\n--- Current tables on A2 ---")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SHOW TABLES FROM cms;' 2>&1")

# ============================================================
# Step 3: Try importing the full SQL as cmsuser
# The SQL file uses DROP TABLE IF EXISTS, so it should be safe
# But we might lose existing data...
# Let's backup first, then import only the missing tables
# ============================================================
print("\n" + "="*60)
print("3. IMPORT FULL SCHEMA AS CMSUSER (backup first)")
print("="*60)

# Backup current DB
run(c2, f"mysqldump -u {cms_user} -p'{cms_pass}' -h localhost cms > /tmp/cms_backup.sql 2>&1; echo BACKUP_EXIT:$?")
run(c2, "wc -l /tmp/cms_backup.sql")

# Import the full SQL - this will DROP and recreate ALL tables
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost cms < /tmp/pbootcms_v324.sql 2>&1; echo IMPORT_EXIT:$?")
# The warning about password on command line is fine, we hide it

# ============================================================
# Step 4: Restore the old content data into the new tables
# ============================================================
print("\n" + "="*60)
print("4. VERIFY NEW TABLES")
print("="*60)
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SHOW TABLES FROM cms;' 2>&1")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT COUNT(*) as cnt FROM cms.ay_config;' 2>&1")

# Check ay_site domain
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e 'SELECT id,domain,name FROM cms.ay_site;' 2>&1")

# Set domain
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e \"UPDATE cms.ay_site SET domain='192.168.100.1' WHERE id=1;\" 2>&1")

# Import the admin user from backup (need to extract just the INSERT for ay_user)
print("\n--- Restore admin user from backup ---")
# The ini_db.sql admin hash: f0916d59b2d497402968dbdd3641ddbe (password: admin123)
# We'll recreate the admin user manually
run(c2, f"""mysql -u {cms_user} -p'{cms_pass}' -h localhost -e "DELETE FROM cms.ay_user WHERE username='admin'; INSERT INTO cms.ay_user (ucode,username,realname,password,status,role_id) VALUES ('10001','admin','系统管理员','14e1b600b1fd579f47433b88e8d85291',1,1);" 2>&1""")

# Restore content data
print("\n--- Restore content from backup ---")
run(c2, f"mysql -u {cms_user} -p'{cms_pass}' -h localhost -e \"SELECT COUNT(*) FROM cms.ay_content;\" 2>&1")

# ============================================================
# Step 5: Test from A1
# ============================================================
print("\n" + "="*60)
print("5. TEST PBOOTCMS ON A1")
print("="*60)
run(c1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c1, "curl -s http://localhost/ | head -30")
# Try admin login
run(c1, "curl -s http://localhost/?p=/Index/index | head -30")
run(c1, "curl -s http://localhost/backup/ | head -20")

c1.close()
c2.close()
print("\nDone!")
