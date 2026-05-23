#!/usr/bin/env python3
"""Install Drupal 7.57 schema on C2 by running install tasks directly"""
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
    if out.strip(): print(f"  out: {out.strip()[:1500]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, exit_code

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Approach: Run Drupal install tasks directly, skipping the theme/output phase
# Based on install.core.inc: install_run_tasks() is what actually creates DB tables

install_script = r'''<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

define('DRUPAL_ROOT', '/var/www/drupal');
define('MAINTENANCE_MODE', 'install');

// Must set these before including install.core.inc
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
$_SERVER['SERVER_SOFTWARE'] = 'Apache';
$_SERVER['REQUEST_METHOD'] = 'GET';

require_once DRUPAL_ROOT . '/includes/install.core.inc';

// Manually set up install_state like install_begin_request does
$install_state = array();
$install_state['parameters'] = array(
    'profile' => 'standard',
    'locale' => 'en',
);
$install_state['settings_verified'] = TRUE;
$install_state['database_verified'] = TRUE;
$install_state['server_verified'] = TRUE;

// Load the profile
$profile = $install_state['parameters']['profile'];
require_once DRUPAL_ROOT . '/profiles/' . $profile . '/' . $profile . '.profile';

// Get the install tasks
$tasks = install_tasks($install_state);
echo "Install tasks found: " . count($tasks) . "\n";

// Override the display function to just echo
function install_display_output($install_state) {
    echo "Install step: " . ($install_state['active_task'] ?? 'unknown') . "\n";
}

// Override st() and t()
if (!function_exists('st')) {
    function st($string, array $args = array(), array $options = array()) {
        return format_string($string, $args);
    }
}

// Bootstrap to configuration level
drupal_bootstrap(DRUPAL_BOOTSTRAP_CONFIGURATION);

// Get the full list of tasks
$tasks = install_tasks_to_display($install_state);
echo "\nTasks to run:\n";
foreach ($tasks as $name => $task) {
    echo "  - $name: " . ($task['display_name'] ?? '') . "\n";
}

// Run tasks in order
try {
    foreach ($tasks as $task_name => $task) {
        if ($task_name === 'done' || $task_name === 'finished') {
            continue;
        }
        echo "\nRunning task: $task_name...\n";
        $install_state['active_task'] = $task_name;

        $function = $task['function'];
        if (function_exists($function)) {
            $function($install_state);
            echo "  Task $task_name completed.\n";
        } else {
            echo "  SKIP: function $function not found\n";
        }
    }
    echo "\nALL TASKS COMPLETE\n";
} catch (Exception $e) {
    echo "\nERROR: " . $e->getMessage() . "\n";
    echo "File: " . $e->getFile() . ":" . $e->getLine() . "\n";
    echo "Trace:\n" . $e->getTraceAsString() . "\n";
}
'''

print("Writing install script...")
sftp = c.open_sftp()
with sftp.open('/tmp/drupal_install_v4.php', 'w') as f:
    f.write(install_script.encode('utf-8'))
sftp.close()
print("Written.")

print("\nRunning install script...")
out, err, ec = run(c,
    "cd /var/www/drupal && echo 'Gdadmin@123' | sudo -S php /tmp/drupal_install_v4.php 2>&1",
    timeout=120)

print("\n=== Checking tables ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM drupal;' 2>/dev/null")

print("\n=== HTTP test ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")

c.close()
