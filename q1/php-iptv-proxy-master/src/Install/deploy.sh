#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "IPTV代理系统部署脚本"
echo "===================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用root权限运行此脚本${NC}"
    exit 1
fi

# 创建必要的目录
echo "创建目录结构..."
mkdir -p /var/www/html/{public,config,storage/{logs,cache}}
chown -R www-data:www-data /var/www/html

# 复制文件
echo "复制项目文件..."
cp -r ./* /var/www/html/
chown -R www-data:www-data /var/www/html

# 设置权限
echo "设置文件权限..."
chmod -R 755 /var/www/html
chmod -R 777 /var/www/html/storage

# 配置Nginx
echo "配置Nginx..."
cp nginx.conf /etc/nginx/sites-available/iptv-proxy
ln -sf /etc/nginx/sites-available/iptv-proxy /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 重启服务
echo "重启服务..."
systemctl restart nginx
systemctl restart php8.1-fpm

echo -e "${GREEN}部署完成！${NC}"
echo "请访问 http://您的服务器IP/install.php 开始安装" 