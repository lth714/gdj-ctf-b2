#!/bin/bash
# ============================================
# VM 部署脚本 — 传输文件并执行setup.sh
# 用法: ./provision.sh <vm-id> <vm-ip>
# 示例: ./provision.sh a2 192.168.100.2
# ============================================
set -e

source "$(dirname "$0")/config.env"

VM_ID="$1"
VM_IP="$2"

if [ -z "$VM_ID" ] || [ -z "$VM_IP" ]; then
    echo "用法: $0 <vm-id> <vm-ip>"
    echo "示例: $0 a2 192.168.100.2"
    echo ""
    echo "VM ID映射:"
    echo "  a1=场景A DMZ,  a2=场景A Internal"
    echo "  b1=场景B DMZ,  b2=场景B Internal"
    echo "  c1=场景C DMZ,  c2=场景C Internal"
    exit 1
fi

# 确定场景和目录
SCENARIO_LETTER=$(echo "$VM_ID" | sed 's/[0-9]//')
VM_NUM=$(echo "$VM_ID" | sed 's/[a-c]//')

case "$SCENARIO_LETTER" in
    a) SCENARIO="scenario-a";;
    b) SCENARIO="scenario-b";;
    c) SCENARIO="scenario-c";;
    *) echo "无效的VM ID: $VM_ID"; exit 1;;
esac

case "$VM_NUM" in
    1) VM_TYPE="dmz";;
    2) VM_TYPE="internal";;
    *) echo "无效的VM ID: $VM_ID"; exit 1;;
esac

VM_DIR="${PROJECT_DIR}/${SCENARIO}/vm-${VM_ID}-${VM_TYPE}"
if [ ! -d "$VM_DIR" ]; then
    echo "[!] VM目录不存在: $VM_DIR"
    exit 1
fi

echo "============================================"
echo " 部署 VM-${VM_ID} (${VM_TYPE})"
echo " 目标IP: $VM_IP"
echo " 源目录: $VM_DIR"
echo "============================================"
echo ""

# --- SSH连接测试 ---
echo "[+] 测试SSH连接..."
if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@"$VM_IP" "echo SSH_OK" 2>/dev/null; then
    echo "[!] 无法SSH连接到 $VM_IP"
    echo "    请确保:"
    echo "    1. VM已安装Ubuntu 20.04并配置了网络"
    echo "    2. root SSH登录已启用"
    echo "    3. 主机能路由到VM (检查bridge配置)"
    exit 1
fi
echo "  -> SSH连接成功"

# --- 创建部署目录 ---
echo "[+] 在VM上创建部署目录..."
ssh root@"$VM_IP" "mkdir -p /opt/deploy/scripts /opt/deploy/files"

# --- 传输setup.sh ---
echo "[+] 传输 setup.sh..."
scp "${VM_DIR}/scripts/setup.sh" "root@${VM_IP}:/opt/deploy/scripts/"
ssh root@"$VM_IP" "chmod +x /opt/deploy/scripts/setup.sh"

# --- 传输files/目录 (如果存在) ---
if [ -d "${VM_DIR}/files" ] && [ "$(ls -A "${VM_DIR}/files" 2>/dev/null)" ]; then
    echo "[+] 传输场景文件 (files/)..."
    # 排除大型预下载文件，单独传输
    rsync -av --progress \
        --exclude='confluence.tar.gz' \
        --exclude='jenkins.war' \
        --exclude='drupal.tar.gz' \
        "${VM_DIR}/files/" "root@${VM_IP}:/opt/deploy/files/" 2>/dev/null || \
        scp -r "${VM_DIR}/files/"* "root@${VM_IP}:/opt/deploy/files/"
else
    echo "[*] 无场景文件需要传输"
fi

# --- 传输init_db.sql (如果存在) ---
if [ -f "${VM_DIR}/init_db.sql" ]; then
    echo "[+] 传输 init_db.sql..."
    scp "${VM_DIR}/init_db.sql" "root@${VM_IP}:/opt/deploy/"
fi

# --- 传输预下载的N-Day应用 ---
# 下载脚本已将这些文件放到对应场景的files/目录
case "$VM_ID" in
    a2)
        if [ -f "${PROJECT_DIR}/scenario-a/vm-a2-internal/files/confluence.tar.gz" ]; then
            echo "[+] 传输 Confluence (~800MB)..."
            scp "${PROJECT_DIR}/scenario-a/vm-a2-internal/files/confluence.tar.gz" \
                "root@${VM_IP}:/opt/deploy/files/"
        fi
        ;;
    b2)
        if [ -f "${PROJECT_DIR}/scenario-b/vm-b2-internal/files/jenkins.war" ]; then
            echo "[+] 传输 Jenkins (~70MB)..."
            scp "${PROJECT_DIR}/scenario-b/vm-b2-internal/files/jenkins.war" \
                "root@${VM_IP}:/opt/deploy/files/"
        fi
        ;;
    c2)
        if [ -f "${PROJECT_DIR}/scenario-c/vm-c2-internal/files/drupal.tar.gz" ]; then
            echo "[+] 传输 Drupal (~12MB)..."
            scp "${PROJECT_DIR}/scenario-c/vm-c2-internal/files/drupal.tar.gz" \
                "root@${VM_IP}:/opt/deploy/files/"
        fi
        ;;
esac

# --- 执行setup.sh ---
echo ""
echo "[+] 执行 setup.sh (这可能需要10-30分钟)..."
echo "    VM端输出将保存到 /opt/deploy/setup.log"
echo ""
ssh root@"$VM_IP" "bash /opt/deploy/scripts/setup.sh 2>&1 | tee /opt/deploy/setup.log"

echo ""
echo "[✓] VM-${VM_ID} 部署完成!"
echo "    日志: root@${VM_IP}:/opt/deploy/setup.log"
