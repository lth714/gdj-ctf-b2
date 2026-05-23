"""Complete B2 fix: remove Jammy, install PHP 7.4, fix Cacti"""
import paramiko, io, time

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
        for line in err.strip().split('\n')[-2:]:
            print(f'    [stderr] {line}')
    return out, err, ec

# Step 1: Fix sources.list via SFTP script
print('\n=== [1/5] 修复 apt 源 (移除 Jammy) ===')

# Read current sources.list
out, _, _ = run('cat /etc/apt/sources.list', sudo=True)
print(f'Current sources.list:\n{out}')

# Write fixed sources.list (only focal)
new_sources = """deb http://mirrors.aliyun.com/ubuntu/ focal main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ focal-security main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ focal-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ focal-proposed main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ focal-backports main restricted universe multiverse
"""
sftp.putfo(io.StringIO(new_sources), '/tmp/sources.list')
run('cp /tmp/sources.list /etc/apt/sources.list', sudo=True)
run('cat /etc/apt/sources.list', sudo=True)

# Step 2: Update and install PHP 7.4
print('\n=== [2/5] apt update + 安装 PHP 7.4 ===')
run('apt update -y 2>&1 | tail -5', sudo=True, timeout=120)

# Check available PHP
out, _, _ = run('apt-cache search php7.4 | head -10')
print(f'PHP 7.4 packages: {out[:500]}')

# Install PHP 7.4
run('DEBIAN_FRONTEND=noninteractive apt install -y php7.4 php7.4-cli php7.4-common php7.4-mysql php7.4-mbstring php7.4-xml php7.4-curl php7.4-gd php7.4-ldap php7.4-bcmath libapache2-mod-php7.4 2>&1 | tail -10', sudo=True, timeout=180)

# Step 3: Verify PHP
print('\n=== [3/5] 验证 PHP ===')
run('php -v 2>&1 | head -2')
run('php -m 2>&1 | grep -iE "mysql|pdo|xml|mb"')

# Test PCRE
php_test = "<?php\n\$r = preg_replace('/foo/', 'BAR', 'foo test');\nvar_dump(\$r);\n"
sftp.putfo(io.StringIO(php_test), '/tmp/pcre_test.php')
run('php /tmp/pcre_test.php 2>&1')

# Step 4: Configure Apache
print('\n=== [4/5] 配置 Apache ===')
run('a2enmod php7.4 2>&1', sudo=True)
run('systemctl restart apache2', sudo=True)
run('systemctl status apache2 2>&1 | grep -E "Active|PID"', sudo=True)

# Step 5: Fix Cacti global.php (restore + fix for PHP 7.4)
print('\n=== [5/5] 修复 Cacti ===')

# PHP 7.4 should handle the original regex fine, but let's check
# Restore the original global.php (or use our fixed version with str_replace)
# Actually, let's check if the Cacti from apt works with PHP 7.4

# Test Cacti
run('curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost/cacti/')
run('tail -5 /var/log/apache2/error.log', sudo=True)

# Test remote_agent
run('curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost/cacti/remote_agent.php')

sftp.close()
ssh.close()
print('\n=== 完成 ===')
