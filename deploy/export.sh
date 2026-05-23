#!/bin/bash
# ============================================
# CTF VM 导出脚本
# 关闭VM → 压缩qcow2镜像 → 计算SHA256
# 用法: ./export.sh [--dir <导出目录>]
# ============================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.env"

EXPORT_DEST="${1:-$EXPORT_DIR}"
if [ -z "$EXPORT_DEST" ] || [ "$EXPORT_DEST" = "--dir" ]; then
    EXPORT_DEST="$2"
fi
EXPORT_DEST="${EXPORT_DEST:-/export/ctf-vms}"

ALL_VMS=("a1" "a2" "b1" "b2" "c1" "c2")

echo "============================================"
echo " CTF VM 导出"
echo " 目标目录: $EXPORT_DEST"
echo "============================================"
echo ""

mkdir -p "$EXPORT_DEST"

# --- 优雅关闭所有VM ---
echo "[+] 关闭所有CTF VM..."
for VM_ID in "${ALL_VMS[@]}"; do
    VM_NAME="ctfd-${VM_ID}"
    if virsh list --name | grep -q "^${VM_NAME}$" 2>/dev/null; then
        echo "  -> 关闭 $VM_NAME..."
        virsh shutdown "$VM_NAME" 2>/dev/null || {
            echo "     shutdown失败，尝试destroy..."
            virsh destroy "$VM_NAME" 2>/dev/null || true
        }
    else
        echo "  -> $VM_NAME 未运行"
    fi
done

# 等待VM关闭
echo "[*] 等待VM关闭(最多60秒)..."
for i in $(seq 1 12); do
    RUNNING=$(virsh list --name | grep -c "ctfd-" 2>/dev/null || echo 0)
    if [ "$RUNNING" -eq 0 ]; then
        echo "  -> 所有VM已关闭"
        break
    fi
    sleep 5
done

# --- 压缩并导出qcow2 ---
echo ""
echo "[+] 导出qcow2镜像..."

SHA256_FILE="${EXPORT_DEST}/SHA256SUMS"
:> "$SHA256_FILE"

for VM_ID in "${ALL_VMS[@]}"; do
    VM_NAME="ctfd-${VM_ID}"
    SRC_DISK="${WORK_DIR}/${VM_NAME}.qcow2"
    DST_DISK="${EXPORT_DEST}/${VM_NAME}.qcow2"

    if [ ! -f "$SRC_DISK" ]; then
        echo "  [!] 源磁盘不存在: $SRC_DISK"
        continue
    fi

    echo "  -> 导出 $VM_NAME..."
    echo "     源大小: $(du -h "$SRC_DISK" | cut -f1)"

    # 压缩转换 (sparse + compress)
    qemu-img convert -c -O qcow2 "$SRC_DISK" "$DST_DISK"

    DST_SIZE=$(du -h "$DST_DISK" | cut -f1)
    echo "     导出大小: $DST_SIZE"

    # SHA256
    sha256sum "$DST_DISK" >> "$SHA256_FILE"
    echo "     SHA256: $(sha256sum "$DST_DISK" | cut -d' ' -f1)"
done

# --- 导出元数据 ---
echo ""
echo "[+] 创建导出清单..."

cat > "${EXPORT_DEST}/manifest.json" << MANIFEST
{
  "export_date": "$(date -Iseconds)",
  "hostname": "$(hostname)",
  "project": "GDJ CTF 2024",
  "vm_count": 6,
  "files": {
MANIFEST

for VM_ID in "${ALL_VMS[@]}"; do
    VM_NAME="ctfd-${VM_ID}"
    DST_DISK="${EXPORT_DEST}/${VM_NAME}.qcow2"
    if [ -f "$DST_DISK" ]; then
        SIZE=$(du -b "$DST_DISK" | cut -f1)
        SHA256=$(sha256sum "$DST_DISK" | cut -d' ' -f1)
        cat >> "${EXPORT_DEST}/manifest.json" << MANIFEST
    "${VM_NAME}.qcow2": {
      "size": ${SIZE},
      "sha256": "${SHA256}",
      "scenario": "$(echo "$VM_ID" | sed 's/[0-9]//')",
      "tier": "$(echo "$VM_ID" | sed 's/[a-c]//' | sed -e 's/1/dmz/' -e 's/2/internal/')"
    },
MANIFEST
    fi
done

# Remove trailing comma from last file entry
sed -i '$ s/,$//' "${EXPORT_DEST}/manifest.json"

cat >> "${EXPORT_DEST}/manifest.json" << MANIFEST
  }
}
MANIFEST

# --- 打包 ---
echo ""
read -rp ">>> 是否打包为 tar.gz? (yes/no): " DO_TAR
if [ "$DO_TAR" = "yes" ]; then
    TARBALL="${EXPORT_DEST}/gdj-ctf-$(date +%Y%m%d).tar.gz"
    echo "[+] 打包到 $TARBALL..."
    cd "$(dirname "$EXPORT_DEST")"
    tar czf "$TARBALL" -C "$(dirname "$EXPORT_DEST")" "$(basename "$EXPORT_DEST")"
    echo "  -> $(du -h "$TARBALL" | cut -f1)"
fi

echo ""
echo "[✓] 导出完成"
echo "    目录: $EXPORT_DEST"
echo "    镜像: $(ls "${EXPORT_DEST}"/*.qcow2 2>/dev/null | wc -l) 个 .qcow2 文件"
echo "    SHA256: $SHA256_FILE"
