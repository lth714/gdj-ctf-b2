"""Fix MySQL admin user creation on B1."""
import paramiko

HOST = '192.168.120.10'
USER = 'gdadmin'
PWD = 'Gdadmin@123'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PWD, timeout=30)
print('[+] Connected')

def run(cmd, timeout=30, sudo=False):
    if sudo:
        cmd = f"echo '{PWD}' | sudo -S bash -c '{cmd}'"
    print(f'  >>> {cmd[:160]}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        for line in out.strip().split('\n')[:30]:
            print(f'      {line}')
    if err.strip() and ec != 0:
        for line in err.strip().split('\n')[:8]:
            print(f'      [stderr] {line}')
    return out, err, ec

# 1. Check MySQL state
print('\n[1] MySQL status...')
run('mysql -u root -e "SHOW DATABASES;" 2>&1', sudo=True)
run('mysql -u root -e "SELECT user, host FROM mysql.user WHERE user IN (\'iptvadmin\', \'root\');" 2>&1', sudo=True)

# 2. Check if iptv_proxy has tables
print('\n[2] iptv_proxy tables...')
run('mysql -u root iptv_proxy -e "SHOW TABLES;" 2>&1', sudo=True)
run('mysql -u root iptv_proxy -e "SELECT * FROM admins;" 2>&1', sudo=True)

# 3. Generate hash and insert admin user (using PHP script to avoid quoting hell)
print('\n[3] Creating admin user via PHP script...')
php_script = """<?php
$hash = password_hash('admin123', PASSWORD_DEFAULT);
$pdo = new PDO('mysql:host=127.0.0.1;dbname=iptv_proxy', 'root', '');
$stmt = $pdo->prepare("INSERT INTO admins (username, password, description) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE password = VALUES(password)");
$stmt->execute(['admin', $hash, 'System Admin']);
echo "Admin user created/updated. Hash: " . $hash;
"""
# Write the PHP script to server
script_cmd = f"cat > /tmp/create_admin.php << 'PHPEOF'\n{php_script}\nPHPEOF\nphp /tmp/create_admin.php 2>&1"
run(script_cmd, sudo=True, timeout=15)

# 4. Verify admin user
print('\n[4] Verify admin user...')
run('mysql -u root iptv_proxy -e "SELECT id, username, description, LENGTH(password) as pass_len FROM admins;" 2>&1', sudo=True)

# 5. Test web app
print('\n[5] Web test...')
run('curl -s http://localhost/ 2>&1 | head -5')
run('curl -s http://localhost/login 2>&1 | head -5')
run('curl -s http://localhost/reset-password 2>&1 | head -5')

# 6. Test password reset API
print('\n[6] Password reset API...')
run('curl -s -X POST http://localhost/auth/reset-password -H "X-Requested-With: XMLHttpRequest" -d "username=admin" -d "new_password=attacker123" 2>&1')

print('\n[DONE]')
ssh.close()
