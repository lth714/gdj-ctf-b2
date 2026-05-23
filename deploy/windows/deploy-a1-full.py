#!/usr/bin/env python3
"""Full A1 deployment: packages -> files -> MySQL -> Nginx -> sudo tee."""
import paramiko
import base64
import tempfile
import os
import time

HOST = '192.168.100.10'
USER = 'gdadmin'
PASS = 'Gdadmin@123'
MYSQL_PASS = 'R00t@Mysql#2024'
SRC_DIR = r'E:\vibecoding\gdj_ctf\q1\news_dev-master'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS,
          timeout=15, look_for_keys=False, allow_agent=False)

def sudo(cmd, timeout=120):
    """Run command with sudo, return (stdout, stderr, exit_code)."""
    full = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = c.exec_command(full, timeout=timeout)
    # Set channel timeout to match to avoid read() timeout
    stdout.channel.settimeout(timeout)
    stderr.channel.settimeout(timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

def sftp_put(local_path, remote_path):
    """Upload a local file to remote via SFTP."""
    sftp = c.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()

def write_remote(path, content):
    """Write content to remote file via base64 + sudo tee."""
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
# Check
for pkg in ['nginx', 'mysql-server', 'php8.1', 'php8.1-fpm', 'php8.1-mysql']:
    out, _, _ = sudo(f'dpkg -l {pkg} 2>/dev/null | tail -1')
    ok = 'ii' in out[:10] if out else False
    print(f"  {pkg}: {'OK' if ok else 'MISSING'}")

# ==================== Step 2: Upload CMS Files ====================
step(2, "Upload & deploy CMS files")
import io, tarfile
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode='w:gz') as tar:
    for root, dirs, files in os.walk(SRC_DIR):
        for f in files:
            full = os.path.join(root, f)
            tar.add(full, os.path.relpath(full, SRC_DIR))
tar_data = buf.getvalue()
print(f"CMS archive: {len(tar_data)/1024:.1f} KB")

# Upload via SFTP
sftp = c.open_sftp()
sftp.putfo(io.BytesIO(tar_data), '/tmp/cms.tar.gz')
sftp.close()

out, _, code = sudo('mkdir -p /var/www/html && cd /var/www/html && tar xzf /tmp/cms.tar.gz && mv news_dev-master baixiu && echo OK')
print(f"Extract: {out}")

out, _, code = sudo('chown -R www-data:www-data /var/www/html/baixiu && chmod -R 755 /var/www/html/baixiu && mkdir -p /var/www/html/baixiu/static/uploads && chmod -R 777 /var/www/html/baixiu/static/uploads && rm -f /var/www/html/baixiu/init_db.sql && echo OK')
print(f"Permissions: {out}")

# ==================== Step 3: MySQL Setup ====================
step(3, "Configure MySQL")

# Upload init_db.sql
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

# Start MySQL
out, _, code = sudo('systemctl enable mysql && systemctl start mysql && echo OK')
print(f"MySQL start: {out}")

# Set root password
sql1 = "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024';\nFLUSH PRIVILEGES;\n"
write_remote('/tmp/setpass.sql', sql1)
out, err, code = sudo('mysql -u root < /tmp/setpass.sql 2>&1')
print(f"Set password: out=[{out}], code={code}")

# Import database (with password now)
out, err, code = sudo(f'mysql -u root -p"{MYSQL_PASS}" < /tmp/init_db.sql 2>&1')
# Ignore the warning about password on command line
if 'IMPORT_OK' in out:
    print("Import: OK")
else:
    print(f"Import: code={code}, out={out[:100]}")

# Verify
out, err, code = sudo(f'mysql -u root -p"{MYSQL_PASS}" -e "SELECT COUNT(*) FROM baixiu.users;" 2>&1')
print(f"Users: {out.split()[-1] if out else 'FAIL'}")

# ==================== Step 4: Nginx + PHP-FPM ====================
step(4, "Configure Nginx + PHP-FPM")

# Start PHP-FPM
out, _, code = sudo('systemctl enable php8.1-fpm && systemctl start php8.1-fpm && echo OK')
print(f"PHP-FPM: {out}")

# Write nginx config locally then SFTP put
nginx_conf = """server {
    listen 80 default_server;
    server_name _;

    root /var/www/html;
    index index.php index.html;

    location = / {
        return 301 /baixiu/;
    }

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }
}
"""
tmpfile = os.path.join(tempfile.gettempdir(), 'nginx-a1.conf')
with open(tmpfile, 'w') as f:
    f.write(nginx_conf)
sftp = c.open_sftp()
sftp.put(tmpfile, '/tmp/nginx-a1.conf')
sftp.close()
os.unlink(tmpfile)

out, _, code = sudo('cp /tmp/nginx-a1.conf /etc/nginx/sites-available/default && nginx -t 2>&1 && systemctl restart nginx && systemctl enable nginx && echo OK')
print(f"Nginx: {out}")

# ==================== Step 5: Sudo Tee ====================
step(5, "Setup sudo tee (www-data -> root)")
write_remote('/etc/sudoers.d/www-data', 'www-data ALL=(root) NOPASSWD: /usr/bin/tee\n')
out, _, code = sudo('chmod 440 /etc/sudoers.d/www-data && echo OK')
print(f"Sudoers: {out}")

# ==================== Step 6: Verification ====================
step(6, "Final Verification")
checks = [
    ("Nginx", "systemctl is-active nginx 2>&1"),
    ("PHP-FPM", "systemctl is-active php8.1-fpm 2>&1"),
    ("MySQL", "systemctl is-active mysql 2>&1"),
    ("Port 80", "ss -tlnp 2>/dev/null | grep ':80 ' | head -1"),
    ("Redirect /", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/"),
    ("baixiu/", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/baixiu/"),
    ("Login page", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/baixiu/admin/login.php"),
    ("CSS", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/baixiu/static/assets/css/style.css"),
    ("Sudo tee", "sudo -u www-data sudo -ln 2>&1 | grep -c tee"),
    ("Config A2 clue", "grep -c '192.168.100.20' /var/www/html/baixiu/config.php"),
    ("SQLi check", "curl -s -X POST http://127.0.0.1/baixiu/admin/login.php --data-urlencode 'email=admin' --data-urlencode 'password=Media@News2024' -o /dev/null -w '%{http_code}'"),
]

for label, cmd in checks:
    out, err, code = sudo(cmd)
    status = "OK" if code == 0 else f"code={code}"
    print(f"  {label}: {out[:60]}")

# Cleanup temp files
sudo('rm -f /tmp/cms.tar.gz /tmp/init_db.sql /tmp/setpass.sql /tmp/nginx-a1.conf')

c.close()
print(f"\n{'='*50}")
print(" A1 DEPLOYMENT COMPLETE")
print(f"{'='*50}")
print("  URL:    http://192.168.100.10/ -> /baixiu/")
print("  Admin:  http://192.168.100.10/baixiu/admin/login.php")
print("  User:   admin / Media@News2024")
print("  Editor: editor / Edit0r@2024")
print("  MySQL:  root / R00t@Mysql#2024")
print("  Privesc: www-data -> sudo tee -> root")
