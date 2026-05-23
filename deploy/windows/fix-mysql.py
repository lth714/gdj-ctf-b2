#!/usr/bin/env python3
"""SSH into VM-A2 and fix MySQL root password, then complete setup."""
import paramiko
import sys
import time

HOST = '192.168.100.2'
USER = 'gdadmin'
PASS = 'Gdadmin@123'

def run(client, cmd, sudo=False):
    """Execute command and return (stdout, stderr, exit_code)."""
    if sudo:
        cmd = f'echo "{PASS}" | sudo -S bash -c \'{cmd}\''
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    code = stdout.channel.recv_exit_status()
    return out.strip(), err.strip(), code

def main():
    print(f"[*] Connecting to {HOST} as {USER}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(HOST, username=USER, password=PASS,
                       timeout=15, look_for_keys=False, allow_agent=False)
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        sys.exit(1)

    print("[+] Connected!\n")

    # ===============================================
    # Phase 1: Force-reset MySQL root password
    # ===============================================
    print("=" * 60)
    print(" Phase 1: MySQL root 密码重置")
    print("=" * 60)

    print("\n[1/6] 停止 MySQL...")
    out, err, code = run(client, 'systemctl stop mysql', sudo=True)
    print(f"  stdout: {out}")
    print(f"  stderr: {err}")
    print(f"  exit={code}")

    print("\n[2/6] 写入 skip-grant-tables 配置...")
    cfg = '[mysqld]\nskip-grant-tables\nskip-networking\n'
    out, err, code = run(client, f"printf '%s' '{cfg}' > /etc/mysql/conf.d/skip-grant-tables.cnf", sudo=True)
    print(f"  stdout: {out}")
    print(f"  stderr: {err}")
    print(f"  exit={code}")

    # Verify config file was written
    out, err, code = run(client, 'cat /etc/mysql/conf.d/skip-grant-tables.cnf', sudo=True)
    print(f"  Config content: {out}")

    print("\n[3/6] 启动 MySQL (无权限验证)...")
    out, err, code = run(client, 'systemctl start mysql', sudo=True)
    print(f"  stdout: {out}")
    print(f"  stderr: {err}")
    print(f"  exit={code}")

    time.sleep(2)

    # Check if MySQL is running
    out, err, code = run(client, 'systemctl is-active mysql', sudo=True)
    print(f"  MySQL status: {out}")

    print("\n[4/6] 重置 root 密码...")
    sql = """FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'R00t@Mysql#2024';
FLUSH PRIVILEGES;"""
    out, err, code = run(client, f"mysql -u root -e \"{sql}\"", sudo=True)
    print(f"  stdout: {out}")
    print(f"  stderr: {err}")
    print(f"  exit={code}")

    print("\n[5/6] 删除 skip-grant-tables 配置...")
    out, err, code = run(client, 'rm -f /etc/mysql/conf.d/skip-grant-tables.cnf', sudo=True)
    print(f"  stdout: {out}")
    print(f"  stderr: {err}")
    print(f"  exit={code}")

    print("\n[6/6] 重启 MySQL (正常模式)...")
    out, err, code = run(client, 'systemctl restart mysql', sudo=True)
    print(f"  stdout: {out}")
    print(f"  stderr: {err}")
    print(f"  exit={code}")

    time.sleep(2)

    # ===============================================
    # Phase 2: Verify
    # ===============================================
    print("\n" + "=" * 60)
    print(" Phase 2: 验证")
    print("=" * 60)

    out, err, code = run(client, "mysql -u root -p'R00t@Mysql#2024' -e 'SELECT 1 AS test_ok; SHOW DATABASES;'")
    print(f"\n[验证] 新密码登录测试:")
    print(f"  stdout:\n{out}")
    print(f"  stderr: {err}")
    print(f"  exit={code}")

    if code == 0 and 'test_ok' in out:
        print("\n[+] MySQL root 密码重置成功!")
    else:
        print("\n[-] MySQL 密码重置可能失败，需要进一步排查")

    # ===============================================
    # Phase 3: Check remaining setup
    # ===============================================
    print("\n" + "=" * 60)
    print(" Phase 3: 检查 setup.sh 剩余步骤")
    print("=" * 60)

    # Check if MySQL has 'cms' database already
    out, err, code = run(client, "mysql -u root -p'R00t@Mysql#2024' -e 'SHOW DATABASES;'")
    print(f"\n[数据库] 现有数据库:\n{out}")

    # Check if init_db.sql exists
    out, err, code = run(client, 'ls -la /opt/deploy/init_db.sql 2>&1')
    print(f"\n[部署文件] /opt/deploy/init_db.sql:\n{out}")

    # Check Confluence setup
    out, err, code = run(client, 'ls -la /opt/confluence/ 2>&1')
    print(f"\n[Confluence] /opt/confluence/:\n{out}")

    # Check operator user
    out, err, code = run(client, 'id operator 2>&1')
    print(f"\n[用户] operator:\n{out}")

    # Check iptables rules
    out, err, code = run(client, 'iptables -L -n 2>&1', sudo=True)
    print(f"\n[iptables] 当前规则:\n{out[:500]}")

    # Check Redis
    out, err, code = run(client, 'systemctl is-active redis-server 2>&1')
    print(f"\n[Redis] 状态: {out}")

    # Check bind-address
    out, err, code = run(client, 'grep bind-address /etc/mysql/mysql.conf.d/mysqld.cnf 2>&1')
    print(f"\n[MySQL] bind-address:\n{out}")

    client.close()
    print("\n[*] 脚本执行完毕")

if __name__ == '__main__':
    main()
