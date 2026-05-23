#!/usr/bin/env python3
"""Debug C2 Drupal settings.php issues"""
import paramiko

host = '192.168.101.141'
user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(c, cmd, use_sudo=False):
    if use_sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    stdin, stdout, stderr = c.exec_command(cmd, timeout=15)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(f">>> {cmd[:120]}")
    if out.strip(): print(f"  out: {out.strip()}")
    if err.strip(): print(f"  err: {err.strip()}")
    return out, err

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Check Apache config
run(c, "ls /etc/apache2/sites-enabled/", use_sudo=True)
run(c, "a2query -s", use_sudo=True)

# Check what ports Apache listens on
run(c, "ss -tlnp | grep apache")

# Check if there's a Drupal .htaccess
run(c, "cat /var/www/drupal/.htaccess | head -20", use_sudo=True)

# Check Apache config that's actually loaded
run(c, "cat /etc/apache2/apache2.conf | grep -i documentroot", use_sudo=True)
run(c, "cat /etc/apache2/sites-available/000-default.conf | head -30", use_sudo=True)

# What modules are enabled?
run(c, "a2query -m rewrite", use_sudo=True)

# Check Drupal database
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM drupal;'")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=\"drupal\";'")

# Try curl with verbose
run(c, "curl -v http://localhost/ 2>&1 | head -40")

# Check the install.php
run(c, "curl -s http://localhost/install.php | head -20")

c.close()

c.close()
