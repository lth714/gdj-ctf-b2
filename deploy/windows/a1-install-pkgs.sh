#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

exec > /tmp/apt-install.log 2>&1
echo "=== START INSTALL $(date) ==="

apt update
apt install -y \
    nginx apache2 \
    php7.4 php7.4-mysql php7.4-mbstring php7.4-xml \
    php7.4-curl php7.4-gd php7.4-zip libapache2-mod-php7.4 \
    mysql-client python3 python3-pip python3-venv \
    curl wget unzip iptables-persistent

echo "exit_code=$?"
echo "=== DONE $(date) ==="
