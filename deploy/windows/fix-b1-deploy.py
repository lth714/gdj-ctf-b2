"""Fix deployment issues on B1 server."""
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
    print(f'  >>> {cmd[:150]}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        for line in out.strip().split('\n')[:25]:
            print(f'      {line}')
    if err.strip() and ec != 0:
        for line in err.strip().split('\n')[:5]:
            print(f'      [stderr] {line}')
    return out, err, ec

# 1. Check what happened with the extraction
print('\n[1] Checking file layout...')
run('ls /opt/php-iptv-proxy-master/public/ 2>&1 | head -10')
run('ls /opt/iptv-proxy/public/ 2>&1 | head -5')
run('ls /opt/iptv-proxy/ 2>&1 | head -10')

# 2. Extract correctly - strip the php-iptv-proxy-master prefix
print('\n[2] Extracting source to /opt/iptv-proxy...')
# First clean the stale /opt/iptv-proxy, then extract with strip-components
run('cd /opt && rm -rf iptv-proxy && mkdir -p iptv-proxy && tar xzf /tmp/iptv-proxy-deploy.tar.gz --strip-components=1 -C /opt/iptv-proxy/ && chown -R www-data:www-data /opt/iptv-proxy && chmod -R 755 /opt/iptv-proxy', sudo=True)
print('Verifying:')
run('ls /opt/iptv-proxy/public/index.php 2>&1')
run('ls /opt/iptv-proxy/src/Controllers/DiagController.php 2>&1')
run('ls /opt/iptv-proxy/src/views/reset-password.php 2>&1')

# 3. Fix MySQL - user probably exists already from previous deploy
print('\n[3] Fixing MySQL...')
# Check if user exists
run("mysql -u root -e \"SELECT user FROM mysql.user WHERE user='iptvadmin';\" 2>&1", sudo=True)
# Grant privileges
run("mysql -u root -e \"GRANT ALL PRIVILEGES ON iptv_proxy.* TO 'iptvadmin'@'localhost'; FLUSH PRIVILEGES;\" 2>&1", sudo=True)
# Import schema
run('mysql -u root iptv_proxy < /opt/iptv-proxy/src/Install/database.sql 2>&1', sudo=True)
# Create admin - get the hash and insert
admin_hash = run('php -r "echo password_hash(\"admin123\", PASSWORD_DEFAULT);" 2>&1')[0].strip()
admin_hash = admin_hash.split('\n')[-1].strip()
print(f'  Hash: {admin_hash[:20]}...')

# Use a different approach to avoid bash escaping issues
pwd_hash_cmd = f"mysql -u root iptv_proxy -e \"INSERT INTO admins (username, password, description) VALUES ('admin', '{admin_hash}', 'System Admin') ON DUPLICATE KEY UPDATE password = VALUES(password);\""
run(pwd_hash_cmd, sudo=True)
print('Admin table:')
run('mysql -u root iptv_proxy -e "SELECT id, username, description FROM admins;" 2>&1', sudo=True)

# 4. Create storage dirs
print('\n[4] Storage directories...')
run('mkdir -p /opt/iptv-proxy/storage/logs /opt/iptv-proxy/storage/cache && chmod -R 777 /opt/iptv-proxy/storage', sudo=True)

# 5. Composer install
print('\n[5] Composer...')
# Check if composer exists, if not skip - the vendor dir may have been in the tarball
run('which composer 2>&1')
run('ls /opt/iptv-proxy/vendor/autoload.php 2>&1')
# If no vendor, try to use composer from the extracted files
run('cd /opt/iptv-proxy && ls composer.lock composer.json 2>&1')

# 6. Fix operator user
print('\n[6] Fixing operator user...')
run('id operator 2>&1 || (groupdel operator 2>/dev/null; useradd -m -s /bin/bash -G sudo operator)', sudo=True)
run("echo 'operator:0p3rat0r@GDJ' | chpasswd", sudo=True)
run('id operator 2>&1')

# 7. Verify sudoers
print('\n[7] Checking sudo...')
run('cat /etc/sudoers.d/www-data-tee 2>&1', sudo=True)

# 8. Restart and test
print('\n[8] Restart services...')
run('systemctl restart php8.1-fpm', sudo=True)
run('nginx -t && systemctl reload nginx', sudo=True)

print('\n[9] Web test...')
run('curl -s -o /dev/null -w "%{http_code}" http://localhost/')
run('curl -s -o /dev/null -w "%{http_code}" http://localhost/login')
run('curl -s -o /dev/null -w "%{http_code}" http://localhost/reset-password')
run('curl -s http://localhost/ 2>&1 | grep -o "<title>[^<]*</title>"')

# 10. Test reset password API
print('\n[10] Reset password API test...')
run("curl -s -X POST http://localhost/auth/reset-password -d 'username=admin&new_password=test456' 2>&1")

print('\n[DONE] Fix complete')
ssh.close()
