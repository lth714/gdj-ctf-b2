#!/usr/bin/env python3
"""Check Drupal 7 prepareQuery to understand prefixing"""
import paramiko

host = '192.168.101.141'
user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(c, cmd, use_sudo=False, timeout=30):
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

# Check prepareQuery
print("=== prepareQuery ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n -A20 'function prepareQuery' /var/www/drupal/includes/database/database.inc")

# Check expandArguments
print("\n=== expandArguments ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n -A15 'function expandArguments' /var/www/drupal/includes/database/database.inc")

# Let me write a PHP script that traces the exact SQL being executed
trace_php = r'''<?php
// Trace what SQL Drupal generates for the system table
define('DRUPAL_ROOT', '/var/www/drupal');

$databases = array(
  'default' => array(
    'default' => array(
      'database' => 'drupal',
      'username' => 'root',
      'password' => 'R00t@Mysql#2024',
      'host' => 'localhost',
      'driver' => 'mysql',
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
require_once DRUPAL_ROOT . '/includes/common.inc';
require_once DRUPAL_ROOT . '/includes/unicode.inc';

drupal_bootstrap(DRUPAL_BOOTSTRAP_DATABASE);

// Load the system module schema definition
require_once DRUPAL_ROOT . '/modules/system/system.install';
$schema = system_schema();

// Get the system table definition
$table_def = $schema['system'];
echo "System table definition:\n";
print_r(array_keys($table_def));
echo "\n";

// Call createTableSql to see what SQL is generated
$connection = Database::getConnection();
$schema_obj = $connection->schema();

// Use reflection to call the protected method
$ref = new ReflectionMethod(get_class($schema_obj), 'createTableSql');
$ref->setAccessible(true);
$sql_statements = $ref->invoke($schema_obj, 'system', $table_def);

echo "Generated SQL:\n";
foreach ($sql_statements as $i => $sql) {
    echo "Statement $i:\n$sql\n\n";
}

// Now apply prefixTables
echo "After prefixTables:\n";
foreach ($sql_statements as $i => $sql) {
    $prefixed = $connection->prefixTables($sql);
    echo "Statement $i:\n$prefixed\n\n";
}

echo "\nAttempting to execute...\n";
try {
    foreach ($sql_statements as $sql) {
        $connection->query($sql);
        echo "  OK: " . substr($sql, 0, 60) . "...\n";
    }
    echo "System table created!\n";
} catch (Exception $e) {
    echo "ERROR: " . $e->getMessage() . "\n";
}
'''

print("\n=== Writing trace script ===")
sftp = c.open_sftp()
with sftp.open('/tmp/trace_system_table.php', 'w') as f:
    f.write(trace_php.encode('utf-8'))
sftp.close()

print("\n=== Running trace script ===")
out, err, ec = run(c,
    "cd /var/www/drupal && echo 'Gdadmin@123' | sudo -S php /tmp/trace_system_table.php 2>&1",
    timeout=30)

c.close()
