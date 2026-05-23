#!/usr/bin/env python3
"""Fix Drupal 7 prefixTables to add backtick quoting, then run drush install"""
import paramiko

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
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  out: {out.strip()[:2000]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, ec

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Step 1: Fix the prefixTables bug - add backtick quoting when no prefix
print("=== Step 1: Fix prefixTables to add backticks ===")

# Read current lines 441-444
run(c, "echo 'Gdadmin@123' | sudo -S sed -n '439,446p' /var/www/drupal/includes/database/database.inc")

# Apply fix: change line 442 to use backtick when prefix is empty
# Original: $this->prefixReplace[] = $this->prefixes['default'];
# Fixed:    $this->prefixReplace[] = $this->prefixes['default'] !== '' ? $this->prefixes['default'] : '`';
# And line 444: $this->prefixReplace[] = $this->prefixes['default'] !== '' ? '' : '`';

fix_cmd = (
    "echo 'Gdadmin@123' | sudo -S sed -i "
    "'442s/.*/    \\$this->prefixReplace[] = \\$this->prefixes['\"'\"'default'\"'\"'] !== '\"''\"''\"'\"' ? \\$this->prefixReplace[] = \\$this->prefixes['\"'\"'default'\"'\"'] : '\"'\"'`'\"'\"';/' "
    "/var/www/drupal/includes/database/database.inc"
)
# This sed approach is getting too complex with escapes. Let me use a Python string replacement instead.

# Read the file via SFTP
sftp = c.open_sftp()
with sftp.open('/var/www/drupal/includes/database/database.inc', 'r') as f:
    content = f.read().decode('utf-8')
sftp.close()

print(f"Read database.inc: {len(content)} chars")

# Apply fixes
old_442 = "    $this->prefixReplace[] = $this->prefixes['default'];"
new_442 = "    $this->prefixReplace[] = $this->prefixes['default'] !== '' ? $this->prefixes['default'] : '`';"

old_444 = "    $this->prefixReplace[] = '';"
new_444 = "    $this->prefixReplace[] = $this->prefixes['default'] !== '' ? '' : '`';"

if old_442 in content:
    content = content.replace(old_442, new_442)
    print("Fixed line 442")
else:
    print("Line 442 not found! Checking...")
    # Find the line
    for i, line in enumerate(content.split('\n'), 1):
        if 'prefixReplace' in line and 'default' in line:
            print(f"  Line {i}: {line}")

if old_444 in content:
    content = content.replace(old_444, new_444)
    print("Fixed line 444")
else:
    print("Line 444 not found!")

# Write back
with sftp.open('/var/www/drupal/includes/database/database.inc', 'w') as f:
    f.write(content.encode('utf-8'))
sftp.close()
print("Written back.")

# Verify
print("\nVerifying fix...")
run(c, "echo 'Gdadmin@123' | sudo -S sed -n '440,446p' /var/www/drupal/includes/database/database.inc")

# Step 2: Reset database
print("\n=== Step 2: Reset database ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'DROP DATABASE IF EXISTS drupal; CREATE DATABASE drupal CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;' 2>/dev/null && echo 'OK'")

# Step 3: Write temp settings.php (no $databases)
print("\n=== Step 3: Write temp settings.php ===")
temp_settings = """<?php
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
     "/var/www/drupal/sites/default/settings.php")

# Step 4: Run drush site-install
print("\n=== Step 4: Run drush site-install ===")
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

# Step 5: Check result
print("\n=== Step 5: Check result ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT COUNT(*) AS cnt FROM information_schema.TABLES WHERE TABLE_SCHEMA=\"drupal\";' 2>/dev/null")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=\"drupal\" ORDER BY TABLE_NAME;' 2>/dev/null | head -40")

# Step 6: Restore settings.php with $databases
print("\n=== Step 6: Restore settings.php ===")
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
     "/var/www/drupal/sites/default/settings.php")

# Step 7: Fix files directory permissions
run(c, "echo 'Gdadmin@123' | sudo -S mkdir -p /var/www/drupal/sites/default/files && "
     "echo 'Gdadmin@123' | sudo -S chmod -R 777 /var/www/drupal/sites/default/files")

# Step 8: Test HTTP
print("\n=== Step 8: Test HTTP ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c, "curl -s http://localhost/ | grep -o '<title>[^<]*</title>'")

c.close()
print("\nDone!")
