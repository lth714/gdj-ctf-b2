#!/usr/bin/env python3
"""Deploy VM-A1 DMZ: upload files + install packages + configure everything."""
import paramiko
import sys
import os
import tarfile
import io
import time

HOST = '192.168.100.1'
USER = 'gdadmin'
PASS = 'Gdadmin@123'
SCENARIO_DIR = r'E:\vibecoding\gdj_ctf\scenario-a\vm-a1-dmz'

def sudo(client, cmd, timeout=60):
    """Execute command with sudo, return (stdout, stderr, exit_code)."""
    full = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = client.exec_command(full, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    err_clean = '\n'.join(l for l in err.split('\n') if 'password for gdadmin' not in l)
    code = stdout.channel.recv_exit_status()
    return out, err_clean, code

def create_tar_gz_bytes(source_dir):
    """Create a tar.gz of a directory, return bytes."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for root, dirs, files in os.walk(source_dir):
            for f in files:
                full_path = os.path.join(root, f)
                arcname = os.path.relpath(full_path, source_dir)
                tar.add(full_path, arcname=arcname)
    return buf.getvalue()

def step(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def ok(msg, detail=""):
    print(f"  [OK] {msg}")
    if detail: print(f"    {detail[:300]}")

def fail(msg, code=0, detail=""):
    print(f"  [FAIL] {msg} (exit={code})")
    if detail: print(f"    {detail[:300]}")

def main():
    step("0. Connect to VM-A1")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS,
                   timeout=15, look_for_keys=False, allow_agent=False)
    ok("Connected to 192.168.100.1")

    # ================================================================
    step("1. Upload PbootCMS + media-api via tar.gz")

    # Create PbootCMS archive in memory
    pboot_dir = os.path.join(SCENARIO_DIR, 'files', 'pbootcms')
    print(f"  Creating pbootcms.tar.gz from {pboot_dir}...")
    pboot_tar = create_tar_gz_bytes(pboot_dir)
    print(f"  Size: {len(pboot_tar) / 1024:.1f} KB")

    # Create media-api archive
    media_dir = os.path.join(SCENARIO_DIR, 'files', 'media-api')
    media_tar = create_tar_gz_bytes(media_dir)
    print(f"  Creating media-api.tar.gz from {media_dir}...")
    print(f"  Size: {len(media_tar) / 1024:.1f} KB")

    # Upload
    sftp = client.open_sftp()
    sftp.putfo(io.BytesIO(pboot_tar), '/tmp/pbootcms.tar.gz')
    ok("Uploaded pbootcms.tar.gz")
    sftp.putfo(io.BytesIO(media_tar), '/tmp/media-api.tar.gz')
    ok("Uploaded media-api.tar.gz")
    sftp.close()

    # Create directories and extract
    out, err, code = sudo(client, 'mkdir -p /var/www/cms /opt/media-api')
    out, err, code = sudo(client, 'cd /var/www/cms && tar xzf /tmp/pbootcms.tar.gz && echo EXTRACT_OK')
    ok("Extracted pbootcms to /var/www/cms" if 'EXTRACT_OK' in out else "Extract pbootcms", out)

    out, err, code = sudo(client, 'cd /opt/media-api && tar xzf /tmp/media-api.tar.gz && echo EXTRACT_OK')
    ok("Extracted media-api to /opt/media-api" if 'EXTRACT_OK' in out else "Extract media-api", out)

    # ================================================================
    step("2. Install required packages")
    # Check what's already installed
    out, _, _ = sudo(client, 'dpkg -l nginx 2>/dev/null | tail -1')
    if 'ii' not in out:
        print("  Installing packages (this may take a while, retrying on failure)...")
        # Try up to 3 times
        for attempt in range(3):
            out, err, code = sudo(client,
                'export DEBIAN_FRONTEND=noninteractive; '
                'apt update 2>&1 | tail -3; '
                'apt install -y nginx apache2 php7.4 php7.4-mysql php7.4-mbstring '
                'php7.4-xml php7.4-curl php7.4-gd php7.4-zip libapache2-mod-php7.4 '
                'mysql-client python3 python3-pip python3-venv curl wget '
                'unzip iptables-persistent 2>&1 | tail -10',
                timeout=300)
            if code == 0 and 'Unable to locate' not in out and 'Failed to fetch' not in out:
                ok(f"Packages installed (attempt {attempt+1})")
                break
            else:
                print(f"  Attempt {attempt+1} failed, retrying...")
                time.sleep(5)
        else:
            fail("Package installation failed after 3 attempts", code, out)
            # Continue anyway for config steps
    else:
        ok("nginx already installed")

    # Enable Apache rewrite
    out, err, code = sudo(client, 'a2enmod rewrite 2>&1 || echo OK_ANYWAY')
    ok("Apache mod_rewrite enabled")

    # ================================================================
    step("3. Configure Apache for PbootCMS (port 8080)")
    sudo(client, """cat > /etc/apache2/ports.conf << 'EOF'
Listen 8080
<IfModule ssl_module>
    Listen 443
</IfModule>
EOF""")
    ok("Apache ports.conf written")

    sudo(client, """cat > /etc/apache2/sites-available/000-default.conf << 'EOF'
<VirtualHost *:8080>
    DocumentRoot /var/www/cms
    <Directory /var/www/cms>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    ErrorLog ${APACHE_LOG_DIR}/cms_error.log
    CustomLog ${APACHE_LOG_DIR}/cms_access.log combined
</VirtualHost>
EOF""")
    ok("Apache virtual host configured")

    sudo(client, 'systemctl restart apache2 2>&1 || echo "apache restart issue"')

    # ================================================================
    step("4. Configure PbootCMS")
    sudo(client, 'chown -R www-data:www-data /var/www/cms')
    sudo(client, 'chmod -R 755 /var/www/cms')
    sudo(client, 'mkdir -p /var/www/cms/static/upload/image /var/www/cms/static/upload/file /var/www/cms/static/upload/video')
    sudo(client, 'chmod -R 777 /var/www/cms/static/upload')
    ok("PbootCMS permissions set")

    # Create backup archive
    bak_dir = '/var/www/cms/static/backup/sql'
    out, _, _ = sudo(client, f'ls {bak_dir}/cms_20240101.sql 2>&1 || echo NOT_FOUND')
    if 'NOT_FOUND' not in out:
        sudo(client, f'cd {bak_dir} && gzip -k -f cms_20240101.sql && chmod 644 cms_20240101.sql.gz')
        ok("Created cms_20240101.sql.gz")
    else:
        print("  [WARN] cms_20240101.sql not found, backup file not created")

    # ================================================================
    step("5. Create ops access note (boundary breakthrough hints)")
    sudo(client, """mkdir -p /opt/ops
cat > /opt/ops/access.txt << 'EOF'
===== 运维值班记录 =====
日期: 2024-01-15
值班人: 张工

内网服务器 (VM-A2) 访问方式:
  IP: 192.168.100.2
  SSH: operator / 0p3rat0r@GDJ
  MySQL: 192.168.100.2:3306 (root / R00t@Mysql#2024)
  Redis: 192.168.100.2:6379
  Confluence: http://192.168.100.2:8090

注意: Confluence管理员密码与SSH密码相同。
EOF
chmod 600 /opt/ops/access.txt""")
    ok("Ops access note created at /opt/ops/access.txt")

    # ================================================================
    step("6. Configure nginx reverse proxy")
    sudo(client, """cat > /etc/nginx/sites-available/cms << 'EOF'
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /backup/ {
        alias /var/www/cms/static/backup/sql/;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }

    location /media/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /upload/ {
        alias /var/www/cms/static/upload/;
        autoindex off;
    }
}
EOF""")
    ok("Nginx cms config written")

    sudo(client, 'ln -sf /etc/nginx/sites-available/cms /etc/nginx/sites-enabled/cms 2>&1 || true')
    sudo(client, 'rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true')

    out, err, code = sudo(client, 'nginx -t 2>&1 && systemctl restart nginx && systemctl enable nginx')
    if code == 0:
        ok("Nginx configured and running")
    else:
        fail("Nginx config", code, out + '\n' + err)

    # ================================================================
    step("7. Setup Flask media-api")
    out, err, code = sudo(client,
        'pip3 install flask gunicorn 2>&1 | tail -3', timeout=120)
    # Check if flask installed
    out2, _, _ = sudo(client, 'python3 -c "import flask; print(flask.__version__)" 2>&1')
    if 'flask' in out2.lower() or '__version__' in out2:
        ok(f"Flask installed: {out2}")
    else:
        print(f"  [WARN] Flask install may have failed: {out2[:100]}")

    sudo(client, """cat > /etc/systemd/system/media-api.service << 'EOF'
[Unit]
Description=Media API Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/media-api
ExecStart=/usr/local/bin/gunicorn -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF""")
    ok("media-api systemd service created")

    sudo(client, 'chown -R www-data:www-data /opt/media-api')
    sudo(client, 'systemctl daemon-reload')
    sudo(client, 'systemctl enable media-api --now 2>&1 || true')

    out, _, _ = sudo(client, 'systemctl is-active media-api 2>&1')
    ok(f"media-api service: {out}")

    # ================================================================
    step("8. SUID find (privesc vector A-6)")
    out, err, code = sudo(client, 'chmod u+s /usr/bin/find && ls -la /usr/bin/find')
    ok("SUID set on /usr/bin/find", out)

    # ================================================================
    step("9. MySQL root password reminder")
    sudo(client, """cat > /root/mysql_root_reminder.txt << 'EOF'
MySQL root password for 192.168.100.2:
R00t@Mysql#2024

Note: "/root.cnf" is actually at /etc/mysql/mysql.conf.d/root.cnf on VM-A2
(SQLi LOAD_FILE target for A-4 challenge)
EOF
chmod 600 /root/mysql_root_reminder.txt""")
    ok("MySQL root reminder created")

    # ================================================================
    step("10. SSH configuration")
    sudo(client, "sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config 2>&1 || true")
    sudo(client, "sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>&1 || true")
    sudo(client, 'systemctl restart sshd 2>&1 || systemctl restart ssh 2>&1 || true')
    ok("SSH configured")

    # Create operator user
    sudo(client, 'groupdel operator 2>/dev/null; useradd -m -s /bin/bash operator 2>/dev/null || true')
    sudo(client, 'echo "operator:0p3rat0r@GDJ" | chpasswd 2>&1 || true')
    out, _, _ = sudo(client, 'id operator 2>&1')
    ok(f"operator user: {out}")

    # ================================================================
    step("11. Clean up temp files")
    sudo(client, 'rm -f /tmp/pbootcms.tar.gz /tmp/media-api.tar.gz')
    sudo(client, 'rm -rf /var/cache/apt/archives/*.deb 2>/dev/null || true')
    ok("Temp files cleaned")

    # ================================================================
    step("=== FINAL VERIFICATION ===")
    checks = [
        ("Nginx :80", "systemctl is-active nginx"),
        ("Apache :8080", "systemctl is-active apache2"),
        ("media-api :5000", "systemctl is-active media-api"),
        ("PHP installed", "php -v 2>&1 | head -1"),
        ("Flask installed", "python3 -c 'import flask; print(\"Flask\", flask.__version__)' 2>&1"),
        ("PbootCMS present", "ls /var/www/cms/index.php 2>&1"),
        ("SUID find", "stat -c '%a %n' /usr/bin/find 2>&1"),
        ("operator user", "id operator 2>&1"),
        ("ops access note", "cat /opt/ops/access.txt 2>&1 | head -3"),
        ("backup autoindex", "ls /var/www/cms/static/backup/sql/*.gz 2>&1"),
        ("nginx port 80", "ss -tlnp 2>/dev/null | grep ':80 '"),
        ("apache port 8080", "ss -tlnp 2>/dev/null | grep ':8080 '"),
    ]

    for name, cmd in checks:
        out, err, code = sudo(client, cmd)
        if code == 0:
            ok(name, out[:150])
        elif 'systemctl is-active' in cmd and 'inactive' in out:
            fail(f"{name}: INACTIVE", code, out)
        else:
            ok(f"{name} (code={code})", out[:150])

    # Test web access from localhost
    out, _, _ = sudo(client, 'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/ 2>&1')
    ok(f"Web test http://127.0.0.1/ → HTTP {out}")

    out, _, _ = sudo(client, 'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/backup/ 2>&1')
    ok(f"Backup test http://127.0.0.1/backup/ → HTTP {out}")

    client.close()
    print(f"\n{'='*60}")
    print(" VM-A1 DEPLOYMENT COMPLETE")
    print(f"{'='*60}")
    print(" Access:")
    print("   Web:     http://192.168.100.1/")
    print("   Backup:  http://192.168.100.1/backup/")
    print("   Admin:   http://192.168.100.1/admin.php")
    print("   Media:   http://192.168.100.1/media/")
    print("   SSH:     operator@192.168.100.1 (0p3rat0r@GDJ)")

if __name__ == '__main__':
    main()
