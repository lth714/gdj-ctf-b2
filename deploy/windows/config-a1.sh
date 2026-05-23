#!/bin/bash
# VM-A1 complete configuration script
set -e

echo "=== Apache + PbootCMS ==="
a2enmod rewrite 2>/dev/null || true

cat > /etc/apache2/ports.conf << 'EOF'
Listen 8080
<IfModule ssl_module>
    Listen 443
</IfModule>
EOF

cat > /etc/apache2/sites-available/000-default.conf << 'EOF'
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
EOF

chown -R www-data:www-data /var/www/cms
chmod -R 755 /var/www/cms
mkdir -p /var/www/cms/static/upload/image /var/www/cms/static/upload/file /var/www/cms/static/upload/video
chmod -R 777 /var/www/cms/static/upload

# Create backup archive if exists
if [ -f /var/www/cms/static/backup/sql/cms_20240101.sql ]; then
    cd /var/www/cms/static/backup/sql
    gzip -k -f cms_20240101.sql
    chmod 644 cms_20240101.sql.gz
fi

systemctl restart apache2
echo "Apache: $(systemctl is-active apache2)"

echo "=== Nginx reverse proxy ==="
cat > /etc/nginx/sites-available/cms << 'EOF'
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
EOF

ln -sf /etc/nginx/sites-available/cms /etc/nginx/sites-enabled/cms
rm -f /etc/nginx/sites-enabled/default

if nginx -t; then
    systemctl restart nginx
    systemctl enable nginx
fi
echo "Nginx: $(systemctl is-active nginx)"

echo "=== Ops hint file ==="
mkdir -p /opt/ops
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
chmod 600 /opt/ops/access.txt

echo "=== Flask media-api ==="
pip3 install flask gunicorn 2>&1 | tail -3 || true

cat > /etc/systemd/system/media-api.service << 'EOF'
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
EOF

chown -R www-data:www-data /opt/media-api
systemctl daemon-reload
systemctl enable media-api --now || true
echo "media-api: $(systemctl is-active media-api)"

echo "=== SUID find ==="
chmod u+s /usr/bin/find
stat -c "%a %n" /usr/bin/find

echo "=== SSH + operator ==="
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config 2>/dev/null || true
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true

groupdel operator 2>/dev/null || true
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
echo "operator: $(id operator 2>&1)"

echo "=== iptables DMZ ==="
mkdir -p /etc/iptables
cat > /etc/iptables/rules.v4 << 'EOF'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p tcp --dport 80 -j ACCEPT
-A INPUT -p icmp -j ACCEPT
COMMIT
EOF

iptables-restore < /etc/iptables/rules.v4

# Persistence
cat > /etc/rc.local << 'EOF'
#!/bin/bash
/sbin/iptables-restore < /etc/iptables/rules.v4
exit 0
EOF
chmod +x /etc/rc.local

echo "iptables: $(iptables -L INPUT -n | head -1)"

echo "=== MySQL root reminder ==="
cat > /root/mysql_root_reminder.txt << 'EOF'
MySQL root password for 192.168.100.2:
R00t@Mysql#2024

Note: "/root.cnf" is actually at /etc/mysql/mysql.conf.d/root.cnf on VM-A2
(SQLi LOAD_FILE target for A-4 challenge)
EOF
chmod 600 /root/mysql_root_reminder.txt

echo "=== Cleanup ==="
rm -f /tmp/pbootcms.tar.gz /tmp/media-api.tar.gz

echo ""
echo "=== VERIFICATION ==="
echo "Nginx: $(systemctl is-active nginx)"
echo "Apache: $(systemctl is-active apache2)"
echo "media-api: $(systemctl is-active media-api)"
echo "SUID find: $(stat -c %a /usr/bin/find)"
echo "Web test: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/)"
echo "Backup test: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/backup/)"
echo "Port 80: $(ss -tlnp | grep ':80 ' | wc -l) listening"
echo "Port 8080: $(ss -tlnp | grep ':8080 ' | wc -l) listening"
echo "Port 5000: $(ss -tlnp | grep ':5000 ' | wc -l) listening"

echo ""
echo "[✓] VM-A1 configuration complete."
echo "    Web:    http://192.168.100.1/"
echo "    Backup: http://192.168.100.1/backup/"
echo "    Admin:  http://192.168.100.1/admin.php"
echo "    Media:  http://192.168.100.1/media/"
echo "    SSH:    operator@192.168.100.1 (0p3rat0r@GDJ)"
