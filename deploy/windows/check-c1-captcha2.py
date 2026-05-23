#!/usr/bin/env python3
"""Check C1: Find CaptchaValidateFilter in admin JAR, check register endpoint"""
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
# 1. Find CaptchaValidateFilter.class in admin JAR
# ============================================================
print("=" * 60)
print("1. FIND CaptchaValidateFilter IN ADMIN JAR")
print("=" * 60)

# List all occurrences
run(c1, 'unzip -l /opt/oa-app/ruoyi/ruoyi-admin/target/ruoyi-admin.jar 2>/dev/null | grep -i CaptchaValidateFilter')

# Check if it's nested inside framework JAR within BOOT-INF/lib
run(c1, 'unzip -l /opt/oa-app/ruoyi/ruoyi-admin/target/ruoyi-admin.jar 2>/dev/null | grep -i "ruoyi-framework"')

# ============================================================
# 2. Extract the framework JAR from admin JAR and check inside
# ============================================================
print("\n" + "=" * 60)
print("2. EXTRACT FRAMEWORK JAR FROM ADMIN JAR")
print("=" * 60)

run(c1, 'cd /tmp && unzip -o /opt/oa-app/ruoyi/ruoyi-admin/target/ruoyi-admin.jar '
     'BOOT-INF/lib/ruoyi-framework-4.8.3.jar 2>&1')

# Now check inside the extracted framework JAR
run(c1, 'unzip -l /tmp/BOOT-INF/lib/ruoyi-framework-4.8.3.jar 2>/dev/null | grep -i CaptchaValidateFilter')

# Extract and check
run(c1, 'cd /tmp && unzip -o BOOT-INF/lib/ruoyi-framework-4.8.3.jar '
     'com/ruoyi/framework/shiro/web/filter/captcha/CaptchaValidateFilter.class 2>&1')

# Check for 'gdj' in the extracted class
print("\n--- Checking for gdj in class ---")
run(c1, "grep -a 'gdj' /tmp/com/ruoyi/framework/shiro/web/filter/captcha/CaptchaValidateFilter.class && echo 'FOUND' || echo 'NOT FOUND - NEED REBUILD'")

# ============================================================
# 3. Check source file content
# ============================================================
print("\n" + "=" * 60)
print("3. SOURCE FILE CONTENT")
print("=" * 60)
run(c1, 'head -60 /opt/oa-app/ruoyi/ruoyi-framework/src/main/java/com/ruoyi/framework/shiro/web/filter/captcha/CaptchaValidateFilter.java')

# ============================================================
# 4. Check RegisterController
# ============================================================
print("\n" + "=" * 60)
print("4. REGISTER CONTROLLER")
print("=" * 60)
run(c1, 'find /opt/oa-app -name "RegisterController.java" -o -name "SysRegisterController.java" 2>/dev/null')
run(c1, 'find /opt/oa-app -name "*.java" -exec grep -l "register" {} \; 2>/dev/null | head -10')

# ============================================================
# 5. Check the actual running app behavior for register
# ============================================================
print("\n" + "=" * 60)
print("5. REGISTER ENDPOINT DETAILS")
print("=" * 60)

# The HTML form shows what params it sends - get the register page and look at form fields
run(c1, 'curl -s http://localhost:8080/register 2>&1 | grep -i "input\|form\|name=" | head -30')

# Also try the Shiro-registered register endpoint (RuoYi uses SysRegisterController)
run(c1, 'curl -s -X POST http://localhost:8080/register -H "Content-Type: application/x-www-form-urlencoded" '
     '-d "username=testuser11&password=Test@1234&confirmPassword=Test@1234&email=test11@test.com&validateCode=gdj2024&captcha=gdj2024"')

# ============================================================
# 6. Check if we can rebuild just the framework module
# ============================================================
print("\n" + "=" * 60)
print("6. CHECK MAVEN REBUILD")
print("=" * 60)
run(c1, 'which mvn && mvn --version 2>&1 | head -5')
run(c1, 'ls /opt/oa-app/ruoyi/pom.xml')

c1.close()
print("\nDone!")
