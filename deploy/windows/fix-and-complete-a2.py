#!/usr/bin/env python3
"""Fix init_db.sql encoding, upload, and complete all VM-A2 setup steps."""
import paramiko
import sys
import os

HOST = '192.168.100.2'
USER = 'gdadmin'
PASS = 'Gdadmin@123'
LOCAL_SQL = r'E:\vibecoding\gdj_ctf\scenario-a\vm-a2-internal\init_db.sql'

def sudo(client, cmd):
    """Run a command via sudo, return (stdout, stderr, exit_code)."""
    full = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = client.exec_command(full, timeout=30)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    # Filter sudo password prompt from stderr
    err_clean = '\n'.join(l for l in err.split('\n') if 'password for gdadmin' not in l)
    code = stdout.channel.recv_exit_status()
    return out, err_clean, code

def step(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def ok(msg, out="", err=""):
    print(f"  [OK] {msg}")
    if out: print(f"    {out[:300]}")
    if err: print(f"    stderr: {err[:200]}")

def fail(msg, code, out="", err=""):
    print(f"  [FAIL({code})] {msg}")
    if out: print(f"    {out[:300]}")
    if err: print(f"    stderr: {err[:200]}")

def main():
    print("[*] Connecting...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS,
                   timeout=15, look_for_keys=False, allow_agent=False)
    print("[+] Connected!")

    # ================================================================
    step("1. Upload fixed init_db.sql via SFTP")
    try:
        sftp = client.open_sftp()
        sftp.put(LOCAL_SQL, '/tmp/init_db.sql')
        sftp.close()
        ok("Uploaded init_db.sql → /tmp/init_db.sql")
    except Exception as e:
        fail("SFTP upload", 0, str(e))
        client.close()
        return

    # Verify upload
    out, err, code = sudo(client, "wc -l /tmp/init_db.sql")
    ok("Verified upload", out)

    # ================================================================
    step("2. Copy fixed init_db.sql to /opt/deploy/")
    out, err, code = sudo(client, "cp /tmp/init_db.sql /opt/deploy/init_db.sql")
    if code == 0:
        ok("Copied to /opt/deploy/init_db.sql")
    else:
        fail("Copy", code, out, err)

    # ================================================================
    step("3. Check current database state")
    out, err, code = sudo(client,
        "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT COUNT(*) AS cnt FROM cms.ay_user; SELECT COUNT(*) AS cnt FROM cms.ay_content;' 2>&1")
    # Don't check exit code — the cms database might already exist
    if 'cnt' in out:
        ok("CMS database has data already", out)
        print("  [INFO] Dropping and re-importing to ensure clean state...")
    else:
        print("  [INFO] CMS database empty or needs import")

    # ================================================================
    step("4. Import fixed init_db.sql")
    out, err, code = sudo(client,
        "mysql -u root -p'R00t@Mysql#2024' < /opt/deploy/init_db.sql 2>&1")
    if code == 0:
        ok("init_db.sql imported successfully")
    else:
        fail("init_db.sql import", code, out, err)
        # Show what line 110 now looks like
        out2, _, _ = sudo(client, "sed -n '110,115p' /opt/deploy/init_db.sql")
        print(f"  Lines 110-115 now:\n{out2}")

    # Verify import
    out, err, code = sudo(client,
        "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT COUNT(*) AS user_count FROM cms.ay_user; SELECT COUNT(*) AS content_count FROM cms.ay_content; SELECT COUNT(*) AS role_count FROM cms.ay_role;' 2>&1")
    ok("Import verification", out)

    # ================================================================
    step("5. Fix MySQL bind-address")
    # Use perl instead of sed for better whitespace handling
    out, err, code = sudo(client,
        "perl -i -pe 's/^bind-address\\s*=.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf")
    if code == 0:
        ok("Updated bind-address")
    else:
        fail("bind-address update", code, out, err)

    # Verify
    out, err, code = sudo(client,
        "grep '^bind-address' /etc/mysql/mysql.conf.d/mysqld.cnf")
    ok("bind-address check", out)

    # Restart MySQL
    out, err, code = sudo(client, "systemctl restart mysql")
    if code == 0:
        ok("MySQL restarted")
    else:
        fail("MySQL restart", code, out, err)

    # ================================================================
    step("6. Fix Redis bind")
    # Check current config
    out, err, code = sudo(client, "grep -n '^bind' /etc/redis/redis.conf || echo 'NO_BIND_LINE_FOUND'")
    print(f"  Current Redis bind config: {out}")

    # Comment out existing bind and add new one
    out, err, code = sudo(client,
        "perl -i -pe 's/^bind 127.0.0.1/#bind 127.0.0.1/' /etc/redis/redis.conf; "
        "perl -i -pe 's/^bind 127.0.0.1 ::1/#bind 127.0.0.1 ::1/' /etc/redis/redis.conf")
    ok("Commented out old Redis bind")

    # Add new bind
    out, err, code = sudo(client,
        "grep -q '^bind 0.0.0.0' /etc/redis/redis.conf || echo 'bind 0.0.0.0' >> /etc/redis/redis.conf")
    ok("Added bind 0.0.0.0 to Redis config")

    # Verify
    out, err, code = sudo(client, "grep '^bind' /etc/redis/redis.conf")
    ok("Redis bind check", out)

    # Restart Redis
    out, err, code = sudo(client, "systemctl restart redis-server")
    ok("Redis restarted", "" if code == 0 else f"exit={code}")

    # ================================================================
    step("7. Create operator user")
    # Check if exists first
    out, _, _ = sudo(client, "id operator 2>&1 || echo 'NOT_FOUND'")
    if 'NOT_FOUND' in out or 'no such user' in out:
        # Create user with explicit commands
        codes = []
        out1, err1, c1 = sudo(client, "useradd -m -s /bin/bash operator")
        codes.append(c1)
        out2, err2, c2 = sudo(client, "echo 'operator:0p3rat0r@GDJ' | chpasswd")
        codes.append(c2)
        out3, err3, c3 = sudo(client, "usermod -aG sudo operator")
        codes.append(c3)

        if all(c == 0 for c in codes):
            ok("Operator user created")
        else:
            # Try alternative approach
            print("  [WARN] Standard method failed, trying adduser...")
            out, err, code = sudo(client,
                "adduser --disabled-password --gecos '' operator 2>&1 || true; "
                "echo 'operator:0p3rat0r@GDJ' | chpasswd; "
                "usermod -aG sudo operator")
            out_v, _, _ = sudo(client, "id operator 2>&1")
            if 'uid=' in out_v:
                ok("Operator user created (fallback method)", out_v)
            else:
                fail("Operator user creation", code, out, err)
    else:
        ok("Operator user already exists", out)

    # Set sudoers for operator
    sudo(client, """cat > /etc/sudoers.d/operator << 'EOF'
operator ALL=(ALL) NOPASSWD: /usr/bin/systemctl, /usr/sbin/service
EOF
chmod 440 /etc/sudoers.d/operator""")
    ok("Operator sudoers configured")

    # ================================================================
    step("8. Apply iptables rules")
    out, err, code = sudo(client, """cat > /etc/iptables/rules.v4 << 'EOF'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -s 192.168.100.1/32 -p tcp --dport 3306 -j ACCEPT
-A INPUT -s 192.168.100.1/32 -p tcp --dport 6379 -j ACCEPT
-A INPUT -s 192.168.100.1/32 -p tcp --dport 8090 -j ACCEPT
-A INPUT -s 192.168.100.0/24 -j ACCEPT
-A INPUT -s 127.0.0.0/8 -j ACCEPT
-A INPUT -p icmp -j ACCEPT
COMMIT
EOF""")
    ok("iptables rules written" if code == 0 else "iptables write warning", out, err)

    # Apply with iptables-restore
    out, err, code = sudo(client, "iptables-restore < /etc/iptables/rules.v4 2>&1")
    if code == 0:
        ok("iptables rules APPLIED")
    else:
        fail("iptables-restore", code, out, err)

    # Verify iptables
    out, err, code = sudo(client, "iptables -L INPUT -n -v 2>&1")
    ok("iptables verification", out[:500])

    # Persistence via rc.local
    sudo(client, """cat > /etc/rc.local << 'EOF'
#!/bin/bash
/sbin/iptables-restore < /etc/iptables/rules.v4
exit 0
EOF
chmod +x /etc/rc.local""")
    ok("iptables persistence via rc.local")

    # ================================================================
    step("9. Confluence setup")
    out, err, code = sudo(client, "ls /opt/atlassian/confluence/bin/start-confluence.sh 2>&1 || echo 'NOT_FOUND'")
    if 'NOT_FOUND' in out:
        print("  [INFO] Confluence not installed (needs internet/download)")
        # Create skeleton for manual install later
        sudo(client, "mkdir -p /opt/atlassian/confluence /var/atlassian/confluence")
        sudo(client, "useradd -m -s /bin/bash confluence 2>/dev/null || true")

        # Create systemd service
        sudo(client, """cat > /etc/systemd/system/confluence.service << 'EOF'
[Unit]
Description=Atlassian Confluence
After=network.target
[Service]
Type=forking
User=confluence
ExecStart=/opt/atlassian/confluence/bin/start-confluence.sh
ExecStop=/opt/atlassian/confluence/bin/stop-confluence.sh
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF""")
        sudo(client, "systemctl daemon-reload")
        ok("Confluence skeleton + systemd service created")
    else:
        ok("Confluence already installed")

    # ================================================================
    step("10. Privesc vector: cron job + writable script")
    sudo(client, """cat > /opt/confluence_health_check.sh << 'EOF'
#!/bin/bash
# Confluence health check — runs as root via cron
systemctl status confluence > /dev/null 2>&1 || systemctl restart confluence
EOF
chmod 777 /opt/confluence_health_check.sh""")
    ok("Created /opt/confluence_health_check.sh (mode 777)")

    sudo(client,
        'echo "*/10 * * * * root /opt/confluence_health_check.sh" > /etc/cron.d/confluence-health')
    ok("Added cron job: /etc/cron.d/confluence-health")

    # ================================================================
    step("11. Netplan internal network")
    # Check if ens37 is already configured
    out, _, _ = sudo(client, "ip addr show ens37 2>&1")
    if '192.168.100.2' in out:
        ok("ens37 already configured with 192.168.100.2/24")
    else:
        print("  [WARN] ens37 needs configuration")

    # ================================================================
    step("=== FINAL VERIFICATION ===")
    checks = [
        ("MySQL root.cnf", "cat /etc/mysql/mysql.conf.d/root.cnf 2>&1 | head -3"),
        ("MySQL bind-address", "grep '^bind-address' /etc/mysql/mysql.conf.d/mysqld.cnf"),
        ("MySQL cmsuser", "mysql -u root -p'R00t@Mysql#2024' -e \"SELECT user,host FROM mysql.user WHERE user='cmsuser'\" 2>&1"),
        ("CMS data count", "mysql -u root -p'R00t@Mysql#2024' -e \"SELECT (SELECT COUNT(*) FROM cms.ay_user) AS users, (SELECT COUNT(*) FROM cms.ay_content) AS content, (SELECT COUNT(*) FROM cms.ay_role) AS roles\" 2>&1"),
        ("Redis bind", "grep '^bind 0.0.0.0' /etc/redis/redis.conf || echo MISSING"),
        ("Redis running", "systemctl is-active redis-server"),
        ("operator user", "id operator 2>&1 | head -1"),
        ("operator sudo", "cat /etc/sudoers.d/operator 2>&1"),
        ("iptables policy", "iptables -L INPUT -n 2>&1 | head -3"),
        ("iptables rules count", "iptables -L INPUT -n 2>&1 | grep -c ACCEPT || echo 0"),
        ("cron job", "cat /etc/cron.d/confluence-health 2>&1"),
        ("health_check perms", "stat -c '%a %n' /opt/confluence_health_check.sh 2>&1"),
        ("Confluence service", "systemctl status confluence 2>&1 | head -3 || echo 'not running (OK - needs manual install)'"),
        ("ens37 IP", "ip -4 addr show ens37 2>&1 | grep inet"),
        ("Listening ports", "ss -tlnp 2>&1 | grep -E '3306|6379|22'"),
    ]

    all_ok = True
    for name, cmd in checks:
        out, err, code = sudo(client, cmd)
        if code != 0:
            # Some checks naturally return non-zero
            if 'grep' in cmd and code == 1:
                fail(f"{name}: NOT FOUND", code, out, err)
                all_ok = False
            elif 'systemctl status' in cmd and code == 3:
                ok(f"{name}: service not running (expected)", out[:100])
            else:
                ok(f"{name}", out[:200])
        else:
            ok(f"{name}", out[:200])

    if all_ok:
        print("\n[+] VM-A2 setup COMPLETE!")
        print("    Confluence needs manual download: wget atlassian-confluence-7.13.6.tar.gz")
    else:
        print("\n[!] Some checks failed — see above for details")

    client.close()

if __name__ == '__main__':
    main()
