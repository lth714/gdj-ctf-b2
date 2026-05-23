#!/usr/bin/env python3
"""Check B2 API gateway source for CTF secrets"""
import paramiko

host = '192.168.110.2'
user = 'gdadmin'
pwd = 'Gdadmin@123'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print("Connected to B2.\n")

def run(cmd, timeout=15):
    print(f">>> {cmd[:120]}")
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip(): print(f"  {out.strip()[:1500]}")
    if err.strip() and ec != 0: print(f"  [err] {err.strip()[:300]}")
    return out, err, ec

# Read the full main.go
print("="*60)
print("API GATEWAY main.go (full)")
print("="*60)
run("cat /opt/api-gateway/main.go")

# Check go.mod
print("\n" + "="*60)
print("go.mod")
print("="*60)
run("cat /opt/api-gateway/go.mod")

# Check API gateway environment (from systemd)
print("\n" + "="*60)
print("API Gateway env vars (from systemd)")
print("="*60)
run("cat /etc/systemd/system/api-gateway.service")

# Check if there are other config files
print("\n" + "="*60)
print("Other files in /opt/api-gateway/")
print("="*60)
run("ls -la /opt/api-gateway/")

# Test API gateway endpoints
print("\n" + "="*60)
print("API Gateway endpoints")
print("="*60)
run("curl -s http://localhost:8080/api/admin/token 2>&1")
run("curl -s http://localhost:8080/api/status 2>&1")
run("curl -s http://localhost:8080/api/ 2>&1")

c.close()
print("\nDone!")
