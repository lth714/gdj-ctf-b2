#!/usr/bin/env python3
"""Check C1: Register controller details and fix register flow"""
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
# 1. Read SysRegisterController source
# ============================================================
print("=" * 60)
print("1. SysRegisterController.java")
print("=" * 60)
run(c1, 'cat /opt/oa-app/ruoyi/ruoyi-admin/src/main/java/com/ruoyi/web/controller/system/SysRegisterController.java')

# ============================================================
# 2. Check SysRegisterService
# ============================================================
print("\n" + "=" * 60)
print("2. SysRegisterService.java")
print("=" * 60)
run(c1, 'cat /opt/oa-app/ruoyi/ruoyi-framework/src/main/java/com/ruoyi/framework/shiro/service/SysRegisterService.java')

# ============================================================
# 3. Test register with GET first to get captcha session
# ============================================================
print("\n" + "=" * 60)
print("3. TEST REGISTER FLOW")
print("=" * 60)

# First: try to understand why POST body isn't being read
# Check if Shiro's CaptchaValidateFilter is consuming the body
run(c1, 'grep -n "getParameter\|getInputStream\|getReader" /opt/oa-app/ruoyi/ruoyi-framework/src/main/java/com/ruoyi/framework/shiro/web/filter/captcha/CaptchaValidateFilter.java')

# The validateResponse method reads the captcha from request.getParameter
# But this shouldn't consume the body for POST with application/x-www-form-urlencoded

# Let's try with proper cookie/session flow
print("\n--- Step 1: Get captcha image and session ---")
run(c1, 'curl -s -v -c /tmp/cjar.txt http://localhost:8080/captcha/captchaImage -o /tmp/captcha.png 2>&1 | grep -i "set-cookie\|JSESSIONID"')

# Check the session cookie
run(c1, 'cat /tmp/cjar.txt')

# Step 2: Try register with the session cookie
print("\n--- Step 2: Register with session ---")
run(c1, 'curl -s -v -b /tmp/cjar.txt -X POST http://localhost:8080/register '
     '-H "Content-Type: application/x-www-form-urlencoded" '
     '-d "username=testuser12&password=Test@1234&confirmPassword=Test@1234&validateCode=gdj2024&acceptTerm=true" 2>&1')

# ============================================================
# 4. Try with different approaches
# ============================================================
print("\n" + "=" * 60)
print("4. ALTERNATIVE APPROACHES")
print("=" * 60)

# Check if the issue is with the captcha session key
run(c1, "grep -rn 'KAPTCHA_SESSION_KEY\|CAPTCHA\|validateCode\|CURRENT_VALIDATECODE' /opt/oa-app/ruoyi/ruoyi-framework/src/main/java/com/ruoyi/framework/shiro/web/filter/captcha/CaptchaValidateFilter.java")

# Check what ShiroConstants.CURRENT_VALIDATECODE is
run(c1, "grep -rn 'CURRENT_VALIDATECODE' /opt/oa-app/ruoyi/ruoyi-common/src/main/java/com/ruoyi/common/constant/ShiroConstants.java")

c1.close()
print("\nDone!")
