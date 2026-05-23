#!/usr/bin/env python3
"""Install Drupal 7.57 on C2 via drush phar"""
import paramiko, time

host = '192.168.101.141'
user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(c, cmd, use_sudo=False, timeout=60):
    if use_sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:150]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    exit_code = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  out: {out.strip()[:1000]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, exit_code

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Step 1: Download drush 8 (compatible with Drupal 7)
print("=== Step 1: Download drush ===")
out, err, ec = run(c,
    "cd /tmp && "
    "wget -q https://github.com/drush-ops/drush/releases/download/8.4.12/drush.phar -O drush.phar 2>&1 && "
    "chmod +x drush.phar && "
    "echo 'DRUSH_DOWNLOADED'",
    timeout=60)

if ec != 0 or 'DRUSH_DOWNLOADED' not in out:
    print("Drush download failed, trying composer...")
    out, err, ec = run(c,
        "cd /tmp && "
        "wget -q https://getcomposer.org/download/2.2.0/composer.phar -O composer.phar && "
        "chmod +x composer.phar && "
        "echo 'COMPOSER_OK'",
        timeout=60)
    if ec == 0:
        out, err, ec = run(c,
            "cd /tmp && "
            "php composer.phar require drush/drush:8.4.12 2>&1 | tail -5",
            timeout=120)

# Step 2: Run drush site-install
print("\n=== Step 2: Run drush site-install ===")
out, err, ec = run(c,
    "cd /var/www/drupal && "
    "echo 'Gdadmin@123' | sudo -S php /tmp/drush.phar site-install standard "
    "--db-url=mysql://root:R00t@Mysql#2024@localhost/drupal "
    "--site-name=GDJ_OA_Portal "
    "--account-name=admin "
    "--account-pass=Admin@Drupal#2024 "
    "--account-mail=admin@gdj.local "
    "--yes 2>&1",
    timeout=120)

# Step 3: Verify
print("\n=== Step 3: Verify tables ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM drupal;' 2>/dev/null | head -30")

print("\n=== Step 4: Test HTTP ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")

c.close()
