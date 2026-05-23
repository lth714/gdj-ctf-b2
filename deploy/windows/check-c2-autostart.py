#!/usr/bin/env python3
"""Check C2 service auto-start (systemctl is-enabled) status"""
import paramiko

host = '192.168.101.141'
user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(c, cmd, timeout=20):
    print(f">>> {cmd}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:500]}")
    if err.strip(): print(f"  [err] {err.strip()[:300]}")
    return out, err, ec

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected.\n")

print("=" * 60)
print("SERVICE AUTO-START STATUS (is-enabled)")
print("=" * 60)

for svc in ['apache2', 'slapd', 'smbd', 'nmbd', 'mysql', 'ssh', 'netfilter-persistent']:
    print(f"\n--- {svc} ---")
    run(c, f"systemctl is-enabled {svc} 2>&1 || echo 'NOT_ENABLED'")
    run(c, f"systemctl is-active {svc} 2>&1 || echo 'NOT_ACTIVE'")

# Check iptables rules file exists
print("\n" + "=" * 60)
print("IPTABLES PERSISTENCE")
print("=" * 60)
run(c, "ls -la /etc/iptables/rules.v4 2>&1")
run(c, "echo 'Gdadmin@123' | sudo -S head -3 /etc/iptables/rules.v4")

# Check netplan
print("\n" + "=" * 60)
print("NETPLAN (network auto-start)")
print("=" * 60)
run(c, "cat /etc/netplan/00-installer-config.yaml")

c.close()
print("\nDone!")
