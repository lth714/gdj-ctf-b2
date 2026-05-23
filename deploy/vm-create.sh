#!/bin/bash
# ============================================
# VM创建脚本
# 用法: ./vm-create.sh <vm-id>
# 示例: ./vm-create.sh a1
# ============================================
set -e

source "$(dirname "$0")/config.env"

VM_ID="$1"
if [ -z "$VM_ID" ]; then
    echo "用法: $0 <vm-id>  (a1|a2|b1|b2|c1|c2)"
    exit 1
fi

VM_NAME="ctfd-${VM_ID}"
VM_DISK_PATH="${WORK_DIR}/${VM_NAME}.qcow2"

# 判断VM类型
case "$VM_ID" in
    a1|b1|c1)
        VM_TYPE="dmz"
        VM_RAM=$VM_RAM_DMZ
        VM_VCPU=$VM_VCPU_DMZ
        ;;
    a2|b2|c2)
        VM_TYPE="internal"
        VM_RAM=$VM_RAM_INTERNAL
        VM_VCPU=$VM_VCPU_INTERNAL
        ;;
    *)
        echo "无效的VM ID: $VM_ID"
        exit 1
        ;;
esac

echo "[+] 创建VM: $VM_NAME ($VM_TYPE)"
echo "    RAM: ${VM_RAM}MB, vCPU: $VM_VCPU, Disk: $VM_DISK"

mkdir -p "$WORK_DIR"

# --- 创建磁盘 ---
if [ ! -f "$VM_DISK_PATH" ]; then
    echo "[+] 创建qcow2磁盘..."
    qemu-img create -f qcow2 "$VM_DISK_PATH" "$VM_DISK"
else
    echo "[*] 磁盘已存在: $VM_DISK_PATH"
fi

# --- 构建virt-install参数 ---
# 注意: 此脚本假设已手动安装一台Ubuntu 20.04 base VM作为模板
# 实际部署时，先手动安装1台base VM，然后clone磁盘，再通过cloud-init注入网络

NETWORK_ARGS=""
SCENARIO_LETTER=$(echo "$VM_ID" | sed 's/[0-9]//')

if [ "$VM_TYPE" = "dmz" ]; then
    # DMZ VM: 双网卡 (外部 + 内网)
    NETWORK_ARGS="--network bridge=${BR_EXT},model=virtio"
    case "$SCENARIO_LETTER" in
        a) NETWORK_ARGS="$NETWORK_ARGS --network bridge=${BR_A},model=virtio" ;;
        b) NETWORK_ARGS="$NETWORK_ARGS --network bridge=${BR_B},model=virtio" ;;
        c) NETWORK_ARGS="$NETWORK_ARGS --network bridge=${BR_C},model=virtio" ;;
    esac
else
    # Internal VM: 单网卡 (仅内网)
    case "$SCENARIO_LETTER" in
        a) NETWORK_ARGS="--network bridge=${BR_A},model=virtio" ;;
        b) NETWORK_ARGS="--network bridge=${BR_B},model=virtio" ;;
        c) NETWORK_ARGS="--network bridge=${BR_C},model=virtio" ;;
    esac
fi

echo ""
echo "[+] 运行以下命令创建VM (需要手动执行):"
echo ""
echo "virt-install \\"
echo "  --name $VM_NAME \\"
echo "  --ram $VM_RAM \\"
echo "  --vcpus $VM_VCPU \\"
echo "  --disk path=$VM_DISK_PATH,format=qcow2,bus=virtio \\"
echo "  --os-variant ubuntu20.04 \\"
echo "  --cdrom $ISO_PATH \\"
echo "  $NETWORK_ARGS \\"
echo "  --graphics vnc,listen=0.0.0.0 \\"
echo "  --noautoconsole"

echo ""
echo "[*] VM创建后，使用以下命令查看IP:"
echo "    virsh domifaddr $VM_NAME"
echo "    (或查看VNC控制台)"
