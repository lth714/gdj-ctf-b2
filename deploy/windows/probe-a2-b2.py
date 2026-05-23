#!/usr/bin/env python3
"""Quick probe A2 (192.168.100.2) and B2 (192.168.110.2) current state"""
import paramiko

hosts = {
    'A2': '192.168.100.2',
    'B2': '192.168.110.2',
}
user = 'gdadmin'
pwd = 'Gdadmin@123'

for name, host in hosts.items():
    print(f"\n{'='*60}")
    print(f"PROBING {name} ({host})")
    print('='*60)
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(host, username=user, password=pwd, timeout=10)
        print("Connected.\n")

        def run(cmd, timeout=15):
            stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
            out = stdout.read().decode('utf-8', errors='replace')
            err = stderr.read().decode('utf-8', errors='replace')
            ec = stdout.channel.recv_exit_status()
            if out.strip(): print(f"  {out.strip()[:600]}")
            if err.strip() and ec != 0: print(f"  [err] {err.strip()[:200]}")
            return out, err, ec

        # OS version
        print("--- OS ---")
        run("cat /etc/os-release | head -3")

        # Package install status
        print("\n--- Key packages ---")
        run("dpkg -l | grep -E 'mysql-server|postgresql|redis|confluence|jenkins|apache2|nginx' | awk '{print $2, $3}' | head -10")

        # Service status
        print("\n--- Services ---")
        for svc in ['mysql', 'redis-server', 'confluence', 'postgresql', 'api-gateway', 'jenkins', 'apache2', 'nginx']:
            run(f"systemctl is-active {svc} 2>&1 || echo 'N/A'", timeout=5)

        # Check if setup.sh was already run
        print("\n--- Setup traces ---")
        run("ls /opt/deploy/ 2>/dev/null || echo 'no /opt/deploy'")
        run("ls /var/www/ 2>/dev/null || echo 'no /var/www'")

        # Check current iptables
        print("\n--- iptables ---")
        run("echo 'Gdadmin@123' | sudo -S iptables -L INPUT -n 2>/dev/null | head -8", timeout=10)

        # Check netplan
        print("\n--- Netplan ---")
        run("cat /etc/netplan/00-installer-config.yaml 2>/dev/null")

        c.close()
    except Exception as e:
        print(f"  CONNECT FAILED: {e}")
