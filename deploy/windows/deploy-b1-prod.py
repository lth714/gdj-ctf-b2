"""Deploy php-iptv-proxy to B1 DMZ server (192.168.120.10)."""
import paramiko
import os
import sys

HOST = '192.168.120.10'
USER = 'gdadmin'
PWD = 'Gdadmin@123'
TARBALL = 'E:/vibecoding/gdj_ctf/iptv-proxy-deploy.tar.gz'
REMOTE_TAR = '/tmp/iptv-proxy-deploy.tar.gz'
TARGET_DIR = '/opt/iptv-proxy'

def main():
    print(f'[*] Connecting to {HOST}...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PWD, timeout=30)
    print('[+] Connected')

    def run(cmd, timeout=30, sudo=False):
        if sudo:
            cmd = f"echo '{PWD}' | sudo -S bash -c '{cmd}'"
        print(f'  >>> {cmd[:140]}')
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        ec = stdout.channel.recv_exit_status()
        if out.strip():
            for line in out.strip().split('\n')[:20]:
                print(f'      {line}')
        if err.strip() and ec != 0:
            for line in err.strip().split('\n')[:5]:
                print(f'      [stderr] {line}')
        return out, err, ec

    # Step 1: Upload tarball
    print(f'\n[1/8] Uploading tarball ({os.path.getsize(TARBALL)/1024:.0f} KB)...')
    sftp = ssh.open_sftp()
    sftp.put(TARBALL, REMOTE_TAR)
    sftp.close()
    print('  [+] Upload complete')

    # Step 2: Clean old files and extract
    print('\n[2/8] Extracting source code...')
    run(f'rm -rf {TARGET_DIR}/* {TARGET_DIR}/.[!.]* 2>/dev/null; '
        f'tar xzf {REMOTE_TAR} -C /opt/ && '
        f'chown -R www-data:www-data {TARGET_DIR} && '
        f'chmod -R 755 {TARGET_DIR} && '
        f'ls {TARGET_DIR}/public/index.php && echo "EXTRACT_OK"',
        sudo=True, timeout=30)

    # Step 3: Create storage directories
    print('\n[3/8] Creating writable storage directories...')
    run(f'mkdir -p {TARGET_DIR}/storage/logs {TARGET_DIR}/storage/cache && '
        f'chmod -R 777 {TARGET_DIR}/storage',
        sudo=True, timeout=10)

    # Step 4: Database setup
    print('\n[4/8] Setting up database...')
    run("mysql -u root -e \"CREATE DATABASE IF NOT EXISTS iptv_proxy CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;\"", sudo=True)
    run("mysql -u root -e \"CREATE USER IF NOT EXISTS 'iptvadmin'@'localhost' IDENTIFIED BY 'Iptv@Proxy#2024';\"", sudo=True)
    run("mysql -u root -e \"GRANT ALL PRIVILEGES ON iptv_proxy.* TO 'iptvadmin'@'localhost'; FLUSH PRIVILEGES;\"", sudo=True)
    # Import schema
    run(f"mysql -u root iptv_proxy < {TARGET_DIR}/src/Install/database.sql 2>&1", sudo=True)
    # Create admin user
    admin_hash = run(
        "php -r \"echo password_hash('admin123', PASSWORD_DEFAULT);\"",
        timeout=10)[0].strip()
    # Get only the last line (the hash) to avoid PHP warnings
    admin_hash = admin_hash.split('\n')[-1].strip()
    print(f'  Admin hash: {admin_hash[:20]}...')
    run(f"mysql -u root iptv_proxy -e \"INSERT INTO admins (username, password, description) VALUES ('admin', '{admin_hash}', 'System Admin') ON DUPLICATE KEY UPDATE password = VALUES(password);\"", sudo=True)
    # Verify
    print('  Verifying admin user:')
    run("mysql -u root iptv_proxy -e \"SELECT id, username, description FROM admins;\"", sudo=True)

    # Step 5: Composer install
    print('\n[5/8] Installing Composer dependencies...')
    if 'composer' not in run('which composer 2>&1', timeout=5)[0]:
        print('  Installing Composer...')
        run('php -r "copy(\'https://install.phpcomposer.com/installer\', \'composer-setup.php\');" && php composer-setup.php --quiet && rm composer-setup.php', timeout=60)
        run('mv composer.phar /usr/local/bin/composer', sudo=True)
    run(f'cd {TARGET_DIR} && composer install --no-dev --optimize-autoloader 2>&1 | tail -5', timeout=120)

    # Step 6: sudo tee backdoor
    print('\n[6/8] Setting up sudo tee privesc backdoor (B-6)...')
    run("bash -c 'echo \"www-data ALL=(root) NOPASSWD: /usr/bin/tee\" > /etc/sudoers.d/www-data-tee && chmod 440 /etc/sudoers.d/www-data-tee'", sudo=True)
    print('  Verifying:')
    run('cat /etc/sudoers.d/www-data-tee', sudo=True)

    # Step 7: Create operator user
    print('\n[7/8] Creating operator user...')
    run('id operator 2>&1 || useradd -m -s /bin/bash operator', sudo=True)
    run("echo 'operator:0p3rat0r@GDJ' | chpasswd", sudo=True)
    run('usermod -aG sudo operator', sudo=True)
    run('id operator 2>&1')

    # Step 8: Restart services and verify
    print('\n[8/8] Restarting PHP-FPM & verifying...')
    run('systemctl restart php8.1-fpm', sudo=True)
    run('nginx -t && systemctl reload nginx', sudo=True, timeout=15)

    print('\n' + '='*60)
    print('VERIFICATION')
    print('='*60)
    print('\n--- Web endpoints ---')
    run('curl -s -o /dev/null -w "GET / -> %{http_code}\n" http://localhost/')
    run('curl -s -o /dev/null -w "GET /login -> %{http_code}\n" http://localhost/login')
    run('curl -s -o /dev/null -w "GET /reset-password -> %{http_code}\n" http://localhost/reset-password')

    print('\n--- Password reset API ---')
    run("curl -s -X POST http://localhost/auth/reset-password -d 'username=admin&new_password=test123'")

    print('\n--- MySQL admin verify ---')
    run("mysql -u root iptv_proxy -e \"SELECT id, username FROM admins;\"", sudo=True)

    print('\n--- sudo tee verify ---')
    run("sudo -u www-data sudo -l 2>&1", sudo=True)

    print('\n--- operator verify ---')
    run('id operator 2>&1')

    print('\n[✓] Deployment complete!')

    ssh.close()

if __name__ == '__main__':
    main()
