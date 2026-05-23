#!/bin/bash
# ============================================
# N-Day应用预下载脚本
# 下载Confluence、Jenkins、Drupal安装包到对应files/目录
# ============================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[+] 下载 N-Day 应用安装包..."
echo ""

# Confluence 7.13.6
CONFLUENCE_URL="https://product-downloads.atlassian.com/software/confluence/downloads/atlassian-confluence-7.13.6.tar.gz"
CONFLUENCE_DEST="$PROJECT_DIR/scenario-a/vm-a2-internal/files"
mkdir -p "$CONFLUENCE_DEST"
echo "[1/3] 下载 Confluence 7.13.6 (~800MB)..."
if [ -f "$CONFLUENCE_DEST/confluence.tar.gz" ]; then
    echo "  -> 已存在，跳过"
else
    wget -O "$CONFLUENCE_DEST/confluence.tar.gz" "$CONFLUENCE_URL" || {
        echo "  [!] Confluence下载失败。手动下载并放到: $CONFLUENCE_DEST/confluence.tar.gz"
    }
fi

# Jenkins 2.441.1 LTS
JENKINS_URL="https://get.jenkins.io/war-stable/2.441.1/jenkins.war"
JENKINS_DEST="$PROJECT_DIR/scenario-b/vm-b2-internal/files"
mkdir -p "$JENKINS_DEST"
echo "[2/3] 下载 Jenkins 2.441.1 (~70MB)..."
if [ -f "$JENKINS_DEST/jenkins.war" ]; then
    echo "  -> 已存在，跳过"
else
    wget -O "$JENKINS_DEST/jenkins.war" "$JENKINS_URL" || {
        echo "  [!] Jenkins下载失败。手动下载并放到: $JENKINS_DEST/jenkins.war"
    }
fi

# Drupal 7.57
DRUPAL_URL="https://ftp.drupal.org/files/projects/drupal-7.57.tar.gz"
DRUPAL_DEST="$PROJECT_DIR/scenario-c/vm-c2-internal/files"
mkdir -p "$DRUPAL_DEST"
echo "[3/3] 下载 Drupal 7.57 (~12MB)..."
if [ -f "$DRUPAL_DEST/drupal.tar.gz" ]; then
    echo "  -> 已存在，跳过"
else
    wget -O "$DRUPAL_DEST/drupal.tar.gz" "$DRUPAL_URL" || {
        echo "  [!] Drupal下载失败。手动下载并放到: $DRUPAL_DEST/drupal.tar.gz"
    }
fi

echo ""
echo "[+] 下载完成。"
echo "    离线环境：确保将下载好的文件随项目一起传输到KVM宿主机。"
