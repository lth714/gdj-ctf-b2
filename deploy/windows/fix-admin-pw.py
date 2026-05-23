"""Fix admin password — SFTP SQL file to avoid shell $ escaping."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.120.10', username='gdadmin', password='Gdadmin@123', timeout=30)

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    print(f'>>> {cmd[:200]}')
    if out.strip(): print(f'  {out.strip()[:600]}')
    if err.strip() and ec != 0: print(f'  [stderr] {err.strip()[:200]}')
    return out, err, ec

# Step 1: Generate hash via PHP CLI
print('[1] Generate PHP bcrypt hash...')
out, _, _ = run("php -r \"echo password_hash('admin123', PASSWORD_DEFAULT);\" 2>&1")
admin_hash = out.strip()
print(f'  Hash: {admin_hash}')

# Step 2: Write SQL file via SFTP (avoids shell $ escaping)
print('[2] Write SQL via SFTP...')
sql = f"UPDATE iptv_proxy.admins SET password = '{admin_hash}' WHERE username = 'admin';"
sftp = ssh.open_sftp()
fh = sftp.open('/home/gdadmin/fix_pw.sql', 'w')
fh.write(sql)
fh.close()
sftp.close()

# Step 3: Execute SQL via mysql (pipe file, not inline)
print('[3] Execute SQL...')
run("echo 'Gdadmin@123' | sudo -S bash -c 'mysql -u root < /home/gdadmin/fix_pw.sql' 2>&1")

# Step 4: Verify
print('[4] Verify hash in DB...')
run("echo 'Gdadmin@123' | sudo -S mysql -u root -e \"SELECT id, username, LEFT(password, 50) FROM iptv_proxy.admins WHERE username='admin';\" 2>&1")

# Step 5: Test login
print('[5] Test login...')
run('curl -s -X POST http://localhost/auth/login -d "username=admin&password=admin123" -H "X-Requested-With: XMLHttpRequest"')

ssh.close()
