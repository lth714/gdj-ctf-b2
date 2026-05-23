#!/usr/bin/env python3
"""Install Drupal 7.57 on C2 via drush - fix MySQL 8 sql_mode then install"""
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

# Step 1: Fix MySQL sql_mode - remove NO_AUTO_CREATE_USER (removed in MySQL 8)
print("=== Step 1: Fix MySQL sql_mode ===")
# Check current sql_mode
run(c, "mysql -u root -p'R00t@Mysql#2024' -e \"SELECT @@sql_mode;\" 2>/dev/null")

# Set global sql_mode without NO_AUTO_CREATE_USER
run(c, "mysql -u root -p'R00t@Mysql#2024' -e \"SET GLOBAL sql_mode = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';\" 2>/dev/null")

# Also set it in the config file for persistence
run(c, "echo 'Gdadmin@123' | sudo -S bash -c 'cat >> /etc/mysql/mysql.conf.d/mysqld.cnf << EOF\n"
     "sql_mode = ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION\n"
     "EOF' && echo 'CONFIG_UPDATED'")

# Restart MySQL
run(c, "echo 'Gdadmin@123' | sudo -S systemctl restart mysql && sleep 2 && echo 'MYSQL_RESTARTED'")

# Verify sql_mode
run(c, "mysql -u root -p'R00t@Mysql#2024' -e \"SELECT @@sql_mode;\" 2>/dev/null")

# Step 2: Verify empty drupal database
print("\n=== Step 2: Reset drupal database ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'DROP DATABASE IF EXISTS drupal; CREATE DATABASE drupal CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;' 2>/dev/null && echo 'DB_RESET'")

# Step 3: Upload drush.phar
print("\n=== Step 3: Upload drush.phar ===")
local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'drush.phar')
sftp = c.open_sftp()
sftp.put(local_path, '/tmp/drush.phar')
sftp.chmod('/tmp/drush.phar', 0o755)
sftp.close()
print("Uploaded.")

# Step 4: Write temp settings.php without $databases
print("\n=== Step 4: Write temp settings.php (no \$databases) ===")
temp_settings = """<?php

// $databases is intentionally NOT set so Drupal installer runs fresh.

$update_free_access = FALSE;

$drupal_hash_salt = 'gdjctf2024drupal757hashsaltforctfcompetition';

ini_set('session.gc_probability', 1);
ini_set('session.gc_divisor', 100);
ini_set('session.gc_maxlifetime', 200000);
ini_set('session.cookie_lifetime', 2000000);

$conf['404_fast_paths_exclude'] = '/\\/(?:styles)\\//';
$conf['404_fast_paths'] = '/\\.(?:txt|png|gif|jpe?g|css|js|ico|swf|flv|cgi|bat|pl|dll|exe|asp)$/i';
$conf['404_fast_html'] = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML+RDFa 1.0//EN" "http://www.w3.org/MarkUp/DTD/xhtml-rdfa-1.dtd"><html xmlns="http://www.w3.org/1999/xhtml"><head><title>404 Not Found</title></head><body><h1>Not Found</h1><p>The requested URL "@path" was not found on this server.</p></body></html>';
"""

sftp = c.open_sftp()
with sftp.open('/tmp/settings_temp.php', 'w') as f:
    f.write(temp_settings.encode('utf-8'))
sftp.close()

run(c, "echo 'Gdadmin@123' | sudo -S cp /tmp/settings_temp.php "
     "/var/www/drupal/sites/default/settings.php && "
     "echo 'Gdadmin@123' | sudo -S chown www-data:www-data "
     "/var/www/drupal/sites/default/settings.php",
     timeout=10)

# Also create files directory with proper permissions
run(c, "echo 'Gdadmin@123' | sudo -S mkdir -p /var/www/drupal/sites/default/files && "
     "echo 'Gdadmin@123' | sudo -S chmod 777 /var/www/drupal/sites/default/files",
     timeout=10)

# Step 5: Run drush site-install
print("\n=== Step 5: Run drush site-install ===")
out, err, ec = run(c,
    "cd /var/www/drupal && "
    "echo 'Gdadmin@123' | sudo -S php /tmp/drush.phar site-install standard "
    "--db-url='mysql://root:R00t@Mysql%232024@localhost/drupal' "
    "--site-name='GDJ OA Portal' "
    "--account-name=admin "
    "--account-pass='Admin@Drupal#2024' "
    "--account-mail=admin@gdj.local "
    "--yes 2>&1",
    timeout=300)

# Step 6: Restore proper settings.php
print("\n=== Step 6: Restore settings.php with \$databases ===")
final_settings = """<?php

$databases = array (
  'default' => array (
    'default' => array (
      'database' => 'drupal',
      'username' => 'root',
      'password' => 'R00t@Mysql#2024',
      'host' => 'localhost',
      'port' => '',
      'driver' => 'mysql',
      'prefix' => '',
    ),
  ),
);

$update_free_access = FALSE;

$drupal_hash_salt = 'gdjctf2024drupal757hashsaltforctfcompetition';

ini_set('session.gc_probability', 1);
ini_set('session.gc_divisor', 100);
ini_set('session.gc_maxlifetime', 200000);
ini_set('session.cookie_lifetime', 2000000);

$conf['404_fast_paths_exclude'] = '/\\/(?:styles)\\//';
$conf['404_fast_paths'] = '/\\.(?:txt|png|gif|jpe?g|css|js|ico|swf|flv|cgi|bat|pl|dll|exe|asp)$/i';
$conf['404_fast_html'] = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML+RDFa 1.0//EN" "http://www.w3.org/MarkUp/DTD/xhtml-rdfa-1.dtd"><html xmlns="http://www.w3.org/1999/xhtml"><head><title>404 Not Found</title></head><body><h1>Not Found</h1><p>The requested URL "@path" was not found on this server.</p></body></html>';
"""

sftp = c.open_sftp()
with sftp.open('/tmp/settings_final.php', 'w') as f:
    f.write(final_settings.encode('utf-8'))
sftp.close()

run(c, "echo 'Gdadmin@123' | sudo -S cp /tmp/settings_final.php "
     "/var/www/drupal/sites/default/settings.php && "
     "echo 'Gdadmin@123' | sudo -S chown www-data:www-data "
     "/var/www/drupal/sites/default/settings.php",
     timeout=10)

# Step 7: Verify
print("\n=== Step 7: Verify tables ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT COUNT(*) AS table_count FROM information_schema.TABLES WHERE TABLE_SCHEMA=\"drupal\";' 2>/dev/null")

# Step 8: Test HTTP
print("\n=== Step 8: Test HTTP ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c, "curl -s http://localhost/ | grep -o '<title>[^<]*</title>'")

# Step 9: Check Drupal login
print("\n=== Step 9: Test user login page ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/user/login")

# Step 10: Check for CVE-2018-7600 target page
print("\n=== Step 10: Test user register page ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/user/register")

c.close()
print("\nDone!")
