"""Fix config.php and create admin user."""
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
        cmd = f"echo '{PWD}' | sudo -S {cmd}"
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

# 1. Fix config.php - replace with proper syntax
print('\n[1] Fixing config.php...')
config_content = """<?php
return [
    'db' => [
        'host' => '127.0.0.1',
        'port' => 3306,
        'dbname' => 'iptv_proxy',
        'username' => 'iptvadmin',
        'password' => 'Iptv@Proxy#2024',
        'charset' => 'utf8mb4',
    ],
    'redis' => [
        'host' => '127.0.0.1',
        'port' => 6379,
        'password' => '',
    ],
    'app' => [
        'debug' => false,
        'site_name' => 'IPTV Proxy System',
    ],
];
"""
fh = sftp.open('/home/gdadmin/config.php', 'w')
fh.write(config_content)
fh.close()
run('cp /home/gdadmin/config.php /opt/iptv-proxy/config/config.php', sudo=True)
print('  New config:')
run('cat /opt/iptv-proxy/config/config.php', sudo=True)

# 2. Create admin user via mysql CLI (uses socket auth, not TCP)
print('\n[2] Generate admin password hash...')
hash_result = run('php -r "echo password_hash(\"admin123\", PASSWORD_DEFAULT);" 2>&1', timeout=10)[0]
admin_hash = hash_result.strip().split('\n')[-1].strip()
print(f'  Hash: {admin_hash}')

# Write SQL file via SFTP
sql_content = f"INSERT INTO iptv_proxy.admins (username, password, description) VALUES ('admin', '{admin_hash}', 'System Admin') ON DUPLICATE KEY UPDATE password = VALUES(password);"
fh = sftp.open('/home/gdadmin/insert_admin.sql', 'w')
fh.write(sql_content)
fh.close()
run('mysql < /home/gdadmin/insert_admin.sql 2>&1', sudo=True)

# 3. Verify
print('\n[3] Verify admin in MySQL...')
run('mysql -u root -e "SELECT id, username, description, LEFT(password, 30) as pass FROM iptv_proxy.admins;" 2>&1', sudo=True)

# 4. Test web
print('\n[4] Web test...')
run('curl -sL -o /dev/null -w "HTTP %{http_code}" http://localhost/ 2>&1')
run('curl -sL http://localhost/ 2>&1 | grep -o "<title>[^<]*</title>"')
run('curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost/reset-password 2>&1')
run('curl -sL http://localhost/reset-password 2>&1 | grep -o "<title>[^<]*</title>"')

# 5. Test reset password API
print('\n[5] Test reset password API...')
run('curl -s -X POST http://localhost/auth/reset-password -d "username=admin&new_password=hack123" 2>&1')

# 6. Check Nginx error log
print('\n[6] Recent Nginx errors...')
run('tail -5 /var/log/nginx/error.log 2>&1', sudo=True)

sftp.close()
ssh.close()
print('\n[DONE]')
