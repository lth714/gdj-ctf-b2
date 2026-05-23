#!/usr/bin/env python3
"""Fix B1 network and probe A1 through A2"""
import paramiko

user = 'gdadmin'
pwd = 'Gdadmin@123'

def run(c, cmd, sudo=False, timeout=15):
    if sudo:
        cmd = f"echo 'Gdadmin@123' | sudo -S bash -c '{cmd}'"
    print(f">>> {cmd[:130]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:800]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:200]}")
    return out, err, ec

# ============================================================
# B1: Check network
# ============================================================
print("="*70)
print("B1 NETWORK DIAGNOSTICS (192.168.110.1)")
print("="*70)
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.110.1', username=user, password=pwd, timeout=10)

# netplan
print("--- Netplan ---")
run(c, "cat /etc/netplan/00-installer-config.yaml")

# interfaces
print("\n--- Interfaces ---")
run(c, "ip addr show | grep -E '^[0-9]|inet '")

# routes
print("\n--- Routes ---")
run(c, "ip route")

# Check if there's a second NIC for internal
print("\n--- All NICs ---")
run(c, "ls /sys/class/net/")

# Try to reach B2 from B1 directly
print("\n--- Reach B2 ---")
run(c, "ip neigh")

c.close()

# ============================================================
# A1: Try via A2 as jump host
# ============================================================
print("\n" + "="*70)
print("A1 via A2 JUMP HOST")
print("="*70)
c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c2.connect('192.168.100.2', username=user, password=pwd, timeout=10)

# Check A2's interfaces
print("--- A2 interfaces ---")
run(c2, "ip addr show | grep -E '^[0-9]|inet '")

# Try to reach A1 from A2
print("\n--- Reach A1 from A2 ---")
run(c2, "ping -c 2 -W 2 192.168.100.1 2>&1 | grep -E 'from|loss|ttl'")
run(c2, "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 gdadmin@192.168.100.1 'hostname' 2>&1", timeout=15)

# Check SSH on A1 through A2
print("\n--- Check A1 SSH port from A2 ---")
run(c2, "nc -zv -w 3 192.168.100.1 22 2>&1")

# Check arp
print("\n--- ARP table on A2 ---")
run(c2, "arp -a 2>/dev/null | head -10")
run(c2, "ip neigh | head -10")

c2.close()
