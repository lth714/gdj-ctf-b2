#!/usr/bin/env python3
"""Install Drupal 7.57 on C2 via drush (uploaded locally)"""
import paramiko, time, os

host = '192.168.101.141'
user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(c, cmd, use_sudo=False, timeout=120):
    if use_sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:150]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    exit_code = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  out: {out.strip()[:1500]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, exit_code

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Step 1: Upload drush.phar
print("=== Step 1: Upload drush.phar ===")
local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'drush.phar')
file_size = os.path.getsize(local_path)
print(f"Local drush.phar: {file_size} bytes")

sftp = c.open_sftp()
sftp.put(local_path, '/tmp/drush.phar')
sftp.chmod('/tmp/drush.phar', 0o755)
sftp.close()
print("Uploaded.")

# Verify
out, err, ec = run(c, "ls -lh /tmp/drush.phar && php /tmp/drush.phar --version")

# Step 2: Run drush site-install
# URL-encode the # in the password: %23
print("\n=== Step 2: Run drush site-install ===")
out, err, ec = run(c,
    "cd /var/www/drupal && "
    "echo 'Gdadmin@123' | sudo -S php /tmp/drush.phar site-install standard "
    "--db-url='mysql://root:R00t@Mysql%232024@localhost/drupal' "
    "--site-name=GDJ_OA_Portal "
    "--account-name=admin "
    "--account-pass=Admin@Drupal#2024 "
    "--account-mail=admin@gdj.local "
    "--yes 2>&1",
    timeout=180)

# Step 3: Verify tables
print("\n=== Step 3: Verify tables ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM drupal;' 2>/dev/null")

# Step 4: Test HTTP
print("\n=== Step 4: Test HTTP ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c, "curl -s http://localhost/ | head -5")

# Step 5: Make sure settings.php still has proper permissions
print("\n=== Step 5: Fix permissions ===")
run(c, "echo 'Gdadmin@123' | sudo -S chown www-data:www-data /var/www/drupal/sites/default/settings.php && echo 'OK'")

c.close()
print("\nDone!")
