"""Fix B2 PHP by removing Jammy repos and installing PHP 7.4 from Focal"""
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
        for line in out.strip().split('\n')[-8:]:
            print(f'    {line}')
    if err.strip() and ec != 0:
        for line in err.strip().split('\n')[-3:]:
            print(f'    [stderr] {line}')
    return out, err, ec

# Step 1: Check current apt sources
print('\n=== [1/6] 检查 apt 源 ===')
run('cat /etc/apt/sources.list | grep -v "^#" | grep -v "^$"', sudo=True)
run('ls /etc/apt/sources.list.d/', sudo=True)

# Step 2: Remove Jammy sources from sources.list
print('\n=== [2/6] 移除 Jammy apt 源 ===')
# Comment out jammy lines in sources.list
run("sed -i 's/^deb.*jammy/#&/' /etc/apt/sources.list", sudo=True)
# Remove any jammy-specific list files
run('rm -f /etc/apt/sources.list.d/*jammy* /etc/apt/sources.list.d/*zabbix* 2>/dev/null; ls /etc/apt/sources.list.d/', sudo=True)

# Step 3: Update and check PHP 7.4 availability
print('\n=== [3/6] apt update + 检查 PHP 7.4 ===')
run('apt update -y 2>&1 | tail -5', sudo=True, timeout=120)
out, _, _ = run('apt-cache policy php7.4-cli 2>&1')
print(f'PHP 7.4 available: {out[:300]}')

# Step 4: Remove PHP 8.1 and install PHP 7.4
print('\n=== [4/6] 安装 PHP 7.4 ===')
run('DEBIAN_FRONTEND=noninteractive apt remove --purge -y php8.1* libapache2-mod-php8.1 2>&1 | tail -5', sudo=True, timeout=120)
run('DEBIAN_FRONTEND=noninteractive apt install -y php7.4 php7.4-cli php7.4-common php7.4-mysql php7.4-pgsql php7.4-mbstring php7.4-xml php7.4-curl php7.4-gd php7.4-ldap php7.4-bcmath php7.4-snmp libapache2-mod-php7.4 2>&1 | tail -10', sudo=True, timeout=180)

# Step 5: Verify PHP
print('\n=== [5/6] 验证 PHP 7.4 ===')
run('php -v 2>&1 | head -2')

# Write a test file
php_test = "<?php\n\$r = preg_replace('/foo/', 'BAR', 'foo test');\nvar_dump(\$r);\n"
sftp.putfo(io.StringIO(php_test), '/tmp/pcre_test.php')
run('php /tmp/pcre_test.php 2>&1')

# Step 6: Reconfigure Apache for PHP 7.4
print('\n=== [6/6] 配置 Apache ===')
run('a2dismod php8.1 2>&1 || true', sudo=True)
run('a2enmod php7.4 2>&1', sudo=True)
run('systemctl restart apache2', sudo=True)
run('systemctl status apache2 2>&1 | grep -E "Active|PID"', sudo=True)

# Final test - check Cacti
print('\n=== 最终测试 ===')
run('curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost/cacti/')
run('tail -3 /var/log/apache2/error.log', sudo=True)

sftp.close()
ssh.close()
print('\n=== 完成 ===')
