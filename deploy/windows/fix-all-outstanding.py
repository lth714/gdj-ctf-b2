"""Fix all remaining B1 deployment issues."""
import paramiko
import bcrypt  # Use Python bcrypt instead of PHP for hash generation

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
    print(f'  >>> {cmd[:200]}')
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

# =============================================================
# 1. Fix MySQL: create iptvadmin user with proper password
# =============================================================
print('\n[1] Fix MySQL iptvadmin user...')
# First check existing users
run('mysql -u root -e "SELECT user, host, plugin FROM mysql.user WHERE user IN (\'iptvadmin\', \'root\');" 2>&1', sudo=True)

# Drop and recreate iptvadmin to fix any issues
run('mysql -u root -e "DROP USER IF EXISTS \'iptvadmin\'@\'localhost\';" 2>&1', sudo=True)
run('mysql -u root -e "CREATE USER \'iptvadmin\'@\'localhost\' IDENTIFIED BY \'Iptv@Proxy#2024\';" 2>&1', sudo=True)
run('mysql -u root -e "GRANT ALL PRIVILEGES ON iptv_proxy.* TO \'iptvadmin\'@\'localhost\'; FLUSH PRIVILEGES;" 2>&1', sudo=True)

# Test connection
print('  Testing iptvadmin connection:')
run('mysql -u iptvadmin -p"Iptv@Proxy#2024" -e "SELECT 1 AS test;" 2>&1')

# =============================================================
# 2. Create admin user with Python bcrypt hash
# =============================================================
print('\n[2] Create admin user...')
# Generate bcrypt hash locally (avoids PHP quoting issues)
hash_b = bcrypt.hashpw(b'admin123', bcrypt.gensalt())
admin_hash = hash_b.decode('utf-8')
print(f'  Generated hash: {admin_hash}')

# Use mysql -e with the hash (handle $ escaping in shell)
# Write SQL to file then pipe to mysql
sql = f"INSERT INTO iptv_proxy.admins (username, password, description) VALUES ('admin', '{admin_hash}', 'System Admin') ON DUPLICATE KEY UPDATE password = VALUES(password); SELECT id, username, description FROM iptv_proxy.admins;"
fh = sftp.open('/home/gdadmin/setup_admin.sql', 'w')
fh.write(sql)
fh.close()

# Use cat to pipe the file to mysql via sudo
run('cat /home/gdadmin/setup_admin.sql | mysql 2>&1', sudo=True)

# =============================================================
# 3. Ensure storage dirs writable
# =============================================================
print('\n[3] Fix storage permissions...')
run('mkdir -p /opt/iptv-proxy/storage/logs /opt/iptv-proxy/storage/cache /opt/iptv-proxy/storage && chmod -R 777 /opt/iptv-proxy/storage && chown -R www-data:www-data /opt/iptv-proxy', sudo=True)

# =============================================================
# 4. Check PCRE/preg_match issue
# =============================================================
print('\n[4] Debug PCRE issue...')
run('php -r "echo PCRE_VERSION . PHP_EOL;" 2>&1')
run('php -r "var_dump(preg_match(\"/test/\", \"test\"));" 2>&1')
run('php -r "var_dump(preg_match(\"/^\/admin\/channels\/check\/(\d+)$/\", \"/admin/channels/check/5\"));" 2>&1')

# Maybe the PCRE compile options issue is in the actual regex patterns
# Let's check what the index.php regex actually looks like
run('grep -n "preg_match" /opt/iptv-proxy/public/index.php 2>&1')

# =============================================================
# 5. Test full web flow
# =============================================================
print('\n[5] Full web test...')
run('curl -sL http://localhost/ 2>&1 | grep -E "<title>|class=\"card-title\""')
run('curl -sL http://localhost/login 2>&1 | grep -E "<title>|class=\"card-title\""')
run('curl -sL http://localhost/reset-password 2>&1 | grep -E "<title>|class=\"card-title\""')

# =============================================================
# 6. Test password reset API
# =============================================================
print('\n[6] Test password reset...')
run('curl -s -X POST http://localhost/auth/reset-password -d "username=admin&new_password=att123456" 2>&1')

# =============================================================
# 7. Verify database state
# =============================================================
print('\n[7] Database state...')
run('mysql -u root -e "SELECT id, username, description FROM iptv_proxy.admins;" 2>&1', sudo=True)

# =============================================================
# 8. Verify sudo and operator
# =============================================================
print('\n[8] Environment verification...')
run('echo "www-data sudo:" && sudo -u www-data sudo -l 2>&1', sudo=True)
run('id operator 2>&1')
run('systemctl is-active php8.1-fpm nginx mysql redis 2>&1')

sftp.close()
ssh.close()
print('\n=== DONE ===')
