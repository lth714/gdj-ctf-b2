#!/usr/bin/env python3
"""Fix C2 Drupal settings.php - $ chars were eaten by bash expansion"""
import paramiko

host = '192.168.101.141'
user = 'gdadmin'
pwd = 'Gdadmin@123'

# Drupal 7.57 settings.php with PROPER $ prefix on all PHP variables
SETTINGS_PHP = """<?php

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

$conf['allow_authorize_operations'] = FALSE;
"""

print(f"Connecting to C2 ({host})...")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.")

sftp = c.open_sftp()

# Write to /tmp first (no permission issues), then sudo cp
tmp_path = '/tmp/settings.php'
with sftp.open(tmp_path, 'w') as f:
    f.write(SETTINGS_PHP.encode('utf-8'))
print(f"Written to: {tmp_path}")

sftp.close()

# sudo cp to Drupal directory
stdin, stdout, stderr = c.exec_command(
    "echo 'Gdadmin@123' | sudo -S cp /tmp/settings.php /var/www/drupal/sites/default/settings.php && "
    "echo 'Gdadmin@123' | sudo -S chown www-data:www-data /var/www/drupal/sites/default/settings.php && "
    "echo 'COPIED'"
)
print(stdout.read().decode().strip())

# Verify the content
stdin, stdout, stderr = c.exec_command('sudo head -20 /var/www/drupal/sites/default/settings.php')
print("\nVerification (first 20 lines):")
print(stdout.read().decode())

# Restart Apache
stdin, stdout, stderr = c.exec_command(
    "echo 'Gdadmin@123' | sudo -S systemctl restart apache2 && sleep 2 && echo 'APACHE_RESTARTED'"
)
print(stdout.read().decode().strip())

# Test HTTP
stdin, stdout, stderr = c.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost/ 2>/dev/null")
http_code = stdout.read().decode().strip()
print(f"\nHTTP status: {http_code}")

# Check Apache error log if still failing
if http_code != '200':
    stdin, stdout, stderr = c.exec_command("sudo tail -20 /var/log/apache2/error.log")
    print("\nApache error log:")
    print(stdout.read().decode())

c.close()
print("\nDone!")
