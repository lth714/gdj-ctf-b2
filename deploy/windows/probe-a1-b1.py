#!/usr/bin/env python3
"""Probe A1 (192.168.100.1) and B1 (192.168.110.1) DMZ VMs"""
import paramiko

user = 'gdadmin'
pwd = 'Gdadmin@123'

hosts = {
    'A1': '192.168.100.1',
    'B1': '192.168.110.1',
}

for name, host in hosts.items():
    print(f"\n{'='*70}")
    print(f"PROBING {name} ({host}) - DMZ")
    print('='*70)
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(host, username=user, password=pwd, timeout=10)
        print("Connected.\n")

        def run(cmd, timeout=15):
            print(f">>> {cmd[:130]}")
            stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
            out = stdout.read().decode('utf-8', errors='replace')
            err = stderr.read().decode('utf-8', errors='replace')
            ec = stdout.channel.recv_exit_status()
            if out.strip(): print(f"  {out.strip()[:800]}")
            if err.strip() and ec != 0: print(f"  [err] {err.strip()[:200]}")
            return out, err, ec

        # OS
        print("--- OS ---")
        run("cat /etc/os-release | head -2")

        # Packages
        print("\n--- Key packages ---")
        run("dpkg -l | grep -E 'apache2|nginx|php|mysql|mariadb|python3-flask|gunicorn' | awk '{print $2}' | sort -u")

        # Services
        print("\n--- Services ---")
        for svc in ['apache2', 'nginx', 'mysql', 'mariadb', 'media-api', 'monitor-dashboard', 'ssh']:
            out, err, _ = run(f"systemctl is-active {svc} 2>&1 || echo 'N/A'")
            run(f"systemctl is-enabled {svc} 2>&1 || echo 'N/A'")

        # Web root
        print("\n--- Web root ---")
        run("ls /var/www/ 2>/dev/null || echo 'no /var/www'")
        run("ls /opt/monitor/ 2>/dev/null || echo 'no /opt/monitor'")
        run("ls /opt/ops/ 2>/dev/null || echo 'no /opt/ops'")

        # Web access
        print("\n--- Web check ---")
        run("curl -s -o /dev/null -w '%{http_code}' http://localhost/ 2>&1")
        run("curl -s http://localhost/ 2>&1 | grep -o '<title>[^<]*</title>'")
        run("curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/ 2>&1")

        # iptables
        print("\n--- iptables ---")
        run("echo 'Gdadmin@123' | sudo -S iptables -L INPUT -n 2>/dev/null | head -10")

        # /opt/deploy
        print("\n--- /opt/deploy ---")
        run("ls -la /opt/deploy/ 2>/dev/null || echo 'NOT_FOUND'")

        # Sudoers
        print("\n--- Sudoers ---")
        run("echo 'Gdadmin@123' | sudo -S cat /etc/sudoers.d/* 2>/dev/null | grep -v '^#' | grep -v '^$' | head -10")

        # Connectivity to internal
        print("\n--- Connectivity to Internal ---")
        if name == 'A1':
            run("ping -c 1 -W 2 192.168.100.2 2>&1 | grep -E 'from|loss'")
            run("curl -s -o /dev/null -w '%{http_code}' http://192.168.100.2:8090/ 2>&1")
        else:
            run("ping -c 1 -W 2 192.168.110.2 2>&1 | grep -E 'from|loss'")
            run("curl -s -o /dev/null -w '%{http_code}' http://192.168.110.2:8080/api/health 2>&1")
            run("curl -s -o /dev/null -w '%{http_code}' http://192.168.110.2:8081/ 2>&1")

        c.close()
    except Exception as e:
        print(f"  CONNECT FAILED: {e}")
