#!/usr/bin/env python3
"""Fix OA app: copy yml files, update JAR, restart service"""
import paramiko, io, time

host = '192.168.101.140'
user = 'gdadmin'
pwd = 'Gdadmin@123'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)

# Copy application.yml to all needed locations
paths = [
    '/opt/oa-app/ruoyi/ruoyi-admin/src/main/resources/application.yml',
    '/opt/oa-app/ruoyi/ruoyi-admin/target/classes/application.yml',
    '/opt/oa-app/application.yml'
]
for path in paths:
    stdin, stdout, stderr = c.exec_command(
        "echo 'Gdadmin@123' | sudo -S cp /tmp/application.yml " + path
    )
    out = stdout.read().decode()
    err = stderr.read().decode()
    print(f"Copy to {path}: out={out.strip()} err={err.strip()}")

# Also copy application-druid.yml to /opt/oa-app/
stdin, stdout, stderr = c.exec_command(
    "echo 'Gdadmin@123' | sudo -S cp /tmp/application-druid.yml /opt/oa-app/application-druid.yml"
)
print("Copied application-druid.yml to /opt/oa-app/")

# Update JAR
stdin, stdout, stderr = c.exec_command(
    'cd /opt/oa-app/ruoyi/ruoyi-admin/target && '
    'mkdir -p BOOT-INF/classes && '
    'cp /tmp/application.yml BOOT-INF/classes/ && '
    'cp /tmp/application-druid.yml BOOT-INF/classes/ && '
    'jar uf ruoyi-admin.jar BOOT-INF/classes/application.yml BOOT-INF/classes/application-druid.yml 2>&1 && '
    'echo JAR_UPDATED'
)
print("JAR update:", stdout.read().decode().strip())

# Stop, reset, start
for cmd in [
    "echo 'Gdadmin@123' | sudo -S systemctl stop oa-app 2>/dev/null; true",
    "echo 'Gdadmin@123' | sudo -S systemctl reset-failed oa-app 2>/dev/null; true",
    "echo 'Gdadmin@123' | sudo -S systemctl start oa-app",
]:
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip() or err.strip():
        print(f"CMD: {out.strip()} {err.strip()}")

print("Waiting 30s for startup...")
time.sleep(30)

# Check status
stdin, stdout, stderr = c.exec_command(
    "echo 'Gdadmin@123' | sudo -S systemctl is-active oa-app"
)
print("Active:", stdout.read().decode().strip())

# Check port
stdin, stdout, stderr = c.exec_command('ss -tlnp | grep 8080')
print("Port 8080:", stdout.read().decode().strip())

# Check log
stdin, stdout, stderr = c.exec_command(
    "echo 'Gdadmin@123' | sudo -S journalctl -u oa-app --no-pager -n 10 2>/dev/null"
)
log = stdout.read().decode()
if 'Tomcat started' in log or 'Started RuoYiApplication' in log:
    print("SUCCESS! App started!")
elif 'FAILED' in log or 'Error' in log:
    print("FAILED. Log:")
    print(log[-2000:])
else:
    print("Still starting. Latest log:")
    print(log[-1000:])

c.close()
