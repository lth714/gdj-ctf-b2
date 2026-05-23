#!/usr/bin/env python3
"""Fix C6: Run oa-app as tomcat user instead of root for sudo tee escalation chain"""
import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run(ssh, cmd, timeout=30):
    print(f">>> {cmd[:200]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        print(f"  {out.strip()[:2000]}")
    if err.strip() and ec != 0:
        print(f"  [err] {err.strip()[:300]}")
    return out, err, ec, stdin

def sudo(ssh, cmd, timeout=30):
    """Run a command with sudo, providing password via stdin"""
    full_cmd = f"sudo -S {cmd} 2>&1"
    print(f">>> sudo {cmd[:180]}")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    # Send password
    stdin.write('Gdadmin@123\n')
    stdin.flush()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        print(f"  {out.strip()[:2000]}")
    if err.strip():
        # Filter out the sudo prompt noise
        err_clean = err.strip().replace('[sudo] password for gdadmin: ', '').strip()
        if err_clean:
            print(f"  [err] {err_clean[:300]}")
    return out, err, ec

c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.101.140', username='gdadmin', password='Gdadmin@123', timeout=10)

# ============================================================
# Step 1: Ensure tomcat user exists
# ============================================================
print("=" * 60)
print("STEP 1: ENSURE tomcat USER EXISTS")
print("=" * 60)
run(c1, "id tomcat 2>&1")
# Create if needed
run(c1, "id tomcat 2>/dev/null || sudo -S useradd -m -s /bin/bash tomcat <<< 'Gdadmin@123'")

# Set password for tomcat
print("\n--- Set tomcat password ---")
sudo(c1, "bash -c \"echo 'tomcat:t0mcat@2024' | chpasswd\"")

# ============================================================
# Step 2: Set up sudoers for tomcat
# ============================================================
print("\n" + "=" * 60)
print("STEP 2: CONFIGURE SUDO FOR tomcat")
print("=" * 60)
sudo(c1, "bash -c \"echo 'tomcat ALL=(root) NOPASSWD: /usr/bin/tee' > /etc/sudoers.d/tomcat\"")
sudo(c1, "chmod 440 /etc/sudoers.d/tomcat")
run(c1, "sudo -n cat /etc/sudoers.d/tomcat 2>&1 || cat /etc/sudoers.d/tomcat 2>&1")

# ============================================================
# Step 3: Fix permissions
# ============================================================
print("\n" + "=" * 60)
print("STEP 3: FIX PERMISSIONS")
print("=" * 60)
sudo(c1, "chown -R tomcat:tomcat /opt/oa-app")
run(c1, "ls -la /opt/oa-app/")

# ============================================================
# Step 4: Update systemd service
# ============================================================
print("\n" + "=" * 60)
print("STEP 4: UPDATE SYSTEMD SERVICE")
print("=" * 60)

service_content = """[Unit]
Description=GDJ OA System (RuoYi)
After=network.target mysql.service

[Service]
Type=simple
User=tomcat
Group=tomcat
WorkingDirectory=/opt/oa-app
ExecStart=/usr/bin/java -jar /opt/oa-app/ruoyi/ruoyi-admin/target/ruoyi-admin.jar --spring.profiles.active=druid
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target"""

sudo(c1, f"bash -c 'cat > /etc/systemd/system/oa-app.service << EOF\n{service_content}\nEOF'")
sudo(c1, "systemctl daemon-reload")
run(c1, "cat /etc/systemd/system/oa-app.service")

# ============================================================
# Step 5: Restart service
# ============================================================
print("\n" + "=" * 60)
print("STEP 5: RESTART SERVICE AS tomcat")
print("=" * 60)
sudo(c1, "systemctl stop oa-app 2>&1 || true")
time.sleep(3)
sudo(c1, "systemctl start oa-app")
print("  Waiting 15s for startup...")
time.sleep(15)
run(c1, "systemctl status oa-app --no-pager 2>&1 | head -20")

# ============================================================
# Step 6: Verify
# ============================================================
print("\n" + "=" * 60)
print("STEP 6: VERIFY")
print("=" * 60)
run(c1, "ps aux | grep java | grep -v grep")
run(c1, "curl -s http://localhost:8080/api/login?username=admin&password=admin123")

# Check it runs as tomcat
print("\n--- SSTI as tomcat ---")
run(c1, "curl -s 'http://localhost:8080/mail/preview?content=%3C%23assign%20ex%3D%22freemarker.template.utility.Execute%22%3Fnew%28%29%3E%24%7Bex%28%22id%22%29%7D'")

# Test sudo tee as tomcat
print("\n--- sudo tee test as tomcat ---")
run(c1, "sudo -u tomcat sudo -n -l 2>&1")

c1.close()
print("\nDone! C6 fix complete.")
