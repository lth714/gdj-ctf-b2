# Windows QEMU 部署指南

## 环境

- QEMU 9.0.50: `D:\environment\qemu\`
- Ubuntu 20.04 ISO: `F:\qax\2026\广东广电局出题\ubuntu-20.04.6-live-server-amd64.iso`
- Hyper-V 已启用 → 使用 WHPX 加速 (不需要 KVM)

## 网络方案

QEMU on Windows 三种网络模式:

| 模式 | 互联网 | 宿主机↔VM | VM↔VM | 复杂度 |
|------|--------|-----------|-------|--------|
| user (SLIRP) | Y | 仅端口转发 | N | 低 |
| tap (OpenVPN) | Y | Y (同网段) | Y | 中 |
| tap (多网桥) | Y | Y | Y (隔离) | 高 |

**推荐方案**: 安装1个 OpenVPN TAP 适配器，桥接物理网卡，所有 VM 共享该网桥。
- DMZ VM: eth0 DHCP 获取外网IP
- Internal VM: eth0 静态内网IP
- 场景隔离 → VM 内部 iptables 规则实现
- 宿主机与 VM 在同一局域网，可直接 SSH/SCP

## 第一步: 安装 TAP 网络

### 1.1 安装 OpenVPN TAP 适配器

```powershell
# 下载 OpenVPN (TAP 驱动在安装包里)
# https://openvpn.net/community-downloads/
# 安装时只选 "TAP Virtual Ethernet Adapter" 组件
```

安装后在"网络连接"面板看到 `TAP-Windows Adapter V9`。

### 1.2 桥接 TAP 与物理网卡

```
控制面板 → 网络和共享中心 → 更改适配器设置
1. 选中 物理网卡 + TAP-Windows Adapter
2. 右键 → 桥接
3. 桥接后出现 "网络桥" (Network Bridge)
```

验证:
```bash
ipconfig
# 应看到 "网络桥" 获得了物理网段的 IP
```

### 1.3 测试桥接

```bash
# 创建测试磁盘
"D:/environment/qemu/qemu-img.exe" create -f qcow2 test.qcow2 5G

# 启动VM (带WHPX加速 + TAP网络)
"D:/environment/qemu/qemu-system-x86_64.exe" \
  -accel whpx \
  -m 2048 \
  -smp 2 \
  -drive file=test.qcow2,format=qcow2,if=virtio \
  -cdrom "F:/qax/2026/广东广电局出题/ubuntu-20.04.6-live-server-amd64.iso" \
  -nic tap,ifname="TAP-Windows Adapter V9",model=virtio \
  -display gtk
```

VM 应从物理网络 DHCP 获取 IP，能上网，宿主机也能 ping 通 VM。

## 第二步: 创建基础 VM

运行 `create-base.bat` 创建6个磁盘:

```
create-base.bat
```

这会创建:
- E:\vibecoding\gdj_ctf\vms\ctfd-a1.qcow2 (15G)
- E:\vibecoding\gdj_ctf\vms\ctfd-a2.qcow2 (15G)
- ... 共6个

## 第三步: 安装 Ubuntu (手动)

逐个启动 VM 安装系统:

```
launch-installer.bat a1
```

Ubuntu 安装关键步骤:
1. 语言: English
2. 网络: 自动 DHCP (会从桥接网络获取IP)
3. **不要**配置 LVM (选整个磁盘直接装)
4. 安装 OpenSSH server: **选上** (光标移到 Install OpenSSH server → 空格勾选)
5. 用户名/密码: 都设一样方便管理，如 `ctfadmin` / `Ctf@2024#Setup`

安装完成后 VM 自动重启，记下 IP。

## 第四步: 网络配置 (安装后)

每个 VM 安装完成后，需要配置第二网络 (内网IP):

### DMZ VM (a1, b1, c1)

```bash
# SSH 进入 VM
ssh ctfadmin@<VM_IP>

# 配置内网IP (第二个地址附加到 eth0，因为只有单网卡)
sudo bash -c 'cat >> /etc/netplan/00-installer-config.yaml << EOF
      addresses:
      - <DMZ_IP>/24
EOF'
sudo netplan apply
```

DMZ IP对照:
- a1: 192.168.100.1/24
- b1: 192.168.110.1/24
- c1: 192.168.120.1/24

### Internal VM (a2, b2, c2)

```bash
# 直接设静态IP (不需要DHCP)
sudo bash -c 'cat > /etc/netplan/00-installer-config.yaml << EOF
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses:
      - <INTERNAL_IP>/24
      routes:
      - to: default
        via: <GATEWAY>  # 宿主机IP或路由器IP
EOF'
sudo netplan apply
```

Internal IP对照:
- a2: 192.168.100.2/24
- b2: 192.168.110.2/24
- c2: 192.168.120.2/24

## 第五步: 部署应用

Linux deploy 脚本可以手动执行:

```bash
# 在宿主机上 (Git Bash 或 WSL)
# 1. 传输文件到 VM
scp -r scenario-a/vm-a1-dmz/scripts/ ctfadmin@<VM_IP>:/opt/deploy/scripts/
scp -r scenario-a/vm-a1-dmz/files/ ctfadmin@<VM_IP>:/opt/deploy/files/

# 2. SSH 执行安装
ssh ctfadmin@<VM_IP>
sudo bash /opt/deploy/scripts/setup.sh
```

## 加速选项

### WHPX (Hyper-V 已启用时)

QEMU 启动参数加: `-accel whpx`

### HAXM (如果禁用 Hyper-V)

```powershell
# 以管理员运行，禁用 Hyper-V
bcdedit /set hypervisorlaunchtype off
# 重启后可用 Intel HAXM 加速
```

QEMU 启动参数加: `-accel hax`
