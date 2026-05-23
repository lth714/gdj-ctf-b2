#!/usr/bin/env python3
"""Fix Drupal 7.57 remaining schema - use standalone PHP to avoid function conflicts"""
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
    exit_code = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  out: {out.strip()[:1500]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, exit_code

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Don't use bash to pass SQL - write a PHP script that does everything
# and put it on C2 via SFTP

php_fix = r'''<?php
/**
 * Standalone script to complete Drupal 7.57 installation.
 * Does NOT include module.inc to avoid function redeclaration.
 */
error_reporting(E_ALL);
ini_set('display_errors', 1);

define('DRUPAL_ROOT', '/var/www/drupal');

// Database connection
try {
    $pdo = new PDO(
        'mysql:host=localhost;dbname=drupal;charset=utf8mb4',
        'root',
        'R00t@Mysql#2024',
        array(PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION)
    );
} catch (PDOException $e) {
    die("DB connection failed: " . $e->getMessage() . "\n");
}

echo "Connected to database.\n";

// Get existing tables
$existing = array();
$stmt = $pdo->query("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='drupal'");
foreach ($stmt as $row) {
    $existing[] = strtolower($row['TABLE_NAME'] ?? $row[0]);
}
echo "Existing tables (" . count($existing) . "): " . implode(', ', $existing) . "\n\n";

// List of enabled modules from Drupal standard profile
$modules = array(
    'block', 'color', 'comment', 'contextual', 'dashboard', 'dblog',
    'field', 'field_sql_storage', 'field_ui', 'file', 'filter', 'help',
    'image', 'list', 'locale', 'menu', 'node', 'number', 'options',
    'overlay', 'path', 'rdf', 'search', 'shortcut', 'system', 'taxonomy',
    'text', 'toolbar', 'update', 'user',
);

// Process each module
foreach ($modules as $module) {
    $install_file = DRUPAL_ROOT . '/modules/' . $module . '/' . $module . '.install';
    if (!file_exists($install_file)) {
        continue;
    }

    // Parse the .install file for hook_schema
    $content = file_get_contents($install_file);

    // Extract schema array - look for function <module>_schema()
    if (!preg_match('/function\s+' . $module . '_schema\s*\([^)]*\)\s*\{/', $content)) {
        continue; // No schema function
    }

    echo "Processing module: $module\n";

    // Brute-force approach: use eval to get the schema
    // But in a safe way - execute the .install file, capture the schema
    $func_name = $module . '_schema';

    // Include the file (it will define the function)
    include_once $install_file;

    if (!function_exists($func_name)) {
        echo "  No schema function $func_name\n";
        continue;
    }

    $schema = $func_name();
    if (!is_array($schema)) {
        continue;
    }

    foreach ($schema as $table_name => $table_def) {
        $lower_name = strtolower($table_name);
        if (in_array($lower_name, $existing)) {
            continue;
        }

        echo "  Creating table: $table_name...\n";
        try {
            create_table_from_schema($pdo, $table_name, $table_def);
            $existing[] = $lower_name;
            echo "    OK\n";
        } catch (PDOException $e) {
            echo "    ERROR: " . $e->getMessage() . "\n";
        }
    }
}

echo "\nDone. Total tables: " . count($existing) . "\n";

/**
 * Create a MySQL table from Drupal 7 schema definition
 */
function create_table_from_schema($pdo, $table_name, $schema) {
    $fields = array();
    $primary_key = array();
    $indexes = array();
    $unique_keys = array();

    foreach ($schema['fields'] as $field_name => $field_def) {
        $sql = drupal_field_to_sql($field_name, $field_def);
        if ($sql) {
            $fields[] = $sql;
        }
    }

    // Primary key
    if (isset($schema['primary key'])) {
        $pk = $schema['primary key'];
        if (is_array($pk)) {
            $primary_key = $pk;
        } else {
            $primary_key = array($pk);
        }
    }

    // Unique keys
    if (isset($schema['unique keys'])) {
        foreach ($schema['unique keys'] as $key_name => $key_cols) {
            $unique_keys[] = "UNIQUE KEY `$key_name` (`" . implode('`, `', (array)$key_cols) . "`)";
        }
    }

    // Indexes
    if (isset($schema['indexes'])) {
        foreach ($schema['indexes'] as $index_name => $index_cols) {
            $indexes[] = "INDEX `$index_name` (`" . implode('`, `', (array)$index_cols) . "`)";
        }
    }

    $all_columns = array_merge($fields, $unique_keys);
    if (!empty($primary_key)) {
        $all_columns[] = "PRIMARY KEY (`" . implode('`, `', $primary_key) . "`)";
    }

    // Use backtick-quoted table name for reserved words
    $table_sql = "`$table_name`";

    $sql = "CREATE TABLE IF NOT EXISTS $table_sql (\n  " . implode(",\n  ", $all_columns) . "\n)";

    // Engine and charset
    $engine = 'InnoDB';
    $charset = 'utf8mb4';
    if (isset($schema['mysql_engine'])) {
        $engine = $schema['mysql_engine'];
    }

    $sql .= " ENGINE=$engine DEFAULT CHARSET=$charset";

    // Comment
    if (isset($schema['description'])) {
        $desc = $pdo->quote($schema['description']);
        $sql .= " COMMENT=$desc";
    }

    $pdo->exec($sql);

    // Create indexes separately (some need to be created after table)
    foreach ($indexes as $index_def) {
        try {
            $pdo->exec("ALTER TABLE $table_sql ADD $index_def");
        } catch (PDOException $e) {
            // Ignore duplicate index errors
            if ($e->getCode() != '42S21') {
                echo "    Index warning: " . $e->getMessage() . "\n";
            }
        }
    }
}

/**
 * Convert Drupal 7 field definition to SQL column definition
 */
function drupal_field_to_sql($field_name, $field_def) {
    $type_map = array(
        'serial' => 'INT NOT NULL AUTO_INCREMENT',
        'int' => 'INT',
        'varchar' => 'VARCHAR',
        'char' => 'CHAR',
        'text' => 'TEXT',
        'blob' => 'BLOB',
    );

    $type = isset($field_def['type']) ? $field_def['type'] : 'varchar';

    // Size
    $size_sql = '';
    if (isset($field_def['length'])) {
        $size_sql = '(' . $field_def['length'] . ')';
    } elseif ($type === 'varchar') {
        $size_sql = '(255)';
    } elseif ($type === 'int') {
        $size = isset($field_def['size']) ? $field_def['size'] : 'normal';
        switch ($size) {
            case 'tiny': $size_sql = ''; $type = 'TINYINT'; break;
            case 'small': $size_sql = ''; $type = 'SMALLINT'; break;
            case 'medium': $size_sql = ''; $type = 'MEDIUMINT'; break;
            case 'big': $size_sql = ''; $type = 'BIGINT'; break;
            default: $size_sql = ''; break;
        }
    } elseif ($type === 'serial') {
        // serial is already handled, but support for non-auto-increment
        if (isset($field_def['not null']) && !$field_def['not null']) {
            $type_map['serial'] = 'INT';
        }
    }

    if (!isset($type_map[$type])) {
        $sql_type = strtoupper($type) . $size_sql;
    } else {
        $sql_type = $type_map[$type] . $size_sql;
    }

    // NOT NULL
    $not_null = '';
    if (isset($field_def['not null']) && $field_def['not null']) {
        $not_null = ' NOT NULL';
    } elseif ($type === 'serial') {
        $not_null = ' NOT NULL';
    }

    // Default
    $default = '';
    if (isset($field_def['default'])) {
        if (is_string($field_def['default'])) {
            $default = " DEFAULT '" . addslashes($field_def['default']) . "'";
        } elseif (is_numeric($field_def['default'])) {
            $default = " DEFAULT " . $field_def['default'];
        }
    }

    // Unsigned
    $unsigned = '';
    if (isset($field_def['unsigned']) && $field_def['unsigned']) {
        $unsigned = ' UNSIGNED';
    }

    // Comment (description)
    $comment = '';
    if (isset($field_def['description'])) {
        $comment = " COMMENT '" . addslashes($field_def['description']) . "'";
    }

    return "`$field_name` $sql_type$unsigned$not_null$default$comment";
}

echo "\nFinal table count verification:\n";
$result = $pdo->query("SELECT COUNT(*) AS cnt FROM information_schema.TABLES WHERE TABLE_SCHEMA='drupal'");
$row = $result->fetch(PDO::FETCH_ASSOC);
echo "Total tables in drupal database: " . $row['cnt'] . "\n";
'''

print("Writing PHP fix script via SFTP...")
sftp = c.open_sftp()
with sftp.open('/tmp/drupal_fix_v2.php', 'w') as f:
    f.write(php_fix.encode('utf-8'))
sftp.close()
print("Written.")

print("\n=== Running PHP fix script ===")
out, err, ec = run(c,
    "cd /var/www/drupal && echo 'Gdadmin@123' | sudo -S php /tmp/drupal_fix_v2.php 2>&1",
    timeout=120)

print("\n=== Final table count ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT COUNT(*) AS cnt FROM information_schema.TABLES WHERE TABLE_SCHEMA=\"drupal\";' 2>/dev/null")

print("\n=== Test HTTP ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c, "curl -s http://localhost/ 2>/dev/null | grep -o '<title>[^<]*</title>'")

# Also check the PHP error log from Apache
print("\n=== Check Apache PHP error ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -i 'error\|fatal\|exception' /var/log/apache2/error.log | tail -5")

c.close()
print("\nDone!")
