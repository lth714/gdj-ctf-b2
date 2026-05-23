#!/bin/bash
# VM-A1 (DMZ) Setup Script — 区域IPTV内容编排平台 (前端服务层)
# Run as root on Ubuntu 20.04

set -e

echo "[+] Updating system..."
apt update && apt upgrade -y

echo "[+] Installing packages..."
DEBIAN_FRONTEND=noninteractive apt install -y \
    nginx apache2 php7.4 php7.4-mysql php7.4-mbstring \
    php7.4-xml php7.4-curl php7.4-gd php7.4-zip \
    libapache2-mod-php7.4 mysql-client \
    python3 python3-pip python3-venv \
    curl wget netcat-openbsd nmap vim openssh-server unzip \
    iptables-persistent

echo "[+] Enabling Apache mod_rewrite..."
a2enmod rewrite

echo "[+] Configuring Apache for CMS application (port 8080)..."
cat > /etc/apache2/ports.conf << 'APACHEEOF'
Listen 8080
<IfModule ssl_module>
    Listen 443
</IfModule>
APACHEEOF

cat > /etc/apache2/sites-available/000-default.conf << 'APACHEEOF'
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
APACHEEOF

systemctl restart apache2
systemctl enable apache2

echo "[+] Deploying IPTV content management system..."
cp -r ../files/pbootcms /var/www/cms
chown -R www-data:www-data /var/www/cms
chmod -R 755 /var/www/cms

# Make writable directories
mkdir -p /var/www/cms/static/upload/image /var/www/cms/static/upload/file /var/www/cms/static/upload/video
chmod -R 777 /var/www/cms/static/upload

# Backup directory is already at static/backup/sql/
chmod -R 755 /var/www/cms/static/backup

echo "[+] Creating compressed backup for archive..."
cd /var/www/cms/static/backup/sql
gzip -k -f cms_20240101.sql
chmod 644 cms_20240101.sql.gz

echo "[+] Creating business hint files for discovery..."
# Publish sync configuration memo
cat > /var/www/cms/static/backup/sql/publish_notes_202405.txt << 'PUBEOF'
===== 播控发布同步配置备忘 =====
日期: 2024-05-20

内网服务依赖:
  - 数据库: 192.168.100.2:3306 (cms库)
  - 缓存: 192.168.100.2:6379
  - 知识库: http://192.168.100.2:8090

运营人员账号:
  operator / Operator@Media2024 (内容运营)
  此账号用于日常节目单编辑和频道封面上传等操作。

同步流程:
  1. EPG数据通过内部接口导入
  2. 频道列表定时从内网数据服务同步
  3. 发布审核流程通过知识库系统记录
PUBEOF

# Partial media API config example
cat > /var/www/cms/static/backup/sql/media_api_config.example.bak << 'CFGEOF'
# Media API 配置示例 (部分配置)
# 实际配置已部署于 /opt/media-api/

[MEDIA_API]
host = 127.0.0.1
port = 5000
debug = false

[ENDPOINTS]
status = /media/status
sync_status = /media/sync/status
cover_resize = /media/cover/resize
epg_import = /media/epg/import

[INTERNAL]
db_host = 192.168.100.2
db_user = cmsuser
db_pass = ********
CFGEOF

chmod 644 /var/www/cms/static/backup/sql/publish_notes_202405.txt
chmod 644 /var/www/cms/static/backup/sql/media_api_config.example.bak

echo "[+] Creating ops access note (internal infrastructure reference)..."
mkdir -p /opt/ops
cat > /opt/ops/access.txt << 'OPSEOF'
===== 播控运维交接记录 =====
日期: 2024-01-15
值班人: 值班工程师

内网支撑服务 (VM-A2) 访问方式:
  IP: 192.168.100.2
  SSH运维: operator / 0p3rat0r@GDJ
  数据库: 192.168.100.2:3306 (root / R00t@Mysql#2024)
  缓存: 192.168.100.2:6379
  知识库: http://192.168.100.2:8090

提示: 知识库管理员账户与SSH运维密码一致，用于查阅播控发布技术文档。
OPSEOF
chmod 600 /opt/ops/access.txt

echo "[+] Creating publish sync runtime log..."
cat > /opt/ops/publish_sync_202405.log << 'LOGEOF'
[2024-05-20 02:00:01] [INFO] 开始播控同步任务
[2024-05-20 02:00:03] [INFO] 连接内网数据库 192.168.100.2:3306
[2024-05-20 02:00:04] [INFO] 同步频道列表: 120个频道
[2024-05-20 02:00:10] [INFO] 同步EPG节目单: 2850条记录
[2024-05-20 02:00:15] [INFO] 连接内网缓存 192.168.100.2:6379 刷新缓存
[2024-05-20 02:00:16] [INFO] 检测内部知识库 http://192.168.100.2:8090
[2024-05-20 02:00:17] [INFO] 知识库连接正常，读取播控发布手册
[2024-05-20 02:00:18] [INFO] 同步任务完成，下次执行: 02:10:00
[2024-05-20 02:00:19] [INFO] 运维账号 operator 具备sudo服务管理权限
LOGEOF
chmod 644 /opt/ops/publish_sync_202405.log

echo "[+] Configuring nginx reverse proxy..."
cat > /etc/nginx/sites-available/cms.conf << 'NGXEOF'
server {
    listen 80 default_server;
    server_name _;

    # IPTV Content Management System
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Backup directory — autoindex for file archive
    location /backup/ {
        alias /var/www/cms/static/backup/sql/;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }

    # Media API — IPTV content orchestration
    location /media/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Uploads — channel cover and logo storage
    location /upload/ {
        alias /var/www/cms/static/upload/;
        autoindex off;
    }
}
NGXEOF

ln -sf /etc/nginx/sites-available/cms.conf /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
nginx -t && systemctl restart nginx
systemctl enable nginx --now

echo "[+] Setting up media-api (Flask)..."
python3 -m pip install flask gunicorn
cat > /etc/systemd/system/media-api.service << 'SVCEEOF'
[Unit]
Description=Media Process API Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/media-api
ExecStart=/usr/local/bin/gunicorn -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
SVCEEOF

cp -r ../files/media-api /opt/
chown -R www-data:www-data /opt/media-api
systemctl daemon-reload
systemctl enable media-api --now

echo "[+] Setting SUID on find (maintenance tool)..."
chmod u+s /usr/bin/find

echo "[+] MySQL database reference note..."
cat > /root/mysql_root_reminder.txt << 'ROOTEOF'
MySQL root password for 192.168.100.2 (内网播控数据库):
R00t@Mysql#2024

Note: 数据库配置文件位于 /etc/mysql/mysql.conf.d/root.cnf on VM-A2
(内网数据管理MySQL连接配置文件)
ROOTEOF
chmod 600 /root/mysql_root_reminder.txt

echo "[+] Configuring SSH..."
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart sshd

# Create operator user for internal access
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd

echo "[+] Setting up internal network..."
cat >> /etc/netplan/00-installer-config.yaml << 'NETEOF'
    eth1:
      dhcp4: no
      addresses: [192.168.100.1/24]
NETEOF

echo "[+] Cleaning up..."
rm -rf /tmp/* /var/cache/apt/archives/*.deb
history -c

echo "[✓] VM-A1 setup complete."
echo "    External:  DHCP on eth0"
echo "    Internal:  192.168.100.1 on eth1"
echo "    CMS:       http://<IP>/"
echo "    Admin:     http://<IP>/admin.php"
echo "    Backup:    http://<IP>/backup/"
echo "    Media API: http://<IP>/media/"
echo ""
echo "    运营账号: operator / Operator@Media2024"
echo "    数据库备份: http://<IP>/backup/cms_20240101.sql.gz"
