#!/bin/bash
# ============================================
# 网络桥接设置脚本
# 创建4个Linux bridge用于CTF VM之间及外部网络通信
# ============================================
set -e

source "$(dirname "$0")/config.env"

echo "[+] 创建CTF网络桥接..."
echo ""

# 检测物理网卡
PHYSICAL_NIC=$(ip route | grep default | awk '{print $5}' 2>/dev/null || echo "eth0")
echo "[*] 物理网卡: $PHYSICAL_NIC"

# --- 创建 br0 (外部网络，桥接物理网卡) ---
echo "[+] 创建 $BR_EXT (外部网络)..."
if ! ip link show "$BR_EXT" &>/dev/null; then
    ip link add name "$BR_EXT" type bridge
    ip link set "$PHYSICAL_NIC" master "$BR_EXT" 2>/dev/null || {
        echo "[!] 无法将 $PHYSICAL_NIC 加入 $BR_EXT"
        echo "    如果使用NetworkManager，请手动配置bridge。"
    }
    ip link set "$BR_EXT" up
    echo "  -> $BR_EXT 已创建"
else
    echo "  -> $BR_EXT 已存在"
fi

# --- 创建隔离网桥 (场景内网，无物理接口) ---
for BR in "$BR_A" "$BR_B" "$BR_C"; do
    echo "[+] 创建 $BR (隔离内网)..."
    if ! ip link show "$BR" &>/dev/null; then
        ip link add name "$BR" type bridge
        ip link set "$BR" up
        echo "  -> $BR 已创建"
    else
        echo "  -> $BR 已存在"
    fi
done

# --- 给Host添加内网IP (用于访问Internal VM) ---
echo "[+] 配置Host内网IP..."
ip addr add 192.168.100.254/24 dev "$BR_A" 2>/dev/null || true
ip addr add 192.168.110.254/24 dev "$BR_B" 2>/dev/null || true
ip addr add 192.168.120.254/24 dev "$BR_C" 2>/dev/null || true

# --- 防止主机iptables干扰bridge流量 ---
echo "[+] 设置 bridge sysctl..."
sysctl -w net.bridge.bridge-nf-call-iptables=0 >/dev/null
sysctl -w net.bridge.bridge-nf-call-ip6tables=0 >/dev/null

# 持久化
cat > /etc/sysctl.d/99-ctf-bridge.conf << 'EOF'
net.bridge.bridge-nf-call-iptables=0
net.bridge.bridge-nf-call-ip6tables=0
EOF

echo ""
echo "[+] 网桥状态:"
bridge link show
echo ""
echo "[✓] 网络桥接设置完成。"
