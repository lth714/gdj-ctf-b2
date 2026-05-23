#!/usr/bin/env python3
"""Fix Drupal 7.57 installation - system table is MySQL 8 reserved word"""
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
    exit_code = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  out: {out.strip()[:1500]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, exit_code

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# Check what tables exist
print("=== Existing tables ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM drupal;' 2>/dev/null")

# Check if 'system' table exists
print("\n=== Check system table ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'DESCRIBE drupal.system;' 2>/dev/null")

# Try to create system table manually with backticks
print("\n=== Try creating system table ===")
create_system = """CREATE TABLE IF NOT EXISTS drupal.`system` (
  `filename` VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'The path of the primary file for this item, relative to the Drupal root',
  `name` VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'The name of the item (e.g. module filename without .module extension)',
  `type` VARCHAR(12) NOT NULL DEFAULT '' COMMENT 'The type of the item (module, theme, or theme_engine)',
  `owner` VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'A theme\'s parent theme, if the theme is a sub-theme',
  `status` INT NOT NULL DEFAULT 0 COMMENT 'Boolean indicating whether or not this item is enabled',
  `bootstrap` INT NOT NULL DEFAULT 0 COMMENT 'Boolean indicating whether this module is loaded during Drupal bootstrap (0 = no, 1 = yes)',
  `schema_version` SMALLINT NOT NULL DEFAULT -1 COMMENT 'The module\'s database schema version number',
  `weight` INT NOT NULL DEFAULT 0 COMMENT 'The order in which this module\'s hooks should be invoked',
  `info` BLOB DEFAULT NULL COMMENT 'The array contained in this item\'s .info file',
  PRIMARY KEY (`filename`),
  INDEX `name_type_parts` (`name`, `type`),
  INDEX `system_list` (`status`, `bootstrap`, `type`, `weight`, `name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='A list of all modules, themes, and theme engines that are or have been installed in Drupal.'"""

run(c, f"mysql -u root -p'R00t@Mysql#2024' -e \"{create_system}\" drupal 2>/dev/null && echo 'SYSTEM_TABLE_CREATED'")

# Also check what other potential reserved word tables exist
# In Drupal 7, these might be reserved in MySQL 8:
# No other Drupal 7 table names conflict, but let's verify
print("\n=== Check for failed tables (reserved word conflicts) ===")
run(c, "echo 'Gdadmin@123' | sudo -S grep -rn \"'system'\" /var/www/drupal/modules/system/system.install | head -5")

# Now let's try to complete the install by running the remaining schema
# Let's use a PHP script that loads the system module schema and creates missing tables

fix_php = r'''<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

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
require_once DRUPAL_ROOT . '/includes/module.inc';
require_once DRUPAL_ROOT . '/includes/common.inc';
require_once DRUPAL_ROOT . '/includes/schema.inc';
require_once DRUPAL_ROOT . '/includes/unicode.inc';

drupal_bootstrap(DRUPAL_BOOTSTRAP_DATABASE);

// Read the system module's install file to get schema
$profile = 'standard';
require_once DRUPAL_ROOT . '/profiles/' . $profile . '/' . $profile . '.profile';

// Get ALL modules from the standard profile and system
$required_modules = array(
    'system', 'user', 'node', 'block', 'comment', 'dblog',
    'field', 'filter', 'file', 'help', 'image', 'list',
    'menu', 'number', 'options', 'path', 'taxonomy', 'text',
    'update', 'shortcut', 'toolbar', 'rdf', 'search'
);

// Also load the standard profile modules
$profile_info = drupal_parse_info_file(DRUPAL_ROOT . '/profiles/standard/standard.info');
$all_modules = array();
if (isset($profile_info['dependencies'])) {
    foreach ($profile_info['dependencies'] as $mod) {
        $all_modules[] = $mod;
    }
}

echo "Profile dependencies: " . implode(', ', $all_modules) . "\n\n";

// Function to load module includes
function module_load_install($module) {
    $file = DRUPAL_ROOT . '/modules/' . $module . '/' . $module . '.install';
    if (file_exists($file)) {
        require_once $file;
    }
}

// Get existing tables
$existing_tables = array();
$result = db_query("SHOW TABLES FROM drupal");
foreach ($result as $row) {
    $key = 'Tables_in_drupal';
    $existing_tables[] = strtolower($row->$key);
}
echo "Existing tables: " . implode(', ', $existing_tables) . "\n\n";

// Check what's missing
foreach ($all_modules as $module) {
    $install_file = DRUPAL_ROOT . '/modules/' . $module . '/' . $module . '.install';
    if (!file_exists($install_file)) {
        echo "SKIP $module: no .install file\n";
        continue;
    }

    require_once $install_file;
    $schema_func = $module . '_schema';
    if (!function_exists($schema_func)) {
        echo "SKIP $module: no schema function\n";
        continue;
    }

    $schema = $schema_func();
    foreach ($schema as $table_name => $table_def) {
        $lower_name = strtolower($table_name);
        if (in_array($lower_name, $existing_tables)) {
            continue; // Already exists
        }

        echo "Creating table: $table_name from module $module...\n";
        try {
            db_create_table($table_name, $table_def);
            echo "  OK\n";
        } catch (Exception $e) {
            echo "  ERROR: " . $e->getMessage() . "\n";
            // If system table, try with backticks
            if (strtolower($table_name) === 'system') {
                echo "  Retrying system table with backtick quoting...\n";
                try {
                    db_query("CREATE TABLE IF NOT EXISTS {system} LIKE `system`");
                } catch (Exception $e2) {
                    echo "  Retry also failed: " . $e2->getMessage() . "\n";
                }
            }
        }
    }
}

echo "\nDONE\n";
'''

print("\n=== Writing PHP fix script ===")
sftp = c.open_sftp()
with sftp.open('/tmp/drupal_fix_schema.php', 'w') as f:
    f.write(fix_php.encode('utf-8'))
sftp.close()

print("\n=== Running PHP fix script ===")
out, err, ec = run(c,
    "cd /var/www/drupal && echo 'Gdadmin@123' | sudo -S php /tmp/drupal_fix_schema.php 2>&1",
    timeout=120)

print("\n=== Final table count ===")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT COUNT(*) AS table_count FROM information_schema.TABLES WHERE TABLE_SCHEMA=\"drupal\";' 2>/dev/null")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW TABLES FROM drupal;' 2>/dev/null")

print("\n=== Test HTTP ===")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
run(c, "curl -s http://localhost/ | grep -o '<title>[^<]*</title>'")

c.close()
print("\nDone!")
