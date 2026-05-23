"""Deploy Zabbix 5.4 to B2 (192.168.120.20)"""
import paramiko, time

HOST = '192.168.120.20'
USER = 'gdadmin'
PWD = 'Gdadmin@123'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PWD, timeout=30)
print('[+] Connected')

sftp = ssh.open_sftp()

def run(cmd, timeout=120, sudo=False):
    if sudo:
        cmd = f"echo '{PWD}' | sudo -S bash -c '{cmd}'"
    print(f'>>> {cmd[:200]}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        for line in out.strip().split('\n')[-10:]:
            print(f'    {line}')
    if err.strip() and ec != 0:
        for line in err.strip().split('\n')[-3:]:
            print(f'    [stderr] {line}')
    return out, err, ec

# ============================================================
# Step 1: System update + prerequisites
# ============================================================
print('\n[1/6] 更新系统 + 安装依赖...')
run('export DEBIAN_FRONTEND=noninteractive && apt update -y 2>&1 | tail -3', sudo=True, timeout=120)
run('export DEBIAN_FRONTEND=noninteractive && apt upgrade -y 2>&1 | tail -3', sudo=True, timeout=300)
run('export DEBIAN_FRONTEND=noninteractive && apt install -y postgresql-12 apache2 php7.4 php7.4-pgsql php7.4-mbstring php7.4-xml php7.4-curl php7.4-gd php7.4-ldap php7.4-bcmath curl wget gnupg 2>&1 | tail -5', sudo=True, timeout=300)

# Verify
run('php -v 2>&1 | head -1')
run('psql --version 2>&1', sudo=True)
run('apache2 -v 2>&1 | head -1')

# ============================================================
# Step 2: Install Zabbix 5.4
# ============================================================
print('\n[2/6] 安装 Zabbix 5.4...')
run('wget -q https://repo.zabbix.com/zabbix/5.4/ubuntu/pool/main/z/zabbix-release/zabbix-release_5.4-1+ubuntu20.04_all.deb -O /tmp/zabbix-release.deb && dpkg -i /tmp/zabbix-release.deb 2>&1', sudo=True)
run('apt update -y 2>&1 | tail -3', sudo=True)
run('export DEBIAN_FRONTEND=noninteractive && apt install -y zabbix-server-pgsql zabbix-frontend-php zabbix-apache-conf zabbix-agent zabbix-sql-scripts 2>&1 | tail -5', sudo=True, timeout=300)

# ============================================================
# Step 3: Configure PostgreSQL
# ============================================================
print('\n[3/6] 配置 PostgreSQL...')
run('systemctl enable postgresql --now', sudo=True)
run('systemctl status postgresql 2>&1 | grep -E "Active|PID"', sudo=True)

# Create zabbix user and database
pg_sql = """
CREATE USER zabbix WITH PASSWORD 'Zabbix@DB#2024';
CREATE DATABASE zabbix OWNER zabbix;
GRANT ALL PRIVILEGES ON DATABASE zabbix TO zabbix;
"""
fh = sftp.open('/home/gdadmin/zabbix_pg.sql', 'w')
fh.write(pg_sql)
fh.close()
run('cat /home/gdadmin/zabbix_pg.sql | sudo -u postgres psql 2>&1', sudo=True)

# Import schema
print('导入 Zabbix 数据库表结构...')
# Find the SQL schema file
out, _, _ = run('find /usr/share -name "server.sql.gz" 2>/dev/null')
schema_path = out.strip().split('\n')[0].strip() if out.strip() else ''
print(f'  Schema: {schema_path}')
if schema_path:
    run(f'zcat {schema_path} | sudo -u zabbix psql zabbix 2>&1 | tail -3', sudo=True, timeout=300)

# Verify tables
run('sudo -u zabbix psql zabbix -c "SELECT count(*) FROM information_schema.tables WHERE table_schema=\'public\';" 2>&1', sudo=True)

# ============================================================
# Step 4: Configure Zabbix Server + Frontend
# ============================================================
print('\n[4/6] 配置 Zabbix Server + Frontend...')

zabbix_conf = """ListenPort=10051
LogFile=/var/log/zabbix/zabbix_server.log
LogFileSize=10
PidFile=/run/zabbix/zabbix_server.pid
DBHost=localhost
DBName=zabbix
DBUser=zabbix
DBPassword=Zabbix@DB#2024
StartPollers=5
StartTrappers=5
StartDiscoverers=1
CacheSize=8M
Timeout=10
"""
fh = sftp.open('/home/gdadmin/zabbix_server.conf', 'w')
fh.write(zabbix_conf)
fh.close()
run('cp /home/gdadmin/zabbix_server.conf /etc/zabbix/zabbix_server.conf', sudo=True)

web_conf = """<?php
global $DB;
$DB['TYPE']     = 'POSTGRESQL';
$DB['SERVER']   = 'localhost';
$DB['PORT']     = '5432';
$DB['DATABASE'] = 'zabbix';
$DB['USER']     = 'zabbix';
$DB['PASSWORD'] = 'Zabbix@DB#2024';
$DB['SCHEMA']   = 'public';
$ZBX_SERVER      = 'localhost';
$ZBX_SERVER_PORT = '10051';
$ZBX_SERVER_NAME = '广电播出监控平台';
$IMAGE_FORMAT_DEFAULT = IMAGE_FORMAT_PNG;
"""
fh = sftp.open('/home/gdadmin/zabbix.conf.php', 'w')
fh.write(web_conf)
fh.close()
run('mkdir -p /etc/zabbix/web && cp /home/gdadmin/zabbix.conf.php /etc/zabbix/web/zabbix.conf.php', sudo=True)

# Apache config
run('a2enconf zabbix-frontend-php 2>&1', sudo=True)
run('a2dissite 000-default 2>&1 || true', sudo=True)
run('a2enmod rewrite 2>&1', sudo=True)
run('systemctl restart apache2', sudo=True)

# Zabbix server
run('systemctl enable zabbix-server zabbix-agent --now 2>&1', sudo=True)
run('systemctl status zabbix-server 2>&1 | grep -E "Active|PID"', sudo=True)

# ============================================================
# Step 5: Enable SAML SSO (CVE-2022-23131)
# ============================================================
print('\n[5/6] 启用 SAML SSO (CVE-2022-23131)...')

saml_sql = """
UPDATE config SET
    authentication_type = 1,
    saml_auth_enabled = 1,
    saml_idp_entityid = 'https://idp.gdj-broadcast.local/saml/metadata',
    saml_sso_url = 'https://idp.gdj-broadcast.local/saml/sso',
    saml_slo_url = 'https://idp.gdj-broadcast.local/saml/slo',
    saml_username_attribute = 'username',
    saml_sp_entityid = 'zabbix-gdj-monitor',
    saml_nameid_format = 'urn:oasis:names:tc:SAML:2.0:nameid-format:transient',
    saml_sign_messages = 0,
    saml_sign_assertions = 0,
    saml_sign_authn_requests = 0,
    saml_case_sensitive = 0,
    saml_x509cert = 'MIIC...FAKE...CERT',
    saml_status = 1
WHERE configid = 1;
"""
fh = sftp.open('/home/gdadmin/zabbix_saml.sql', 'w')
fh.write(saml_sql)
fh.close()
run('cat /home/gdadmin/zabbix_saml.sql | sudo -u zabbix psql zabbix 2>&1', sudo=True)

# Verify SAML
run('sudo -u zabbix psql zabbix -c "SELECT authentication_type, saml_auth_enabled FROM config LIMIT 1;" 2>&1', sudo=True)

# ============================================================
# Step 6: Privesc + Operator
# ============================================================
print('\n[6/6] 配置提权 + operator...')

sudo_conf = 'zabbix ALL=(root) NOPASSWD: /usr/bin/find\n'
fh = sftp.open('/home/gdadmin/zabbix-find', 'w')
fh.write(sudo_conf)
fh.close()
run('cp /home/gdadmin/zabbix-find /etc/sudoers.d/zabbix-find && chmod 440 /etc/sudoers.d/zabbix-find', sudo=True)

run('id operator 2>&1 || (useradd -m -s /bin/bash operator && echo \"operator:0p3rat0r@GDJ\" | chpasswd)', sudo=True)
run('usermod -aG sudo operator 2>&1', sudo=True)

# Verify sudo
run('sudo -u zabbix sudo -l 2>&1', sudo=True)
run('id operator 2>&1')

# ============================================================
# Final Verification
# ============================================================
print('\n=== 最终验证 ===')
run('systemctl is-active postgresql apache2 zabbix-server zabbix-agent 2>&1')
run('curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost/ 2>&1')

# DB connection
run('sudo -u zabbix psql zabbix -c "SELECT alias FROM users LIMIT 3;" 2>&1', sudo=True)

sftp.close()
ssh.close()
print('\n=== B2 部署完成 ===')
print('Zabbix: http://192.168.120.20/')
print('Admin: Admin / zabbix')
print('PG: zabbix / Zabbix@DB#2024')
print('Operator: operator / 0p3rat0r@GDJ')
print('Sudo: zabbix ALL=(root) NOPASSWD: /usr/bin/find')
