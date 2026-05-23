#!/usr/bin/env python3
"""Configure Nginx + PHP-FPM + Sudo Tee on A1."""
import paramiko
import base64

HOST = '192.168.100.10'
USER = 'gdadmin'
PASS = 'Gdadmin@123'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS,
          timeout=10, look_for_keys=False, allow_agent=False)

def write_remote_file(path, content):
    b64 = base64.b64encode(content.encode()).decode()
    cmd = f'{{ echo "{PASS}"; echo {b64} | base64 -d; }} | sudo -S tee "{path}" > /dev/null 2>&1'
    stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
    stdout.channel.recv_exit_status()

def sudorun(cmd, timeout=30):
    full = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = c.exec_command(full, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

# ========== 1. Start PHP-FPM ==========
print("=== 1. Start PHP 8.1-FPM ===")
out, err, code = sudorun('systemctl enable php8.1-fpm && systemctl start php8.1-fpm && echo FPM_OK')
print(f"FPM: {out}")

# Check socket path
out, err, code = sudorun('ls /run/php/php8.1-fpm.sock 2>&1 || ls /run/php/php-fpm.sock 2>&1 || echo "checking alt"')
print(f"Socket: {out}")

# ========== 2. Configure Nginx ==========
print("\n=== 2. Configure Nginx ===")
nginx_conf = """server {
    listen 80 default_server;
    server_name _;

    root /var/www/html/baixiu;
    index index.php index.html;

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
}"""

write_remote_file('/etc/nginx/sites-available/default', nginx_conf)
print("Nginx config written")

# Test nginx config
out, err, code = sudorun('nginx -t 2>&1')
print(f"Nginx test: {out}")

# Start nginx
out, err, code = sudorun('systemctl enable nginx && systemctl restart nginx && echo NGINX_OK')
print(f"Nginx restart: {out}")

# ========== 3. Verify PHP info via web ==========
print("\n=== 3. Test PHP ===")
write_remote_file('/var/www/html/baixiu/info.php', '<?php phpinfo(); ?>')
out, err, code = sudorun('curl -s http://127.0.0.1/info.php 2>&1 | head -5')
print(f"Web PHP test: {out[:150]}")
sudorun('rm -f /var/www/html/baixiu/info.php')

# ========== 4. Test CMS Homepage ==========
print("\n=== 4. Test CMS homepage ===")
out, err, code = sudorun('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/index.php 2>&1')
print(f"HTTP status: {out}")

# ========== 5. Test CMS Login Page ==========
print("\n=== 5. Test admin login page ===")
out, err, code = sudorun('curl -s http://127.0.0.1/admin/login.php 2>&1 | grep -o "<title>[^<]*</title>"')
print(f"Login page title: {out}")

# ========== 6. Setup sudo tee for www-data ==========
print("\n=== 6. Setup sudo tee ===")
sudoers_content = "www-data ALL=(root) NOPASSWD: /usr/bin/tee\n"
write_remote_file('/etc/sudoers.d/www-data', sudoers_content)
out, err, code = sudorun('chmod 440 /etc/sudoers.d/www-data && echo SUDO_OK')
print(f"Sudoers: {out}")

# Verify sudo
out, err, code = sudorun('sudo -u www-data sudo -ln 2>&1')
print(f"www-data sudo: {out[:200]}")

# ========== 7. Final verification ==========
print("\n=== 7. Final verification ===")
checks = [
    ("Nginx running", "systemctl is-active nginx 2>&1"),
    ("PHP-FPM running", "systemctl is-active php8.1-fpm 2>&1"),
    ("MySQL running", "systemctl is-active mysql 2>&1"),
    ("Port 80 listening", "ss -tlnp 2>/dev/null | grep ':80 ' | head -1"),
    ("CMS files present", "ls /var/www/html/baixiu/index.php 2>&1"),
    ("Config has A2 clue", "grep -c '192.168.100.20' /var/www/html/baixiu/config.php 2>&1"),
]

for label, cmd in checks:
    out, err, code = sudorun(cmd)
    print(f"  {label}: {out[:80]}")

c.close()
print("\n=== DONE ===")
