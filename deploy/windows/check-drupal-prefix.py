#!/usr/bin/env python3
"""Check Drupal 7 MySQL prefix/quoting mechanism"""
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

# Check how prefixTables/prefixSearch/prefixReplace is configured
print("=== MySQL connection class prefix handling ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n -A10 'prefixReplace\|prefixSearch\|__construct' /var/www/drupal/includes/database/mysql/database.inc")

# Check the query method to see if prefixTables is called
print("\n=== query method ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -n -A15 'function query' /var/www/drupal/includes/database/database.inc | head -30")

# Let's test with a simple PHP script
test_php = r'''<?php
// Test how Drupal handles {table} syntax with MySQL 8
$pdo = new PDO('mysql:host=localhost;dbname=drupal;charset=utf8mb4', 'root', 'R00t@Mysql#2024');

// Test 1: Create a table using {table} -> backtick conversion manually
$name = 'system';
$sql1 = "CREATE TABLE IF NOT EXISTS `$name` (test_col INT)";
echo "Test 1 (manual backtick): ";
try {
    $pdo->exec($sql1);
    echo "OK\n";
    $pdo->exec("DROP TABLE IF EXISTS `$name`");
} catch (Exception $e) {
    echo "FAIL: " . $e->getMessage() . "\n";
}

// Test 2: Without backticks
$sql2 = "CREATE TABLE IF NOT EXISTS $name (test_col INT)";
echo "Test 2 (no backtick): ";
try {
    $pdo->exec($sql2);
    echo "OK\n";
    $pdo->exec("DROP TABLE IF EXISTS `$name`");
} catch (Exception $e) {
    echo "FAIL: " . $e->getMessage() . "\n";
}

// Test 3: With curly braces
$sql3 = "CREATE TABLE IF NOT EXISTS {test_table} (test_col INT)";
echo "Test 3 (curly braces): ";
try {
    $pdo->exec($sql3);
    echo "OK\n";
    $pdo->exec("DROP TABLE IF EXISTS `test_table`");
} catch (Exception $e) {
    echo "FAIL: " . $e->getMessage() . "\n";
}

echo "\nMySQL Version: " . $pdo->query('SELECT VERSION()')->fetchColumn() . "\n";
'''

print("\n=== Testing table name quoting ===")
sftp = c.open_sftp()
with sftp.open('/tmp/test_quoting.php', 'w') as f:
    f.write(test_php.encode('utf-8'))
sftp.close()
run(c, "php /tmp/test_quoting.php")

c.close()
