#!/usr/bin/env python3
"""Install Drupal 7.57 schema on C2 using drush or programmatic install"""
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
    if out.strip(): print(f"  out: {out.strip()[:800]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, exit_code

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Step 1: Check if drush is available
print("=== Step 1: Check drush ===")
out, err, ec = run(c, "which drush || echo 'NOT_FOUND'")

# Step 2: Create an install PHP script that runs Drupal's installer
# This script:
# - Temporarily removes $databases from settings.php
# - Boots Drupal's installer programmatically
# - Uses the 'standard' install profile

install_script = '''<?php
// Programmatic Drupal 7 install
define('DRUPAL_ROOT', '/var/www/drupal');

// Define DB settings that Drupal installer needs
$databases = array(
  'default' => array(
    'default' => array(
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

$_SERVER['HTTP_HOST'] = 'localhost';
$_SERVER['REMOTE_ADDR'] = '127.0.0.1';
$_SERVER['REQUEST_URI'] = '/install.php?profile=standard&locale=en';
$_SERVER['SCRIPT_NAME'] = '/install.php';

require_once DRUPAL_ROOT . '/includes/install.core.inc';

// Run the install
try {
    install_drupal();
    echo "INSTALL_COMPLETE\\n";
} catch (Exception $e) {
    echo "INSTALL_ERROR: " . $e->getMessage() . "\\n";
    echo "Trace: " . $e->getTraceAsString() . "\\n";
}
'''

print("\n=== Step 2: Write install script to C2 ===")
# Write via SFTP to /tmp
sftp = c.open_sftp()
with sftp.open('/tmp/drupal_install.php', 'w') as f:
    f.write(install_script.encode('utf-8'))
sftp.close()
print("Written /tmp/drupal_install.php")

# Step 3: Run the install script
print("\n=== Step 3: Run Drupal installer ===")
out, err, ec = run(c,
    "cd /var/www/drupal && "
    "echo 'Gdadmin@123' | sudo -S php /tmp/drupal_install.php 2>&1",
    timeout=120)

# Step 4: Check if tables were created
print("\n=== Step 4: Verify tables ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM drupal;' 2>&1")

# Step 5: Check if Drupal serves
print("\n=== Step 5: Test HTTP ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")

print("\nDone!")
c.close()
