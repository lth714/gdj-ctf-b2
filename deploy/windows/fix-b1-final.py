"""Final fix for B1 php-iptv-proxy deployment."""
import paramiko

HOST = '192.168.120.10'
USER = 'gdadmin'
PWD = 'Gdadmin@123'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PWD, timeout=30)
print('[+] Connected')
sftp = ssh.open_sftp()

def run(cmd, timeout=30, sudo=False):
    if sudo:
        cmd = f"echo '{PWD}' | sudo -S bash -c \"{cmd}\""
    print(f'  >>> {cmd[:180]}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        for line in out.strip().split('\n')[:30]:
            print(f'      {line}')
    if err.strip() and ec != 0:
        for line in err.strip().split('\n')[:5]:
            print(f'      [stderr] {line}')
    return out, err, ec

# 1. Upload admin creation PHP script via SFTP
print('\n[1] Uploading create_admin.php via SFTP...')
admin_script = """<?php
error_reporting(E_ALL);
$hash = password_hash('admin123', PASSWORD_DEFAULT);
try {
    $pdo = new PDO('mysql:host=127.0.0.1;dbname=iptv_proxy', 'root', '');
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $stmt = $pdo->prepare("INSERT INTO admins (username, password, description) VALUES (:u, :p, :d) ON DUPLICATE KEY UPDATE password = VALUES(password)");
    $stmt->execute(['u' => 'admin', 'p' => $hash, 'd' => 'System Admin']);
    echo "OK: admin created. Hash: " . $hash . "\\n";
} catch (Exception $e) {
    echo "ERROR: " . $e->getMessage() . "\\n";
}
"""
fh = sftp.open('/home/gdadmin/create_admin.php', 'w')
fh.write(admin_script)
fh.close()
print('  [+] Uploaded to /home/gdadmin/create_admin.php')

# 2. Run it
print('\n[2] Running create_admin.php...')
run('php /home/gdadmin/create_admin.php 2>&1', sudo=True)

# 3. Verify
print('\n[3] MySQL admin check...')
run('mysql -u root iptv_proxy -e "SELECT id, username, description FROM admins;" 2>&1', sudo=True)

# 4. Debug: check services and error logs
print('\n[4] Service check...')
run('systemctl status php8.1-fpm 2>&1 | grep -E "Active|PID|Tasks"', sudo=True)
run('systemctl status nginx 2>&1 | grep -E "Active|PID"', sudo=True)

# 5. Test the app with curl -L (follow redirects)
print('\n[5] Web test with redirect...')
run('curl -sL -o /dev/null -w "HTTP %{http_code}" http://localhost/ 2>&1')
run('curl -sL http://localhost/ 2>&1 | grep -o "<title>[^<]*</title>" || echo "no title"')

# 6. Check PHP error
print('\n[6] Recent PHP errors...')
run('tail -10 /var/log/php8.1-fpm.log 2>&1', sudo=True)
run('tail -5 /var/log/nginx/error.log 2>&1', sudo=True)
run('journalctl -u php8.1-fpm --no-pager -n 5 2>&1', sudo=True)

# 7. Direct PHP index test
print('\n[7] Direct PHP test...')
run('cd /opt/iptv-proxy/public && php index.php 2>&1 | head -10', timeout=10)

# 8. Nginx error log specifically
print('\n[8] Nginx error log tail...')
run('tail -20 /var/log/nginx/error.log 2>&1', sudo=True)

sftp.close()
ssh.close()
print('\n[DONE]')
