#!/usr/bin/env python
"""Verify CVE output after hostname change"""
import paramiko, sys, io

HOST = '192.168.120.20'
USER = 'gdadmin'
PASS = 'Gdadmin@123'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=15, look_for_keys=False, allow_agent=False)

def sudo(cmd):
    full = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = c.exec_command(full, timeout=15, get_pty=True)
    stdout.channel.settimeout(15); stderr.channel.settimeout(15)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("=== CVE output ===")
print(sudo("cat /dev/shm/pwned2.txt 2>&1 || echo 'NOT FOUND'"))
print(sudo("hostname"))
c.close()
