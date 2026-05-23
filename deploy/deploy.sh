#!/bin/bash
# ============================================
# CTF 主编排脚本
# 按正确顺序部署全部6台VM
# 用法: ./deploy.sh
# ============================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.env"

echo "============================================"
echo " GDJ CTF 环境部署编排"
echo "============================================"
echo ""
echo "部署顺序: Internal VM先部署 (数据库需就绪)"
echo "  Phase 1: A2 → C2 → B2 (Internal)"
echo "  Phase 2: A1 → C1 → B1 (DMZ)"
echo ""
echo "共计 6 台 VM"
echo "预计总耗时: 60-120 分钟 (取决于网络和磁盘IO)"
echo ""

# --- 阶段0: 网络检查 ---
echo "========================================"
echo " Phase 0: 网络基础设施"
echo "========================================"
echo ""

echo "[*] 检查bridge是否存在..."
MISSING_BR=0
for BR in "$BR_EXT" "$BR_A" "$BR_B" "$BR_C"; do
    if ip link show "$BR" &>/dev/null; then
        echo "  [✓] $BR 已存在"
    else
        echo "  [!] $BR 不存在 — 请先运行: sudo ./net-setup.sh"
        MISSING_BR=1
    fi
done

if [ "$MISSING_BR" -eq 1 ]; then
    echo ""
    echo "[!] 缺少bridge，请先运行 net-setup.sh 创建网络"
    exit 1
fi

# 给host添加内部bridge的IP (用于访问Internal VM)
echo ""
echo "[+] 配置host访问内部网络..."
ip addr add 192.168.100.254/24 dev "$BR_A" 2>/dev/null || true
ip addr add 192.168.110.254/24 dev "$BR_B" 2>/dev/null || true
ip addr add 192.168.120.254/24 dev "$BR_C" 2>/dev/null || true

echo ""
echo "[*] 预下载N-Day应用..."
bash "${SCRIPT_DIR}/download-apps.sh"

echo ""
echo "[*] VM创建命令预览:"
echo "   (请确保已完成Ubuntu 20.04 base VM的手动安装)"
echo ""
for VM in "${VM_ORDER[@]}"; do
    echo "  $ bash ${SCRIPT_DIR}/vm-create.sh $VM"
done

echo ""
read -rp ">>> VM是否已全部创建? (yes/no): " VMS_READY
if [ "$VMS_READY" != "yes" ]; then
    echo "请先使用 vm-create.sh 创建所有VM，然后重新运行本脚本"
    exit 0
fi

echo ""
echo "========================================"
echo " Phase 1: 部署 Internal VM"
echo " (Internal必须先部署 — DMZ需要数据库)"
echo "========================================"
echo ""

# Internal VM的静态IP (来自config.env)
echo "[*] Internal VM IP映射:"
echo "  VM-A2: ${VM_IPS[a2]}"
echo "  VM-C2: ${VM_IPS[c2]}"
echo "  VM-B2: ${VM_IPS[b2]}"

for VM in a2 c2 b2; do
    echo ""
    echo "----------------------------------------"
    echo " 部署 VM-${VM} (Internal)"
    echo "----------------------------------------"

    VM_IP=$(echo "${VM_IPS[$VM]}" | cut -d/ -f1)

    read -rp ">>> 部署 VM-${VM} (IP: ${VM_IP})? (yes/no/skip): " DO_DEPLOY
    case "$DO_DEPLOY" in
        yes)
            bash "${SCRIPT_DIR}/provision.sh" "$VM" "$VM_IP"
            ;;
        skip)
            echo "[*] 跳过 VM-${VM}"
            ;;
        *)
            echo "[!] 输入无效，跳过"
            ;;
    esac
done

echo ""
echo "========================================"
echo " Phase 2: 部署 DMZ VM"
echo " (DMZ在Internal就绪后部署)"
echo "========================================"
echo ""

# DMZ VM的Internal IP
echo "[*] DMZ VM Internal IP:"
echo "  VM-A1: ${VM_IPS[a1_int]}"
echo "  VM-C1: ${VM_IPS[c1_int]}"
echo "  VM-B1: ${VM_IPS[b1_int]}"

for VM in a1 c1 b1; do
    echo ""
    echo "----------------------------------------"
    echo " 部署 VM-${VM} (DMZ)"
    echo "----------------------------------------"

    VM_IP=$(echo "${VM_IPS[${VM}_int]}" | cut -d/ -f1)

    read -rp ">>> 部署 VM-${VM} (Internal IP: ${VM_IP})? (yes/no/skip): " DO_DEPLOY
    case "$DO_DEPLOY" in
        yes)
            bash "${SCRIPT_DIR}/provision.sh" "$VM" "$VM_IP"
            ;;
        skip)
            echo "[*] 跳过 VM-${VM}"
            ;;
        *)
            echo "[!] 输入无效，跳过"
            ;;
    esac
done

echo ""
echo "========================================"
echo " 部署完成!"
echo "========================================"
echo ""
echo "下一步:"
echo "  1. 验证网络:  ./verify.sh network"
echo "  2. 验证服务:  ./verify.sh services"
echo "  3. 验证攻击链: ./verify.sh chains"
