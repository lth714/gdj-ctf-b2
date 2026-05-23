#!/usr/bin/env python3
"""Verify all C2 services: Drupal, LDAP, Samba, MySQL, iptables"""
import paramiko

host = '192.168.101.141'
user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(c, cmd, use_sudo=False, timeout=30):
    if use_sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:150]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  out: {out.strip()[:1000]}")
    if err.strip(): print(f"  err: {err.strip()[:500]}")
    return out, err, ec

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

# 1. Drupal verification
print("="*60)
print("1. DRUPAL 7.57")
print("="*60)
run(c, "curl -s -o /dev/null -w 'HTTP: %{http_code}' http://localhost/ && echo ''")
run(c, "curl -s -o /dev/null -w 'Login: %{http_code}' http://localhost/user/login && echo ''")
run(c, "curl -s -o /dev/null -w 'Register: %{http_code}' http://localhost/user/register && echo ''")
run(c, "curl -s http://localhost/user/register | grep -o 'form_id.*user_register_form' | head -1")

# CVE-2018-7600 test - check if the vulnerable form element exists
print("\n--- CVE-2018-7600 check ---")
run(c, "curl -s http://localhost/user/register | grep -o 'name=\"mail\"' | head -1")
run(c, "curl -s http://localhost/user/register | grep -o 'name=\"form_id\"' | head -1")

# 2. LDAP verification
print("\n" + "="*60)
print("2. OPENLDAP")
print("="*60)
run(c, "ldapsearch -x -H ldap://localhost -D 'cn=admin,dc=gdj,dc=local' -w 'Ldap@Admin#2024' -b 'dc=gdj,dc=local' '(objectClass=*)' dn | head -20")
run(c, "ss -tlnp | grep 389")

# 3. Samba verification
print("\n" + "="*60)
print("3. SAMBA")
print("="*60)
run(c, "smbclient -L localhost -N 2>/dev/null | head -10")
run(c, "ss -tlnp | grep -E '445|139'")
# Check if 运维手册.txt is readable
run(c, "smbclient //localhost/public -N -c 'ls' 2>/dev/null")

# 4. MySQL verification
print("\n" + "="*60)
print("4. MYSQL")
print("="*60)
run(c, "ss -tlnp | grep 3306")
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT user, host FROM mysql.user;' 2>/dev/null")
# Show oa database users
run(c, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT username, password FROM oa.users;' 2>/dev/null")

# 5. iptables verification
print("\n" + "="*60)
print("5. IPTABLES")
print("="*60)
run(c, "echo 'Gdadmin@123' | sudo -S iptables -L INPUT -n --line-numbers 2>/dev/null")

# 6. Service status
print("\n" + "="*60)
print("6. SERVICE STATUS")
print("="*60)
for svc in ['apache2', 'slapd', 'smbd', 'nmbd', 'mysql']:
    run(c, f"echo 'Gdadmin@123' | sudo -S systemctl is-active {svc} 2>/dev/null | tr -d '\\n' && echo '  <- {svc}'")

# 7. Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
run(c, "curl -s http://localhost/ | grep -o '<title>[^<]*</title>'")
run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost/user/register && echo ' <- /user/register (CVE-2018-7600 target)'")

c.close()
print("\nDone!")
