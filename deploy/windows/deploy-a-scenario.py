#!/usr/bin/env python3
"""Deploy Scenario A IPTV theme updates to running VMs."""
import paramiko
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

A1_IP = '192.168.100.1'
A2_IP = '192.168.100.2'
PASSWORD = 'Gdadmin@123'
BASE = 'E:/vibecoding/gdj_ctf'


def ssh_cmd(ssh, cmd, timeout=30, sudo=False):
    """Run a command via SSH."""
    if sudo:
        cmd = f'echo "{PASSWORD}" | sudo -S {cmd}'
    print(f"  >>> {cmd[:150]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    if sudo:
        stdin.write(PASSWORD + '\n')
        stdin.flush()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        for line in out.strip().split('\n')[:4]:
            print(f"      {line}")
    if err.strip() and ec != 0:
        print(f"  [err] {err.strip()[:200]}")
    return out, err, ec


def scp_put(ssh, local_path, remote_path):
    """SCP a file to remote."""
    print(f"  SCP: {local_path} -> {remote_path}")
    sftp = ssh.open_sftp()
    try:
        sftp.put(local_path, remote_path)
        sftp.chmod(remote_path, 0o644)
    finally:
        sftp.close()


def scp_dir(ssh, local_dir, remote_dir):
    """SCP all files in a directory."""
    sftp = ssh.open_sftp()
    try:
        sftp.mkdir(remote_dir)
    except:
        pass
    finally:
        sftp.close()
    for f in os.listdir(local_dir):
        lp = os.path.join(local_dir, f)
        rp = os.path.join(remote_dir, f)
        if os.path.isfile(lp):
            scp_put(ssh, lp, rp)


# ============================================================
# Connect
# ============================================================
print("[1] Connecting to VMs...")
a1 = paramiko.SSHClient()
a1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
a1.connect(A1_IP, username='gdadmin', password=PASSWORD, timeout=10)
print(f"  A1 ({A1_IP}) connected")

a2 = paramiko.SSHClient()
a2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
a2.connect(A2_IP, username='gdadmin', password=PASSWORD, timeout=10)
print(f"  A2 ({A2_IP}) connected")

# ============================================================
# Step 2: Deploy init_db.sql to A2 and re-import
# ============================================================
print("\n[2] Deploying init_db.sql to A2...")
scp_put(a2,
        f'{BASE}/scenario-a/vm-a2-internal/init_db.sql',
        '/tmp/init_db.sql')

print("  Re-importing database...")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' < /tmp/init_db.sql 2>&1", sudo=False)
print("  Database re-imported.")

# ============================================================
# Step 3: Deploy updated config.php to A1
# ============================================================
print("\n[3] Deploying config.php to A1...")
scp_put(a1,
        f'{BASE}/scenario-a/vm-a1-dmz/files/pbootcms/config/config.php',
        '/tmp/config.php')
ssh_cmd(a1, "sudo cp /var/www/cms/config/config.php /var/www/cms/config/config.php.bak 2>/dev/null; sudo cp /tmp/config.php /var/www/cms/config/config.php; sudo chown www-data:www-data /var/www/cms/config/config.php; echo done", sudo=True)

# ============================================================
# Step 4: Deploy new Flask API to A1
# ============================================================
print("\n[4] Deploying media-api app.py to A1...")
scp_put(a1,
        f'{BASE}/scenario-a/vm-a1-dmz/files/media-api/app.py',
        '/tmp/app.py')
ssh_cmd(a1, "sudo cp /tmp/app.py /opt/media-api/app.py && sudo chown www-data:www-data /opt/media-api/app.py; echo done", sudo=True)
ssh_cmd(a1, "sudo systemctl restart media-api 2>&1", sudo=True)

# ============================================================
# Step 5: Deploy backup/ files to A1
# ============================================================
print("\n[5] Deploying updated SQL + hint files to A1 backup directory...")
scp_put(a1,
        f'{BASE}/scenario-a/vm-a1-dmz/files/pbootcms/static/backup/sql/cms_20240101.sql',
        '/tmp/cms_20240101.sql')
scp_put(a1,
        f'{BASE}/scenario-a/vm-a1-dmz/files/publish_notes_202405.txt',
        '/tmp/publish_notes_202405.txt')
scp_put(a1,
        f'{BASE}/scenario-a/vm-a1-dmz/files/media_api_config.example.bak',
        '/tmp/media_api_config.example.bak')
ssh_cmd(a1, "sudo cp /tmp/cms_20240101.sql /var/www/cms/static/backup/sql/ && sudo cp /tmp/publish_notes_202405.txt /var/www/cms/static/backup/sql/ && sudo cp /tmp/media_api_config.example.bak /var/www/cms/static/backup/sql/ && sudo chown -R www-data:www-data /var/www/cms/static/backup/sql/; echo done", sudo=True)

# Re-compress SQL dump
print("  Re-compressing SQL dump...")
ssh_cmd(a1, "cd /var/www/cms/static/backup/sql && gzip -k -f cms_20240101.sql && chmod 644 cms_20240101.sql.gz")

# ============================================================
# Step 6: Deploy ops files to A1
# ============================================================
print("\n[6] Deploying ops files to A1...")
scp_put(a1,
        f'{BASE}/scenario-a/vm-a1-dmz/files/publish_sync_202405.log',
        '/tmp/publish_sync_202405.log')
ssh_cmd(a1, "sudo mkdir -p /opt/ops && sudo cp /tmp/publish_sync_202405.log /opt/ops/ && sudo chmod 644 /opt/ops/publish_sync_202405.log; echo done", sudo=True)

# Update /opt/ops/access.txt
print("  Updating /opt/ops/access.txt...")
access_txt = """===== 播控运维交接记录 =====
日期: 2024-01-15
值班人: 值班工程师

内网支撑服务 (VM-A2) 访问方式:
  IP: 192.168.100.2
  SSH运维: operator / 0p3rat0r@GDJ
  数据库: 192.168.100.2:3306 (root / R00t@Mysql#2024)
  缓存: 192.168.100.2:6379
  知识库: http://192.168.100.2:8090

提示: 知识库管理员账户与SSH运维密码一致，用于查阅播控发布技术文档。"""

ssh_cmd(a1, f"cat > /opt/ops/access.txt << 'OPSEOF'\n{access_txt}\nOPSEOF")
ssh_cmd(a1, "chmod 600 /opt/ops/access.txt")

# Update MySQL reminder
print("  Updating /root/mysql_root_reminder.txt...")
mysql_reminder = """MySQL root password for 192.168.100.2 (内网播控数据库):
R00t@Mysql#2024

Note: 数据库配置文件位于 /etc/mysql/mysql.conf.d/root.cnf on VM-A2
(内网数据管理MySQL连接配置文件)"""

ssh_cmd(a1, f"cat > /tmp/mysql_reminder.txt << 'ROOTEOF'\n{mysql_reminder}\nROOTEOF")
ssh_cmd(a1, "sudo cp /tmp/mysql_reminder.txt /root/mysql_root_reminder.txt && sudo chmod 600 /root/mysql_root_reminder.txt", sudo=True)

# ============================================================
# Step 7: Restart services on A1
# ============================================================
print("\n[7] Restarting services on A1...")
ssh_cmd(a1, "sudo systemctl restart apache2", sudo=True)
ssh_cmd(a1, "sudo systemctl restart nginx", sudo=True)

# ============================================================
# Step 8: Verify A1 services
# ============================================================
print("\n[8] Verifying A1 services...")
ssh_cmd(a1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
ssh_cmd(a1, "curl -s http://localhost/media/status 2>&1 | head -5")
ssh_cmd(a1, "curl -s -o /dev/null -w '%{http_code}' http://localhost/backup/")

# ============================================================
# Step 9: Verify A2 services
# ============================================================
print("\n[9] Verifying A2 services...")
ssh_cmd(a2, "systemctl is-active mysql redis-server confluence 2>&1")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT COUNT(*) as tables FROM information_schema.tables WHERE table_schema=\"cms\"' 2>&1")

# ============================================================
# Step 10: Verify new users in database
# ============================================================
print("\n[10] Verifying new users...")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT username, realname FROM cms.ay_user' 2>&1")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT scode, name FROM cms.ay_content_sort ORDER BY sorting' 2>&1")
ssh_cmd(a2, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT name, title FROM cms.ay_site' 2>&1")

# ============================================================
# Done
# ============================================================
a1.close()
a2.close()
print("\n[✓] Scenario A IPTV theme deployment complete!")
print("    A1: http://192.168.100.1/")
print("    A2: MySQL 192.168.100.2:3306 / Confluence :8090")
