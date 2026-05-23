#!/usr/bin/env python3
"""Complete VM-A2 Internal setup - SSH and finish all remaining steps."""
import paramiko
import sys
import time

HOST = '192.168.100.2'
USER = 'gdadmin'
PASS = 'Gdadmin@123'

def sudo_run(client, cmd, desc=""):
    """Run command with sudo, return (stdout, stderr, exit_code)."""
    full_cmd = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = client.exec_command(full_cmd, timeout=30)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    code = stdout.channel.recv_exit_status()
    if desc:
        status = "OK" if code == 0 else f"FAIL({code})"
        print(f"  [{status}] {desc}")
        if out:
            print(f"    stdout: {out[:200]}")
        if err and 'password for gdadmin' not in err:
            print(f"    stderr: {err[:200]}")
    return out, err, code

def main():
    print(f"[*] Connecting to {HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS,
                   timeout=15, look_for_keys=False, allow_agent=False)
    print("[+] Connected!\n")

    # ================================================================
    print("=" * 60)
    print(" Step 1: MySQL root.cnf (for LOAD_FILE attack chain)")
    print("=" * 60)
    sudo_run(client, """cat > /etc/mysql/mysql.conf.d/root.cnf << 'EOF'
[client]
user=root
password=R00t@Mysql#2024
EOF
chmod 644 /etc/mysql/mysql.conf.d/root.cnf""", "Create root.cnf")

    # ================================================================
    print("\n" + "=" * 60)
    print(" Step 2: Import init_db.sql")
    print("=" * 60)
    sudo_run(client,
        "mysql -u root -p'R00t@Mysql#2024' < /opt/deploy/init_db.sql 2>&1",
        "Import init_db.sql")

    # ================================================================
    print("\n" + "=" * 60)
    print(" Step 3: MySQL bind-address → 0.0.0.0")
    print("=" * 60)
    sudo_run(client,
        "sed -i 's/^bind-address.*=.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf && systemctl restart mysql",
        "Set bind-address=0.0.0.0 and restart MySQL")

    # ================================================================
    print("\n" + "=" * 60)
    print(" Step 4: Redis bind → 0.0.0.0")
    print("=" * 60)
    sudo_run(client,
        "sed -i 's/^bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf && systemctl restart redis-server",
        "Set Redis bind=0.0.0.0 and restart")

    # ================================================================
    print("\n" + "=" * 60)
    print(" Step 5: Create operator user")
    print("=" * 60)
    sudo_run(client,
        "id operator 2>/dev/null || (useradd -m -s /bin/bash operator && echo 'operator:0p3rat0r@GDJ' | chpasswd && usermod -aG sudo operator)",
        "Create operator user")
    sudo_run(client,
        """cat > /etc/sudoers.d/operator << 'EOF'
operator ALL=(ALL) NOPASSWD: /usr/bin/apt, /usr/bin/systemctl, /usr/sbin/service
EOF
chmod 440 /etc/sudoers.d/operator""",
        "Set operator sudoers")

    # ================================================================
    print("\n" + "=" * 60)
    print(" Step 6: Configure iptables")
    print("=" * 60)
    sudo_run(client, """cat > /etc/iptables/rules.v4 << 'EOF'
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
EOF""", "Write iptables rules")
    sudo_run(client, "iptables-restore < /etc/iptables/rules.v4",
        "Apply iptables rules")

    # Install iptables-persistent if possible, otherwise use rc.local fallback
    out, err, code = sudo_run(client,
        "apt install -y iptables-persistent 2>&1 || echo 'NET_UNAVAILABLE'",
        "Install iptables-persistent")
    if 'NET_UNAVAILABLE' in out or 'Unable to locate' in err:
        print("  [!] No internet - using rc.local fallback for iptables persistence")
        sudo_run(client, """cat > /etc/rc.local << 'EOF'
#!/bin/bash
iptables-restore < /etc/iptables/rules.v4
exit 0
EOF
chmod +x /etc/rc.local""", "Create rc.local for iptables persistence")

    # ================================================================
    print("\n" + "=" * 60)
    print(" Step 7: Confluence health check + cron (privesc vector)")
    print("=" * 60)
    sudo_run(client, """cat > /opt/confluence_health_check.sh << 'EOF'
#!/bin/bash
# Confluence health check — runs as root via cron
systemctl status confluence > /dev/null 2>&1 || systemctl restart confluence
EOF
chmod 777 /opt/confluence_health_check.sh""",
        "Create writable cron script (privesc vector)")
    sudo_run(client,
        'echo "*/10 * * * * root /opt/confluence_health_check.sh" > /etc/cron.d/confluence-health',
        "Add root cron job")

    # ================================================================
    print("\n" + "=" * 60)
    print(" Step 8: Confluence installation")
    print("=" * 60)
    # Check if Confluence already exists
    out, _, _ = sudo_run(client, "ls /opt/atlassian/confluence/bin/start-confluence.sh 2>&1")
    if 'No such file' in out:
        print("  [!] Confluence NOT installed — will attempt download...")
        # Try download
        out, err, code = sudo_run(client,
            "cd /tmp && wget -q --timeout=30 https://product-downloads.atlassian.com/software/confluence/downloads/atlassian-confluence-7.13.6.tar.gz 2>&1 && echo 'DOWNLOAD_OK' || echo 'DOWNLOAD_FAIL'",
            "Download Confluence 7.13.6")
        if 'DOWNLOAD_OK' in out:
            print("  [+] Download OK, extracting...")
            sudo_run(client, """mkdir -p /opt/atlassian/confluence
cd /tmp
tar xzf atlassian-confluence-7.13.6.tar.gz
mv atlassian-confluence-7.13.6/* /opt/atlassian/confluence/
rm -rf /tmp/atlassian-confluence-7.13.6*""",
                "Extract Confluence")
        else:
            print("  [!] Cannot download Confluence (no internet)")
            print("  [!] Manual step needed: download on host and SCP to VM")
            # Create placeholder + systemd service anyway
            sudo_run(client, "mkdir -p /opt/atlassian/confluence/bin")
            sudo_run(client, """cat > /etc/systemd/system/confluence.service << 'EOF'
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
EOF""", "Create Confluence systemd service")
            sudo_run(client, "useradd -m -s /bin/bash confluence 2>/dev/null || true",
                "Create confluence user")
            sudo_run(client, "mkdir -p /var/atlassian/confluence",
                "Create Confluence home dir")
    else:
        print("  [+] Confluence already installed")

    # ================================================================
    print("\n" + "=" * 60)
    print(" Step 9: Verify everything")
    print("=" * 60)

    checks = [
        ("MySQL root.cnf", "cat /etc/mysql/mysql.conf.d/root.cnf 2>&1 | head -5"),
        ("MySQL bind-address", "grep '^bind-address' /etc/mysql/mysql.conf.d/mysqld.cnf"),
        ("MySQL cmsuser", "mysql -u root -p'R00t@Mysql#2024' -e \"SELECT user,host FROM mysql.user WHERE user='cmsuser'\""),
        ("Redis bind", "grep '^bind' /etc/redis/redis.conf"),
        ("operator user", "id operator 2>&1"),
        ("iptables rules", "iptables -L INPUT -n 2>&1 | head -10"),
        ("cron job", "cat /etc/cron.d/confluence-health 2>&1"),
        ("health_check.sh", "ls -la /opt/confluence_health_check.sh 2>&1"),
    ]

    all_ok = True
    for name, cmd in checks:
        out, err, code = sudo_run(client, cmd, f"Check: {name}")
        if code != 0 and 'grep' not in cmd:  # grep returns 1 for no match
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print(" [+] VM-A2 setup COMPLETE (except Confluence download)")
    else:
        print(" [!] Some checks failed - review above")

    client.close()

if __name__ == '__main__':
    main()
