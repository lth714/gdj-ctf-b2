#!/usr/bin/env python3
"""Clean up A1 deployment from wrong host (192.168.101.137).
   KEEP MySQL intact! Only remove nginx, php, cms files, sudoers."""
import paramiko

HOST = '192.168.101.137'
USER = 'gdadmin'
PASS = 'Gdadmin@123'

def sudo(client, cmd, timeout=30):
    full = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = client.exec_command(full, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS,
                   timeout=15, look_for_keys=False, allow_agent=False)
    print(f"[OK] Connected to {HOST}")

    # 1. Stop and disable services
    print("\n--- 1. Stopping nginx + php-fpm ---")
    for svc in ['nginx', 'php7.4-fpm']:
        out, err, code = sudo(client, f'systemctl stop {svc} 2>/dev/null; systemctl disable {svc} 2>/dev/null; echo "stopped {svc}"')
        print(f"  {out}")

    # 2. Remove CMS files
    print("\n--- 2. Removing CMS files ---")
    out, err, code = sudo(client, 'rm -rf /var/www/html/baixiu && echo "removed" || echo "not found"')
    print(f"  /var/www/html/baixiu: {out}")

    # 3. Restore nginx default config (basic placeholder)
    print("\n--- 3. Restoring nginx default config ---")
    sudo(client, '''cat > /etc/nginx/sites-available/default << 'NGXEOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    root /var/www/html;
    index index.html index.htm index.nginx-debian.html;
    server_name _;
    location / {
        try_files $uri $uri/ =404;
    }
}
NGXEOF
echo "nginx config restored"''')
    print("  nginx config restored")

    # 4. Remove sudoers for www-data
    print("\n--- 4. Removing /etc/sudoers.d/www-data ---")
    out, err, code = sudo(client, 'rm -f /etc/sudoers.d/www-data && echo "removed" || echo "not found"')
    print(f"  sudoers: {out}")

    # 5. Uninstall nginx + PHP packages (keep mysql-server!)
    print("\n--- 5. Removing nginx + PHP packages (keeping mysql-server) ---")
    pkgs = 'nginx nginx-common nginx-full php7.4 php7.4-fpm php7.4-mysql php7.4-mbstring php7.4-xml php7.4-curl php7.4-gd php7.4-zip'
    out, err, code = sudo(client, f'DEBIAN_FRONTEND=noninteractive apt remove -y {pkgs} 2>&1 | tail -8', timeout=120)
    print(f"  apt remove result:\n{out}")
    if err:
        print(f"  stderr: {err[:200]}")

    # 6. Clean temp files
    print("\n--- 6. Clean temp ---")
    out, _, _ = sudo(client, 'rm -rf /tmp/deploy && echo "cleaned"')
    print(f"  {out}")

    # 7. Final verification
    print("\n=== Verification ===")
    checks = [
        ("MySQL status", "systemctl is-active mysql 2>&1 || systemctl is-active mysqld 2>&1"),
        ("Nginx status", "systemctl is-active nginx 2>&1 || echo 'not running'"),
        ("PHP-FPM status", "systemctl is-active php7.4-fpm 2>&1 || echo 'not running'"),
        ("Web root contents", "ls /var/www/html/ 2>&1"),
        ("Nginx packages left", "dpkg -l | grep -E '^ii.*nginx' | wc -l"),
        ("PHP packages left", "dpkg -l | grep -E '^ii.*php7.4' | wc -l"),
        ("sudoers.d contents", "ls /etc/sudoers.d/ 2>&1"),
    ]
    for name, cmd in checks:
        out, _, _ = sudo(client, cmd)
        print(f"  {name}: {out}")

    client.close()
    print("\n=== CLEANUP COMPLETE ===")

if __name__ == '__main__':
    main()
