#!/usr/bin/env python3
"""
修改VM网络配置：ens33=192.168.101.145, ens37=192.168.110.10
"""
import paramiko
import time

HOST = "192.168.101.130"
USER = "gdadmin"
PASS = "Gdadmin@123"
PORT = 22

def exec_cmd(client, cmd, timeout=30):
    """执行命令并返回输出"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    return exit_code, out, err

def main():
    # netplan配置内容
    netplan_config = """network:
  version: 2
  ethernets:
    ens33:
      dhcp4: false
      addresses:
        - 192.168.101.145/24
      gateway4: 192.168.101.1
      nameservers:
        addresses:
          - 8.8.8.8
    ens37:
      dhcp4: false
      addresses:
        - 192.168.110.10/24
      gateway4: 192.168.110.1
      nameservers:
        addresses:
          - 8.8.8.8
"""

    print(f"[+] 连接 {HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=10)
    print("[+] 连接成功")

    # 1. 写入netplan配置
    print("[+] 写入netplan配置...")
    cmd = f'echo """{netplan_config}""" > /tmp/netplan.yaml'
    exec_cmd(client, cmd)

    # 2. 复制到netplan目录
    print("[+] 应用网络配置...")
    exec_cmd(client, f'echo "{PASS}" | sudo -S cp /tmp/netplan.yaml /etc/netplan/00-installer-config.yaml')

    # 3. 应用netplan
    exec_cmd(client, f'echo "{PASS}" | sudo -S netplan apply')

    # 4. 验证
    print("[+] 验证网络配置...")
    exit_code, out, err = exec_cmd(client, "ip a")
    print(out)

    # 5. 检查ens37是否存在
    exit_code, out, err = exec_cmd(client, "ip a show ens37 2>&1 || ip link show ens37 2>&1")
    if "ens37" in out:
        print("[+] ens37 已存在")
    else:
        print("[!] ens37 不存在，可能需要启动或添加网卡")

    client.close()
    print("[*] 完成")

if __name__ == "__main__":
    main()
