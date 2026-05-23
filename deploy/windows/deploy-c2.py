#!/usr/bin/env python3
"""Comprehensive C2 deployment: OpenLDAP + Samba + MySQL + Drupal"""
import paramiko, time, sys, os

HOST = '192.168.101.141'
USER = 'gdadmin'
PWD = 'Gdadmin@123'

def run_ssh(client, cmd, timeout=300, show_out=True):
    """Run command via SSH and return stdout, stderr, exit_code"""
    if show_out:
        print(f"  $ {cmd[:130]}{'...' if len(cmd) > 130 else ''}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if show_out and out.strip():
        tail = out.strip()[-400:]
        if len(out) > 400:
            print(f"    ({len(out)} chars) ...{tail}")
        else:
            print(f"    {out.strip()}")
    if err.strip() and 'password' not in err.lower():
        print(f"    stderr: {err.strip()[-200:]}")
    return out, err, ec

def sudo_pipe(cmd):
    """Run command with sudo password piped"""
    return f"echo '{PWD}' | sudo -S bash -c '{cmd}' 2>&1"

print("=" * 60)
print("C2 Internal VM Deployment")
print("=" * 60)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PWD, timeout=10)
print(f"Connected to {HOST}\n")

# =====================================================
# STEP 1: Upload deployment files
# =====================================================
print("STEP 1: Upload deployment files")
print("-" * 40)

# Create /opt/deploy/ directory
run_ssh(c, f"echo '{PWD}' | sudo -S mkdir -p /opt/deploy")

# Upload init_db.sql
local_sql = os.path.join(os.path.dirname(__file__), '..', '..', 'scenario-c', 'vm-c2-internal', 'init_db.sql')
sftp = c.open_sftp()
with open(local_sql, 'r', encoding='utf-8') as f:
    sql_content = f.read()
with sftp.open('/tmp/init_db.sql', 'w') as f:
    f.write(sql_content.encode('utf-8'))
sftp.close()
run_ssh(c, f"echo '{PWD}' | sudo -S cp /tmp/init_db.sql /opt/deploy/init_db.sql")
print(f"  Uploaded init_db.sql ({len(sql_content)} bytes)")

# =====================================================
# STEP 2: Install packages
# =====================================================
print("\nSTEP 2: Install packages (slapd, samba, mysql, apache2, php7.4...)")
print("-" * 40)

# Pre-configure slapd (non-interactive)
debconf_cmds = [
    'echo "slapd slapd/domain string gdj.local" | sudo -S debconf-set-selections',
    'echo "slapd slapd/internal/adminpw password Ldap@Admin#2024" | sudo -S debconf-set-selections',
    'echo "slapd slapd/internal/generated_adminpw password Ldap@Admin#2024" | sudo -S debconf-set-selections',
    'echo "slapd slapd/password1 password Ldap@Admin#2024" | sudo -S debconf-set-selections',
    'echo "slapd slapd/password2 password Ldap@Admin#2024" | sudo -S debconf-set-selections',
    'echo "slapd slapd/backend string MDB" | sudo -S debconf-set-selections',
]
for cmd in debconf_cmds:
    run_ssh(c, f"echo '{PWD}' | sudo -S bash -c \"{cmd}\" 2>/dev/null", show_out=False)

# Add PHP repo and install
install_script = '''
export DEBIAN_FRONTEND=noninteractive
echo '[*] Installing base packages...'
apt install -y software-properties-common 2>&1 | tail -3
add-apt-repository -y ppa:ondrej/php 2>&1 | tail -5
apt update -qq 2>&1 | tail -3

echo '[*] Installing main packages...'
DEBIAN_FRONTEND=noninteractive apt install -y \\
    slapd ldap-utils samba mysql-server-8.0 \\
    apache2 php7.4 php7.4-mysql php7.4-mbstring php7.4-xml php7.4-curl \\
    php7.4-gd libapache2-mod-php7.4 \\
    openssh-server curl wget netcat-openbsd vim \\
    iptables-persistent 2>&1 | tail -10

echo 'INSTALL_DONE'
'''
stdin, stdout, stderr = c.exec_command(
    f"echo '{PWD}' | sudo -S bash -c \"{install_script}\"", timeout=600)
# Read output incrementally
while not stdout.channel.exit_status_ready():
    if stdout.channel.recv_ready():
        data = stdout.channel.recv(4096).decode('utf-8', errors='replace')
        if data.strip():
            print(f"    {data.strip()[-200:]}")
    time.sleep(1)
# Get remaining
rest = stdout.read().decode('utf-8', errors='replace')
if rest.strip():
    print(f"    {rest.strip()[-300:]}")

# =====================================================
# STEP 3: Configure OpenLDAP
# =====================================================
print("\nSTEP 3: Configure OpenLDAP")
print("-" * 40)

# Reconfigure slapd
run_ssh(c, sudo_pipe("dpkg-reconfigure -f noninteractive slapd 2>&1"))

# Import LDIF
ldif = '''dn: ou=users,dc=gdj,dc=local
objectClass: organizationalUnit
ou: users

dn: ou=groups,dc=gdj,dc=local
objectClass: organizationalUnit
ou: groups

dn: cn=admin,ou=users,dc=gdj,dc=local
objectClass: inetOrgPerson
cn: admin
sn: Admin
mail: admin@gdj.local
userPassword: Admin@OA2024

dn: cn=zhangsan,ou=users,dc=gdj,dc=local
objectClass: inetOrgPerson
cn: zhangsan
sn: Zhang
mail: zhangsan@gdj.local
userPassword: Pass@1234

dn: cn=operator,ou=users,dc=gdj,dc=local
objectClass: inetOrgPerson
cn: operator
sn: Operator
mail: operator@gdj.local
userPassword: 0p3rat0r@GDJ'''

sftp = c.open_sftp()
with sftp.open('/tmp/base.ldif', 'w') as f:
    f.write(ldif.encode('utf-8'))
sftp.close()

run_ssh(c, sudo_pipe(
    "ldapadd -x -D 'cn=admin,dc=gdj,dc=local' -w 'Ldap@Admin#2024' -f /tmp/base.ldif 2>&1 || true"))

# Allow remote LDAP access
run_ssh(c, sudo_pipe(
    r"sed -i 's|SLAPD_SERVICES=\"ldap:/// ldapi:///\"|SLAPD_SERVICES=\"ldap://0.0.0.0 ldapi:///\"|' /etc/default/slapd 2>/dev/null || true"))
run_ssh(c, sudo_pipe("systemctl restart slapd"))
print("  OpenLDAP configured")

# =====================================================
# STEP 4: Configure Samba
# =====================================================
print("\nSTEP 4: Configure Samba")
print("-" * 40)

smb_conf = '''[global]
   workgroup = GDJ
   server string = GDJ Internal File Server
   security = user
   map to guest = Bad User
   log file = /var/log/samba/log.%m
   max log size = 1000

[public]
   path = /srv/samba/public
   browseable = yes
   read only = yes
   guest ok = yes
   comment = Public Documents'''

sftp = c.open_sftp()
with sftp.open('/tmp/smb.conf', 'w') as f:
    f.write(smb_conf.encode('utf-8'))
sftp.close()
run_ssh(c, sudo_pipe("cp /tmp/smb.conf /etc/samba/smb.conf"))

ops_manual = '''===========================================
广电局内部OA系统运维手册 v3.0
===========================================

一、服务器列表
  DMZ Web服务器 (OA): 192.168.120.1
  Internal 后端服务器:  192.168.120.2

二、登录信息
  Internal服务器 SSH:
    地址: 192.168.120.2
    用户: operator
    密码: 0p3rat0r@GDJ

  数据库 (MySQL):
    地址: 192.168.120.2:3306
    用户: oauser / Oaus3r@2024!

  LDAP管理:
    地址: 192.168.120.2:389
    Bind DN: cn=admin,dc=gdj,dc=local
    Bind密码: Ldap@Admin#2024

三、内部应用
  内部门户网站: http://192.168.120.2/
  (仅限内网访问，DMZ不可直接访问)

四、故障处理
  如遇到服务异常，SSH登录后执行:
    sudo systemctl restart apache2
    sudo systemctl restart mysql

五、重要提醒
  - 请勿将本手册外传
  - 定期更换密码
  - 运维结束后清理SSH历史

编写日期: 2024-01-15
编写人: 张工
==========================================='''

sftp = c.open_sftp()
with sftp.open('/tmp/ops_manual.txt', 'w') as f:
    f.write(ops_manual.encode('utf-8'))
sftp.close()

run_ssh(c, sudo_pipe("mkdir -p /srv/samba/public"))
run_ssh(c, sudo_pipe("cp /tmp/ops_manual.txt '/srv/samba/public/运维手册.txt'"))
run_ssh(c, sudo_pipe("chmod 644 '/srv/samba/public/运维手册.txt'"))
run_ssh(c, sudo_pipe("systemctl restart smbd"))
print("  Samba configured")

# =====================================================
# STEP 5: Configure MySQL
# =====================================================
print("\nSTEP 5: Configure MySQL")
print("-" * 40)

run_ssh(c, sudo_pipe("systemctl enable mysql --now"))

# Set root password
run_ssh(c, sudo_pipe(
    "mysql -u root -e \"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024'; FLUSH PRIVILEGES;\" 2>&1"))

# Import init_db.sql
run_ssh(c, sudo_pipe("mysql -u root -p'R00t@Mysql#2024' < /opt/deploy/init_db.sql 2>&1"))
print("  init_db.sql imported")

# Allow remote connections
run_ssh(c, sudo_pipe(r"sed -i 's/bind-address.*=.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null || echo 'bind-address = 0.0.0.0' >> /etc/mysql/mysql.conf.d/mysqld.cnf"))
run_ssh(c, sudo_pipe("systemctl restart mysql"))

# Verify DB
out, _, _ = run_ssh(c, sudo_pipe("mysql -u root -p'R00t@Mysql#2024' -e 'SHOW DATABASES; SELECT COUNT(*) as user_count FROM oa.users;' 2>&1"))
print(f"  MySQL verification: {out.strip()[-300:]}")
print("  MySQL configured")

# =====================================================
# STEP 6: Deploy Drupal 7.57
# =====================================================
print("\nSTEP 6: Deploy Drupal 7.57 (CVE-2018-7600 target)")
print("-" * 40)

# Download Drupal 7.57
print("  Downloading Drupal 7.57...")
run_ssh(c, sudo_pipe(
    "cd /tmp && wget -q https://ftp.drupal.org/files/projects/drupal-7.57.tar.gz -O drupal.tar.gz 2>&1 && echo 'DOWNLOAD_OK' || echo 'DOWNLOAD_FAIL'"), timeout=300)

# Extract
run_ssh(c, sudo_pipe("mkdir -p /var/www/drupal"))
run_ssh(c, sudo_pipe(
    "cd /tmp && tar xzf drupal.tar.gz -C /tmp/ && cp -r /tmp/drupal-7.57/* /var/www/drupal/ && cp /tmp/drupal-7.57/.htaccess /var/www/drupal/ 2>/dev/null || true && rm -rf /tmp/drupal-7.57"))

# Create Drupal database
run_ssh(c, sudo_pipe(
    "mysql -u root -p'R00t@Mysql#2024' -e \"CREATE DATABASE IF NOT EXISTS drupal CHARACTER SET utf8mb4; GRANT ALL ON drupal.* TO 'oauser'@'%';\" 2>&1"))

# Set up settings.php
settings_php = '''<?php
$databases = array(
  'default' => array(
    'default' => array(
      'database' => 'drupal',
      'username' => 'oauser',
      'password' => 'Oaus3r@2024!',
      'host' => 'localhost',
      'port' => '',
      'driver' => 'mysql',
      'prefix' => '',
    ),
  ),
);
$update_free_access = FALSE;
$drupal_hash_salt = 'gdjctf_drupal_salt_2024';
ini_set('session.gc_probability', 1);
ini_set('session.gc_divisor', 100);
ini_set('session.gc_maxlifetime', 200000);
ini_set('session.cookie_lifetime', 2000000);
$conf['404_fast_paths_exclude'] = '/\/(?:styles)\//';
$conf['404_fast_paths'] = '/\.(?:txt|png|gif|jpe?g|css|js|ico|swf|flv|cgi|bat|pl|dll|exe|asp)$/i';
$conf['404_fast_html'] = '<html><head><title>404 Not Found</title></head><body><h1>Not Found</h1></body></html>';
'''

sftp = c.open_sftp()
with sftp.open('/tmp/settings.php', 'w') as f:
    f.write(settings_php.encode('utf-8'))
sftp.close()

run_ssh(c, sudo_pipe("cp /tmp/settings.php /var/www/drupal/sites/default/settings.php"))
run_ssh(c, sudo_pipe("chown -R www-data:www-data /var/www/drupal"))
run_ssh(c, sudo_pipe("mkdir -p /var/www/drupal/sites/default/files"))
run_ssh(c, sudo_pipe("chmod 777 /var/www/drupal/sites/default/files"))
run_ssh(c, sudo_pipe("chmod 644 /var/www/drupal/sites/default/settings.php"))

print("  Drupal files deployed")

# =====================================================
# STEP 7: Configure Apache
# =====================================================
print("\nSTEP 7: Configure Apache vhost")
print("-" * 40)

vhost = '''<VirtualHost *:80>
    DocumentRoot /var/www/drupal
    <Directory /var/www/drupal>
        Options FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    ErrorLog ${APACHE_LOG_DIR}/drupal_error.log
    CustomLog ${APACHE_LOG_DIR}/drupal_access.log combined
</VirtualHost>'''

sftp = c.open_sftp()
with sftp.open('/tmp/drupal.conf', 'w') as f:
    f.write(vhost.encode('utf-8'))
sftp.close()

run_ssh(c, sudo_pipe("cp /tmp/drupal.conf /etc/apache2/sites-available/drupal.conf"))
run_ssh(c, sudo_pipe("a2dissite 000-default 2>/dev/null || true"))
run_ssh(c, sudo_pipe("a2ensite drupal 2>&1"))
run_ssh(c, sudo_pipe("a2enmod rewrite 2>&1"))
run_ssh(c, sudo_pipe("systemctl restart apache2"))
print("  Apache configured")

# =====================================================
# STEP 8: Create operator user + privesc
# =====================================================
print("\nSTEP 8: Create operator user + privilege escalation")
print("-" * 40)

run_ssh(c, sudo_pipe("useradd -m -s /bin/bash operator 2>/dev/null || true"))
run_ssh(c, sudo_pipe("echo 'operator:0p3rat0r@GDJ' | chpasswd"))
run_ssh(c, sudo_pipe("usermod -aG sudo operator"))
run_ssh(c, sudo_pipe("echo 'operator ALL=(ALL) NOPASSWD: /usr/bin/find' > /etc/sudoers.d/operator-escalate"))
run_ssh(c, sudo_pipe("chmod 440 /etc/sudoers.d/operator-escalate"))
print("  operator user created (sudo find escalation)")

# =====================================================
# STEP 9: Configure iptables
# =====================================================
print("\nSTEP 9: Configure iptables (network isolation)")
print("-" * 40)

iptables_rules = '''*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]

-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow from VM-C1: LDAP (389)
-A INPUT -s 192.168.120.1/32 -p tcp --dport 389 -j ACCEPT

# Allow from VM-C1: Samba (445, 139)
-A INPUT -s 192.168.120.1/32 -p tcp --dport 445 -j ACCEPT
-A INPUT -s 192.168.120.1/32 -p tcp --dport 139 -j ACCEPT

# Allow from VM-C1: MySQL (3306)
-A INPUT -s 192.168.120.1/32 -p tcp --dport 3306 -j ACCEPT

# Allow from VM-C1: Drupal/HTTP (80)
-A INPUT -s 192.168.120.1/32 -p tcp --dport 80 -j ACCEPT

# Allow internal network + loopback
-A INPUT -s 192.168.120.0/24 -j ACCEPT
-A INPUT -s 127.0.0.0/8 -j ACCEPT
-A INPUT -p icmp -j ACCEPT

# SSH from management network
-A INPUT -s 192.168.101.0/24 -p tcp --dport 22 -j ACCEPT

COMMIT'''

sftp = c.open_sftp()
with sftp.open('/tmp/rules.v4', 'w') as f:
    f.write(iptables_rules.encode('utf-8'))
sftp.close()

run_ssh(c, sudo_pipe("mkdir -p /etc/iptables"))
run_ssh(c, sudo_pipe("cp /tmp/rules.v4 /etc/iptables/rules.v4"))
run_ssh(c, sudo_pipe("iptables-restore < /etc/iptables/rules.v4 2>&1 || true"))
run_ssh(c, sudo_pipe("netfilter-persistent save 2>&1 || true"))
print("  iptables configured")

# =====================================================
# STEP 10: Verify all services
# =====================================================
print("\n" + "=" * 60)
print("STEP 10: Service Verification")
print("=" * 60)

checks = [
    ("slapd (LDAP)", "systemctl is-active slapd"),
    ("smbd (Samba)", "systemctl is-active smbd"),
    ("mysql", "systemctl is-active mysql"),
    ("apache2", "systemctl is-active apache2"),
    ("Port 389 (LDAP)", "ss -tlnp | grep ':389 '"),
    ("Port 445 (Samba)", "ss -tlnp | grep ':445 '"),
    ("Port 3306 (MySQL)", "ss -tlnp | grep ':3306 '"),
    ("Port 80 (HTTP)", "ss -tlnp | grep ':80 '"),
    ("Drupal http check", "curl -s -o /dev/null -w '%{http_code}' http://localhost/ 2>/dev/null"),
    ("LDAP query", "ldapsearch -x -H ldap://localhost -b 'dc=gdj,dc=local' -D 'cn=admin,dc=gdj,dc=local' -w 'Ldap@Admin#2024' '(objectClass=*)' 2>/dev/null | grep -c 'dn:'"),
    ("MySQL OA DB", "echo 'R00t@Mysql#2024' | sudo -S mysql -u root -e 'SELECT COUNT(*) FROM oa.users;' 2>/dev/null | tail -1"),
]

for name, cmd in checks:
    out, err, ec = run_ssh(c, f"echo '{PWD}' | sudo -S bash -c \"{cmd}\" 2>/dev/null", timeout=15)
    result = out.strip().split('\n')[-1] if out.strip() else 'N/A'
    status = "✅" if ec == 0 and result and 'inactive' not in result.lower() and result != '000' else "❌"
    print(f"  {status} {name}: {result}")

# Cleanup
run_ssh(c, "rm -f /tmp/init_db.sql /tmp/base.ldif /tmp/smb.conf /tmp/ops_manual.txt /tmp/settings.php /tmp/drupal.conf /tmp/rules.v4", show_out=False)

c.close()
print("\n" + "=" * 60)
print("C2 DEPLOYMENT COMPLETE!")
print("=" * 60)
print(f"VM-C2 Internal: {HOST}")
print("Services: LDAP:389 | Samba:445 | MySQL:3306 | Drupal:80")
print("SSH user: operator / 0p3rat0r@GDJ")
print("Privesc: sudo find (NOPASSWD)")
