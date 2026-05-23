#!/usr/bin/env python3
"""Fix Drupal 7 prefixTables and run drush install - v2 with better SFTP handling"""
import paramiko, time

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
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  out: {out.strip()[:2000]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, ec

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Step 1: Check if fix already applied
print("=== Step 1: Check current prefixTable code ===")
out, err, ec = run(c, "echo 'Gdadmin@123' | sudo -S sed -n '440,446p' /var/www/drupal/includes/database/database.inc")

# If the fix is NOT applied (no backtick in line 442), apply it via sed
if "`" not in out:
    print("\nFix NOT applied. Applying now...")
    # Use Python to write the fixed lines via echo/sed
    # Approach: use a temp file approach with SFTP

    # Read current file
    sftp = c.open_sftp()
    try:
        with sftp.open('/var/www/drupal/includes/database/database.inc', 'r') as f:
            content = f.read().decode('utf-8')
        sftp.close()

        # Apply fix
        old_442 = "    $this->prefixReplace[] = $this->prefixes['default'];"
        new_442 = "    $this->prefixReplace[] = $this->prefixes['default'] !== '' ? $this->prefixes['default'] : '`';"
        old_444 = "    $this->prefixReplace[] = '';"
        new_444 = "    $this->prefixReplace[] = $this->prefixes['default'] !== '' ? '' : '`';"

        content = content.replace(old_442, new_442)
        content = content.replace(old_444, new_444)

        # Write to temp first
        sftp = c.open_sftp()
        with sftp.open('/tmp/database.inc.fixed', 'w') as f:
            f.write(content.encode('utf-8'))
        sftp.close()

        # sudo copy into place
        run(c, "echo 'Gdadmin@123' | sudo -S cp /tmp/database.inc.fixed "
             "/var/www/drupal/includes/database/database.inc && echo 'FIXED'")

        # Verify
        print("\nVerifying...")
        run(c, "echo 'Gdadmin@123' | sudo -S sed -n '440,446p' /var/www/drupal/includes/database/database.inc")
    except Exception as e:
        print(f"SFTP error: {e}")
        # Fall back to sed approach
        run(c, "echo 'Gdadmin@123' | sudo -S sed -i "
             "\"s|\\$this->prefixReplace\\[\\] = \\$this->prefixes\\['default'\\];|\\$this->prefixReplace[] = \\$this->prefixes['default'] !== '' ? \\$this->prefixes['default'] : '`';|g\" "
             "/var/www/drupal/includes/database/database.inc && echo 'SED_FIX_442'")
        run(c, "echo 'Gdadmin@123' | sudo -S sed -i "
             "\"s|    \\$this->prefixReplace\\[\\] = '';|    \\$this->prefixReplace[] = \\$this->prefixes['default'] !== '' ? '' : '`';|g\" "
             "/var/www/drupal/includes/database/database.inc && echo 'SED_FIX_444'")
else:
    print("Fix already applied!")

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

if 'cnt' in out and '74' in out or '73' in out or '70' in out:
    print("✅ FULL INSTALL - 70+ tables!")
else:
    run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM drupal;' 2>/dev/null")

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

# Step 7: Fix files directory
run(c, "echo 'Gdadmin@123' | sudo -S mkdir -p /var/www/drupal/sites/default/files && "
     "echo 'Gdadmin@123' | sudo -S chmod -R 777 /var/www/drupal/sites/default/files")

# Step 8: Test HTTP
print("\n=== Step 8: Test HTTP ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c, "curl -s http://localhost/ | grep -o '<title>[^<]*</title>'")

c.close()
print("\nDone!")
