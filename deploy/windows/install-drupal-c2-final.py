#!/usr/bin/env python3
"""Install Drupal 7.57 on C2 via drush - final approach"""
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
sftp = c.open_sftp()
sftp.put(local_path, '/tmp/drush.phar')
sftp.chmod('/tmp/drush.phar', 0o755)
sftp.close()
print("Uploaded.")

# Step 2: Temporarily remove $databases from settings.php so Drupal
# doesn't think it's already installed
print("\n=== Step 2: Create temp settings.php without \$databases ===")

# Write a minimal settings.php that only creates the files directory,
# with $databases COMMENTED OUT so drush can install fresh
temp_settings = """<?php

// $databases is intentionally NOT set here so Drupal installer runs fresh.
// It will be added after drush site-install completes.

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

# Backup current settings.php
run(c, "echo 'Gdadmin@123' | sudo -S cp /var/www/drupal/sites/default/settings.php "
     "/var/www/drupal/sites/default/settings.php.bak", timeout=10)

# Write temp settings via SFTP
sftp = c.open_sftp()
with sftp.open('/tmp/settings_temp.php', 'w') as f:
    f.write(temp_settings.encode('utf-8'))
sftp.close()

run(c, "echo 'Gdadmin@123' | sudo -S cp /tmp/settings_temp.php "
     "/var/www/drupal/sites/default/settings.php && "
     "echo 'Gdadmin@123' | sudo -S chown www-data:www-data "
     "/var/www/drupal/sites/default/settings.php",
     timeout=10)

print("Temp settings.php written (no \$databases).")

# Step 3: Run drush site-install
print("\n=== Step 3: Run drush site-install ===")
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

# Step 4: Restore proper settings.php with $databases
print("\n=== Step 4: Restore settings.php with \$databases ===")

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

# Step 5: Clear Drupal cache (drush may have created cache entries with wrong settings)
print("\n=== Step 5: Verify ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM drupal;' 2>/dev/null | head -30")

# Step 6: Test HTTP
print("\n=== Step 6: Test HTTP ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c, "curl -s http://localhost/ | head -10")

# Step 7: Check for errors
print("\n=== Step 7: Apache error log ===")
run(c, "echo 'Gdadmin@123' | sudo -S tail -10 /var/log/apache2/error.log")

c.close()
print("\nDone!")
