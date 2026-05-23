"""Fix B2: force clean PHP packages, install PHP 7.4 from focal"""
import paramiko, io

HOST = '192.168.120.20'
USER = 'gdadmin'
PWD = 'Gdadmin@123'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PWD, timeout=30)
sftp = ssh.open_sftp()
print('[+] Connected')

def run(cmd, timeout=120, sudo=False):
    if sudo:
        cmd = f"echo '{PWD}' | sudo -S bash -c '{cmd}'"
    print(f'>>> {cmd[:200]}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        for line in out.strip().split('\n')[-6:]:
            print(f'    {line}')
    if err.strip() and ec != 0:
        for line in err.strip().split('\n')[-3:]:
            print(f'    [stderr] {line}')
    return out, err, ec

# Step 1: Show current PHP package state
print('\n=== [1/4] 当前 PHP 包状态 ===')
run('dpkg -l | grep -i php 2>&1 | head -20', sudo=True)
run('apt-cache policy php-common 2>&1')

# Step 2: Force remove ALL PHP packages and install PHP 7.4
print('\n=== [2/4] 强制清理 + 安装 PHP 7.4 ===')
# Remove ALL PHP packages
run('DEBIAN_FRONTEND=noninteractive apt remove --purge -y php-common php8.1* php7.4* libapache2-mod-php* 2>&1 | tail -5', sudo=True, timeout=120)

# Now install PHP 7.4 from focal
cmd = 'DEBIAN_FRONTEND=noninteractive apt install -y php7.4 php7.4-cli php7.4-common php7.4-mysql php7.4-mbstring php7.4-xml php7.4-curl php7.4-gd php7.4-ldap php7.4-bcmath libapache2-mod-php7.4 2>&1 | tail -15'
out, err, ec = run(cmd, sudo=True, timeout=180)

# If that fails, try with --fix-broken
if ec != 0:
    print('\n[!] 尝试 apt --fix-broken install...')
    run('DEBIAN_FRONTEND=noninteractive apt --fix-broken install -y 2>&1 | tail -5', sudo=True, timeout=120)
    out, err, ec = run(cmd, sudo=True, timeout=180)

# Step 3: Verify
print('\n=== [3/4] 验证 PHP 7.4 ===')
run('php -v 2>&1 | head -2')

# Test PCRE
php_test = "<?php\n\$r = preg_replace('/foo/', 'BAR', 'foo test');\nvar_dump(\$r);\n"
sftp.putfo(io.StringIO(php_test), '/tmp/pcre_test.php')
run('php /tmp/pcre_test.php 2>&1')

# Test Cacti regex
php_test2 = '<?php\n$r = preg_replace("/\s*[\r\n]+\s*/", " ", "hello\nworld");\nvar_dump($r);\n'
sftp.putfo(io.StringIO(php_test2), '/tmp/pcre_test2.php')
run('php /tmp/pcre_test2.php 2>&1')

# Step 4: Apache
print('\n=== [4/4] Apache + Cacti ===')
run('a2enmod php7.4 2>&1', sudo=True)
run('systemctl restart apache2', sudo=True)

# Check Cacti
run('curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost/cacti/')
run('curl -s http://localhost/cacti/ 2>&1 | head -10')

sftp.close()
ssh.close()
print('\n=== 完成 ===')
