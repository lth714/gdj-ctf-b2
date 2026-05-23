#!/usr/bin/env python3
"""Install Drupal 7.57 schema on C2 via drush or direct SQL"""
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

# Approach: Use a PHP script that simulates the install process
# by calling individual install tasks directly, not install_drupal()

install_script_v2 = '''<?php
// Programmatic Drupal 7 install - bypass theme()
define('DRUPAL_ROOT', '/var/www/drupal');

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
$_SERVER['REQUEST_URI'] = '/';
$_SERVER['SCRIPT_NAME'] = '/index.php';

require_once DRUPAL_ROOT . '/includes/bootstrap.inc';
require_once DRUPAL_ROOT . '/includes/database/database.inc';
require_once DRUPAL_ROOT . '/includes/database/schema.inc';

// Bootstrap the database
drupal_bootstrap(DRUPAL_BOOTSTRAP_DATABASE);

// Get list of enabled modules from standard profile
$profile = 'standard';
$profile_path = DRUPAL_ROOT . '/profiles/' . $profile;
require_once $profile_path . '/' . $profile . '.profile';

// Read profile info to get dependencies
$info = drupal_parse_info_file($profile_path . '/' . $profile . '.info');
$modules = isset($info['dependencies']) ? $info['dependencies'] : array();
// Also look at system module
$system_info = drupal_parse_info_file(DRUPAL_ROOT . '/modules/system/system.info');
if (isset($system_info['dependencies'])) {
    $modules = array_merge($modules, $system_info['dependencies']);
}

echo "Modules to install: " . implode(', ', $modules) . "\\n";

// Install each module's schema
foreach ($modules as $module_name) {
    $module_path = DRUPAL_ROOT . '/modules/' . $module_name;
    $install_file = $module_path . '/' . $module_name . '.install';
    if (file_exists($install_file)) {
        module_load_install($module_name);
        $schema_func = $module_name . '_schema';
        if (function_exists($schema_func)) {
            $schema = $schema_func();
            foreach ($schema as $table_name => $table_def) {
                if (!db_table_exists($table_name)) {
                    db_create_table($table_name, $table_def);
                    echo "  Created table: $table_name\\n";
                }
            }
        }
    }
}

// Also handle profile schema
$profile_install = $profile_path . '/' . $profile . '.install';
if (file_exists($profile_install)) {
    require_once $profile_install;
    $schema_func = $profile . '_schema';
    if (function_exists($schema_func)) {
        // profile doesn't usually have schema, but check
    }
    // Run profile install tasks
    $install_func = $profile . '_install';
    if (function_exists($install_func)) {
        $install_func();
        echo "  Ran profile install\\n";
    }
}

echo "DONE\\n";
'''

print("Writing install script v2...")
sftp = c.open_sftp()
with sftp.open('/tmp/drupal_install_v2.php', 'w') as f:
    f.write(install_script_v2.encode('utf-8'))
sftp.close()

print("Running install script v2...")
out, err, ec = run(c,
    "cd /var/www/drupal && echo 'Gdadmin@123' | sudo -S php /tmp/drupal_install_v2.php 2>&1",
    timeout=120)

print("\nChecking tables...")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM drupal;' 2>/dev/null")

print("\nTesting HTTP...")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")

c.close()
