"""Test PHP PCRE regex on B2"""
import paramiko, tempfile, os

HOST = '192.168.120.20'
USER = 'gdadmin'
PWD = 'Gdadmin@123'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PWD, timeout=30)
sftp = ssh.open_sftp()
print('[+] Connected')

def run(cmd, timeout=30, sudo=False):
    if sudo:
        cmd = f"echo '{PWD}' | sudo -S bash -c '{cmd}'"
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    return out, err, ec

# Test 1: simple regex
php_code = "<?php\n$r = preg_replace('/foo/', 'BAR', 'foo test');\nvar_dump($r);\n"
local = os.path.join(tempfile.gettempdir(), 't1.php')
with open(local, 'w', newline='\n') as f:
    f.write(php_code)
with open(local, 'rb') as f:
    print(f'Test1 local bytes: {f.read()}')
sftp.put(local, '/tmp/t1.php')

out, err, ec = run('cat -A /tmp/t1.php')
print(f'Test1 server file: {out}')

out, err, ec = run('php /tmp/t1.php 2>&1')
print(f'Test1 PHP output: {out.strip()}')

# Test 2: Cacti regex from functions.php:2367
php_code2 = "<?php\n$r = preg_replace('/\s*[\r\n]+\s*/', ' ', \"hello\\nworld\");\nvar_dump($r);\n"
local2 = os.path.join(tempfile.gettempdir(), 't2.php')
with open(local2, 'w', newline='\n') as f:
    f.write(php_code2)
sftp.put(local2, '/tmp/t2.php')

out, err, ec = run('php /tmp/t2.php 2>&1')
print(f'Test2 PHP output: {out.strip()}')

os.remove(local)
os.remove(local2)
sftp.close()
ssh.close()
