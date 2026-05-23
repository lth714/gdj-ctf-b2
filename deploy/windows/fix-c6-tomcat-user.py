#!/usr/bin/env python3
"""Fix C6: Run oa-app as tomcat user instead of root for sudo tee escalation chain"""
import paramiko
import sys

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
    return out, err, ec

c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.101.140', username='gdadmin', password='Gdadmin@123', timeout=10)

# ============================================================
# Step 1: Create tomcat user
# ============================================================
print("=" * 60)
print("STEP 1: CREATE tomcat USER")
print("=" * 60)
run(c1, "echo 'Gdadmin@123' | sudo -S useradd -m -s /bin/bash tomcat 2>&1 || echo 'User may already exist'")
run(c1, "echo 'tomcat:t0mcat@2024' | sudo -S chpasswd")
run(c1, "id tomcat")

# ============================================================
# Step 2: Set up sudoers for tomcat (tee privilege)
# ============================================================
print("\n" + "=" * 60)
print("STEP 2: CONFIGURE SUDO FOR tomcat")
print("=" * 60)
sudoers_content = 'tomcat ALL=(root) NOPASSWD: /usr/bin/tee'
run(c1, f"echo '{sudoers_content}' | sudo -S tee /etc/sudoers.d/tomcat")
run(c1, "sudo -S chmod 440 /etc/sudoers.d/tomcat")
run(c1, "sudo -S cat /etc/sudoers.d/tomcat")

# ============================================================
# Step 3: Fix permissions for oa-app directory
# ============================================================
print("\n" + "=" * 60)
print("STEP 3: FIX PERMISSIONS")
print("=" * 60)
run(c1, "echo 'Gdadmin@123' | sudo -S chown -R tomcat:tomcat /opt/oa-app")
run(c1, "ls -la /opt/oa-app/")

# ============================================================
# Step 4: Update systemd service to run as tomcat
# ============================================================
print("\n" + "=" * 60)
print("STEP 4: UPDATE SYSTEMD SERVICE")
print("=" * 60)
run(c1, "cat /etc/systemd/system/oa-app.service")

# Update the service file
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

run(c1, f"echo 'Gdadmin@123' | sudo -S tee /etc/systemd/system/oa-app.service << 'SERVICEEOF'\n{service_content}\nSERVICEEOF")
run(c1, "echo 'Gdadmin@123' | sudo -S systemctl daemon-reload")
run(c1, "cat /etc/systemd/system/oa-app.service")

# ============================================================
# Step 5: Stop, restart service as tomcat
# ============================================================
print("\n" + "=" * 60)
print("STEP 5: RESTART SERVICE AS tomcat")
print("=" * 60)
run(c1, "echo 'Gdadmin@123' | sudo -S systemctl stop oa-app")
run(c1, "sleep 3 && echo OK")
run(c1, "echo 'Gdadmin@123' | sudo -S systemctl start oa-app")
run(c1, "sleep 8 && echo OK")
run(c1, "echo 'Gdadmin@123' | sudo -S systemctl status oa-app --no-pager | head -15")

# ============================================================
# Step 6: Verify tomcat user is running the process
# ============================================================
print("\n" + "=" * 60)
print("STEP 6: VERIFY")
print("=" * 60)
run(c1, "ps aux | grep java | grep -v grep")
run(c1, "curl -s http://localhost:8080/api/login?username=admin&password=admin123")

# ============================================================
# Step 7: Test FreeMarker SSTI now runs as tomcat (not root)
# ============================================================
print("\n" + "=" * 60)
print("STEP 7: VERIFY SSTI NOW RUNS AS tomcat")
print("=" * 60)
# URL encode: <#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}
run(c1, "curl -s 'http://localhost:8080/mail/preview?content=%3C%23assign%20ex%3D%22freemarker.template.utility.Execute%22%3Fnew%28%29%3E%24%7Bex%28%22id%22%29%7D'")
# Verify sudo tee works as tomcat
run(c1, "echo 'Gdadmin@123' | sudo -S -u tomcat sudo -l 2>&1")

c1.close()
print("\nDone! C6 fix complete.")
