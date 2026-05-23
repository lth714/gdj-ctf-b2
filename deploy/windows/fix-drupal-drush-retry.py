#!/usr/bin/env python3
"""Retry drush install - check what's at database.inc:2227 and ensure MySQL 8 compat"""
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

# Check line 2227 in database.inc
print("=== database.inc around line 2227 ===")
run(c, "echo 'Gdadmin@123' | sudo -S sed -n '2220,2240p' /var/www/drupal/includes/database/database.inc")

# The real approach: Let me just try to manually create the system table
# using Drupal's schema definition but through a simpler path

# Actually let me try a completely different approach:
# Use the WEB installer instead of drush. The web installer goes through
# Drupal's full bootstrap and might handle things better.

# Step 1: Reset and prepare
print("\n=== Step 1: Reset database ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'DROP DATABASE IF EXISTS drupal; CREATE DATABASE drupal CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;' 2>/dev/null && echo 'OK'")

# Step 2: Write temp settings without $databases
print("\n=== Step 2: Write temp settings.php ===")
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

# Step 3: Run drush again with verbose output
print("\n=== Step 3: Run drush with verbose output ===")
run(c, "echo 'Gdadmin@123' | sudo -S rm -f /tmp/drush_install_v2.php")

# Let's try using drush with --debug flag
out, err, ec = run(c,
    "cd /var/www/drupal && "
    "echo 'Gdadmin@123' | sudo -S php /tmp/drush.phar site-install standard "
    "--db-url='mysql://root:R00t@Mysql%232024@localhost/drupal' "
    "--site-name='GDJ OA Portal' "
    "--account-name=admin "
    "--account-pass='Admin@Drupal#2024' "
    "--account-mail=admin@gdj.local "
    "--yes --debug 2>&1 | tail -80",
    timeout=300)

# Check what tables we got
print("\n=== Table count ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT COUNT(*) AS cnt FROM information_schema.TABLES WHERE TABLE_SCHEMA=\"drupal\";' 2>/dev/null")

# If system table is the only issue, create it manually
print("\n=== Check if system table exists ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'DESC drupal.system;' 2>/dev/null && echo 'EXISTS' || echo 'MISSING'")

c.close()
print("\nDone!")
