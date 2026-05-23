#!/usr/bin/env python3
"""Check C1 ens37 network configuration."""
import paramiko

c1 = paramiko.SSHClient()
c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c1.connect("192.168.101.140", username="gdadmin", password="Gdadmin@123", timeout=10)

stdin, stdout, stderr = c1.exec_command("hostname && echo '--- ens37 ---' && ip addr show ens37 2>&1 || echo 'ens37 not found' && echo '--- all interfaces ---' && ip addr show 2>&1 | grep -E '^[0-9]|inet ' && echo '--- netplan ---' && cat /etc/netplan/*.yaml 2>&1")
print(stdout.read().decode())
err = stderr.read().decode()
if err.strip():
    print("STDERR:", err)
c1.close()
