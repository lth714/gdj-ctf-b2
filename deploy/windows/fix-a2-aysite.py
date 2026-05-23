#!/usr/bin/env python3
"""Fix ay_site table + complete PbootCMS schema on VM-A2 and clear cache on VM-A1."""
import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

A1_IP = '192.168.100.1'
A2_IP = '192.168.100.2'
PASSWORD = 'Gdadmin@123'
BASE = 'E:/vibecoding/gdj_ctf'


def ssh_cmd(ssh, cmd, timeout=30, sudo=False):
    if sudo:
        cmd = 'echo "%s" | sudo -S %s' % (PASSWORD, cmd)
    print("  >>> %s..." % cmd[:150])
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    if sudo:
        stdin.write(PASSWORD + '\n')
        stdin.flush()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        for line in out.strip().split('\n')[:10]:
            print("      " + line)
    if err.strip() and ec != 0:
        print("  [err] " + err.strip()[:300])
    return out, err, ec


print("[1] Connecting to VMs...")
a1 = paramiko.SSHClient()
a1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
a1.connect(A1_IP, username='gdadmin', password=PASSWORD, timeout=10)
print("  A1 (%s) connected" % A1_IP)

a2 = paramiko.SSHClient()
a2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
a2.connect(A2_IP, username='gdadmin', password=PASSWORD, timeout=10)
print("  A2 (%s) connected" % A2_IP)

# --- Step 2: SCP fixed init_db.sql to A2 ---
print("\n[2] SCP fixed init_db.sql to A2...")
sftp = a2.open_sftp()
sftp.put('%s/scenario-a/vm-a2-internal/init_db.sql' % BASE, '/tmp/init_db.sql')
sftp.close()
print("  Done")

# --- Step 3: Re-import database ---
print("\n[3] Re-importing database on A2...")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' < /tmp/init_db.sql 2>&1")

# --- Step 3b: Fix table schemas (add missing standard PbootCMS columns) ---
print("\n[3b] Adding missing standard PbootCMS columns to ay_content_sort...")
sort_cols = [
    "ALTER TABLE cms.ay_content_sort ADD COLUMN acode varchar(20) NOT NULL DEFAULT 'cn' AFTER scode",
    "ALTER TABLE cms.ay_content_sort ADD COLUMN mcode varchar(20) NOT NULL DEFAULT '2' AFTER sorting",
    "ALTER TABLE cms.ay_content_sort ADD COLUMN status tinyint(1) DEFAULT '1' AFTER mcode",
    "ALTER TABLE cms.ay_content_sort ADD COLUMN filename varchar(100) DEFAULT '' AFTER status",
    "ALTER TABLE cms.ay_content_sort ADD COLUMN outlink varchar(255) DEFAULT '' AFTER filename",
]
for col in sort_cols:
    ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e \"%s\" 2>&1" % col)
    time.sleep(0.1)

# Fix index name (PbootCMS uses FORCE INDEX with specific names)
print("\n[3c] Fixing ay_content_sort index name (required by FORCE INDEX)...")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e \"ALTER TABLE cms.ay_content_sort DROP INDEX idx_scode\" 2>&1 || true")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e \"ALTER TABLE cms.ay_content_sort ADD UNIQUE KEY ay_content_sort_scode (scode)\" 2>&1")

print("\n[3d] Adding missing standard PbootCMS columns to ay_content...")
content_cols = [
    "ALTER TABLE cms.ay_content ADD COLUMN acode varchar(20) NOT NULL DEFAULT 'cn' AFTER scode",
    "ALTER TABLE cms.ay_content ADD COLUMN subscode varchar(50) NOT NULL DEFAULT '' AFTER scode",
    "ALTER TABLE cms.ay_content ADD COLUMN filename varchar(100) NOT NULL DEFAULT '' AFTER title",
    "ALTER TABLE cms.ay_content ADD COLUMN outlink varchar(255) NOT NULL DEFAULT '' AFTER filename",
    "ALTER TABLE cms.ay_content ADD COLUMN enclosure varchar(255) NOT NULL DEFAULT '' AFTER tags",
    "ALTER TABLE cms.ay_content ADD COLUMN keywords varchar(200) NOT NULL DEFAULT '' AFTER enclosure",
    "ALTER TABLE cms.ay_content ADD COLUMN gid int(10) NOT NULL DEFAULT '0' AFTER oppose",
]
for col in content_cols:
    ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e \"%s\" 2>&1" % col)
    time.sleep(0.1)

# Update existing content with acode='cn'
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e \"UPDATE cms.ay_content SET acode='cn'\" 2>&1")

# --- Step 4: Verify ay_site columns ---
print("\n[4] Verifying ay_site columns...")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e 'DESCRIBE cms.ay_site' 2>&1")

# --- Step 5: Verify ay_site data ---
print("\n[5] Verifying ay_site data...")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT acode,title,subtitle FROM cms.ay_site' 2>&1")

# --- Step 6: Clear PbootCMS cache on A1 ---
print("\n[6] Clearing all caches on A1...")
ssh_cmd(a1, "sudo rm -rf /var/www/cms/runtime/cache/* /var/www/cms/runtime/complile/* /var/www/cms/runtime/archive/* /var/www/cms/runtime/data/* /var/www/cms/runtime/config/* /var/www/cms/runtime/session/* 2>/dev/null; echo done", sudo=True)

# --- Step 7: Restart apache2 ---
print("\n[7] Restarting apache2 on A1...")
ssh_cmd(a1, "sudo systemctl restart apache2", sudo=True)

time.sleep(1)

# --- Step 8: Test frontend ---
print("\n[8] Testing frontend...")
ssh_cmd(a1, "curl -s -o /dev/null -w '%%{http_code}' http://localhost/")
title_out, _, _ = ssh_cmd(a1, "curl -s http://localhost/ 2>&1 | grep -o '<title>[^<]*</title>'")
title = title_out.strip()
print("  Title: " + title)

# --- Step 9: Verify users ---
print("\n[9] Verifying users...")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT username,realname FROM cms.ay_user' 2>&1")

# --- Step 10: Verify business tables ---
print("\n[10] Verifying business tables...")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM cms' 2>&1")

a1.close()
a2.close()

print("\n[OK] Fix complete!")
print("  Title result: " + title)
if '区域IPTV内容编排平台' in title:
    print("  [PASS] Frontend loads correctly with IPTV title")
else:
    print("  [FAIL] Frontend title does not contain expected text")
