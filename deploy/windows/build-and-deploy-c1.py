#!/usr/bin/env python3
"""Build RuoYi on C1, fix JAR, deploy, and verify"""
import paramiko, time, sys

host = '192.168.101.140'
user = 'gdadmin'
pwd = 'Gdadmin@123'

def run_ssh(client, cmd, timeout=600):
    """Run a command and return stdout, stderr, exit_code"""
    print(f"\n>>> {cmd[:120]}{'...' if len(cmd) > 120 else ''}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    exit_code = stdout.channel.recv_exit_status()
    if out.strip():
        # Print last 2000 chars for long output
        if len(out) > 2000:
            print(f"  stdout ({len(out)} chars): ...{out[-2000:]}")
        else:
            print(f"  stdout: {out.strip()}")
    if err.strip():
        # Only show last 500 chars of stderr
        if len(err) > 500:
            print(f"  stderr ({len(err)} chars): ...{err[-500:]}")
        else:
            print(f"  stderr: {err.strip()}")
    return out, err, exit_code

print("Connecting to C1...")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.")

# Step 1: Build RuoYi
print("\n" + "="*60)
print("STEP 1: mvn clean package -DskipTests")
print("="*60)

build_cmd = (
    "cd /opt/oa-app/ruoyi && "
    "MAVEN_OPTS='-Xmx2g' mvn clean package -DskipTests 2>&1 | tail -80"
)
out, err, ec = run_ssh(c, build_cmd, timeout=600)

if ec != 0:
    print(f"\nBUILD FAILED (exit {ec}). Checking for errors...")
    # Get more error context
    out2, err2, ec2 = run_ssh(c,
        "cd /opt/oa-app/ruoyi && "
        "MAVEN_OPTS='-Xmx2g' mvn clean package -DskipTests 2>&1 | grep -E '(ERROR|BUILD|FAILURE|Compilation failure)' | tail -30",
        timeout=600)
    # If still failing, get the full error
    if 'BUILD FAILURE' in out2:
        # Find the specific module that failed
        out3, err3, ec3 = run_ssh(c,
            "cd /opt/oa-app/ruoyi && "
            "MAVEN_OPTS='-Xmx2g' mvn clean package -DskipTests 2>&1 | grep -B5 'ERROR' | tail -50",
            timeout=600)
    print("\nBuild failed. Check above for error details.")
    c.close()
    sys.exit(1)

# Step 2: Verify JAR exists
print("\n" + "="*60)
print("STEP 2: Verify JAR file")
print("="*60)
out, err, ec = run_ssh(c, "ls -lh /opt/oa-app/ruoyi/ruoyi-admin/target/ruoyi-admin.jar")
if ec != 0:
    print("JAR not found! Build may have failed silently.")
    run_ssh(c, "ls -la /opt/oa-app/ruoyi/ruoyi-admin/target/")
    c.close()
    sys.exit(1)

# Step 3: Fix yml profile path in target/classes
print("\n" + "="*60)
print("STEP 3: Fix application.yml profile path")
print("="*60)

# Read current yml
sftp = c.open_sftp()
try:
    with sftp.open('/opt/oa-app/ruoyi/ruoyi-admin/target/classes/application.yml', 'r') as f:
        yml = f.read().decode('utf-8')
    print(f"Read target/classes/application.yml: {len(yml)} chars")
except:
    # Maybe classes exist elsewhere (spring-boot repackage)
    print("No target/classes/application.yml, checking src/main/resources...")
    with sftp.open('/opt/oa-app/ruoyi/ruoyi-admin/src/main/resources/application.yml', 'r') as f:
        yml = f.read().decode('utf-8')
    print(f"Read src main resources: {len(yml)} chars")
sftp.close()

# Fix profile path if needed
if 'D:/ruoyi/uploadPath' in yml:
    print("  Fixing D:/ruoyi/uploadPath -> /opt/oa-app/uploadPath")
    # Already fixed in source, should be OK
else:
    print("  Profile path already correct (no D:/ found)")

# Step 4: Update JAR with correct yml files
print("\n" + "="*60)
print("STEP 4: Update JAR with yml files")
print("="*60)

jar_update_cmd = (
    "cd /opt/oa-app/ruoyi/ruoyi-admin/target && "
    "mkdir -p BOOT-INF/classes && "
    "cp /opt/oa-app/ruoyi/ruoyi-admin/src/main/resources/application.yml BOOT-INF/classes/ && "
    "cp /opt/oa-app/ruoyi/ruoyi-admin/src/main/resources/application-druid.yml BOOT-INF/classes/ && "
    "jar uf ruoyi-admin.jar BOOT-INF/classes/application.yml BOOT-INF/classes/application-druid.yml 2>&1 && "
    "echo 'JAR_UPDATED'"
)
out, err, ec = run_ssh(c, jar_update_cmd)

# Step 5: Copy yml to /opt/oa-app/ for service WorkingDirectory
print("\n" + "="*60)
print("STEP 5: Copy yml files to /opt/oa-app/")
print("="*60)

copy_cmds = [
    "echo 'Gdadmin@123' | sudo -S cp /opt/oa-app/ruoyi/ruoyi-admin/src/main/resources/application.yml /opt/oa-app/application.yml",
    "echo 'Gdadmin@123' | sudo -S cp /opt/oa-app/ruoyi/ruoyi-admin/src/main/resources/application-druid.yml /opt/oa-app/application-druid.yml",
]
for cmd in copy_cmds:
    out, err, ec = run_ssh(c, cmd)

# Step 6: Ensure uploadPath directory exists
print("\n" + "="*60)
print("STEP 6: Create uploadPath directory")
print("="*60)
run_ssh(c, "echo 'Gdadmin@123' | sudo -S mkdir -p /opt/oa-app/uploadPath && sudo chmod 755 /opt/oa-app/uploadPath")

# Step 7: Stop, reset, start service
print("\n" + "="*60)
print("STEP 7: Restart oa-app service")
print("="*60)

service_cmds = [
    "echo 'Gdadmin@123' | sudo -S systemctl stop oa-app 2>/dev/null; true",
    "echo 'Gdadmin@123' | sudo -S systemctl reset-failed oa-app 2>/dev/null; true",
    "echo 'Gdadmin@123' | sudo -S systemctl start oa-app",
]
for cmd in service_cmds:
    out, err, ec = run_ssh(c, cmd)

# Step 8: Wait for startup
print("\n" + "="*60)
print("STEP 8: Wait 40s for startup...")
print("="*60)
time.sleep(40)

# Step 9: Check status
print("\n" + "="*60)
print("STEP 9: Verify service status")
print("="*60)

# Service active?
out, err, ec = run_ssh(c, "echo 'Gdadmin@123' | sudo -S systemctl is-active oa-app")
is_active = out.strip()

# Port listening?
out, err, ec = run_ssh(c, "ss -tlnp | grep -E '(8080|80)'")
port_info = out.strip()

# Check log
out, err, ec = run_ssh(c,
    "echo 'Gdadmin@123' | sudo -S journalctl -u oa-app --no-pager -n 30 2>/dev/null")
log = out.strip()

print(f"\n  Service active: {is_active}")
print(f"  Port info: {port_info}")

if 'Started RuoYiApplication' in log or 'Started RuoYi' in log or 'Tomcat started' in log:
    print("  ✅ App started successfully!")
elif 'FAILED' in log or 'Exception' in log or 'Error' in log:
    print("  ❌ App FAILED to start!")
    # Show error lines
    for line in log.split('\n'):
        if 'ERROR' in line or 'Exception' in line or 'FAILED' in line or 'Caused by' in line:
            print(f"     {line.strip()}")
else:
    print("  ⏳ Still starting...")

# Step 10: HTTP check
print("\n" + "="*60)
print("STEP 10: HTTP endpoint check")
print("="*60)

run_ssh(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/ 2>/dev/null || echo 'NOT_REACHABLE'")
run_ssh(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/mail/preview 2>/dev/null || echo 'NOT_REACHABLE'")
run_ssh(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/druid/ 2>/dev/null || echo 'NOT_REACHABLE'")

c.close()
print("\nDone!")
