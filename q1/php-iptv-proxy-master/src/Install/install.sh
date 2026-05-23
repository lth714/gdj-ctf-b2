#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 定义变量
PHP_VERSION="8.1"
WEB_ROOT="/var/www/html"
MYSQL_ROOT_PASSWORD=$(openssl rand -base64 12)
LOG_FILE="/var/log/iptv-proxy-install.log"
BACKUP_DIR="/root/iptv-proxy-backup-$(date +%Y%m%d%H%M%S)"

# 输出带颜色的信息
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示欢迎界面
show_banner() {
    clear
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║         IPTV代理系统环境安装脚本         ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "此脚本将安装以下组件："
    echo "- PHP ${PHP_VERSION} 及必要扩展"
    echo "- Nginx Web服务器"
    echo "- MySQL 数据库服务器"
    echo "- Redis 缓存服务器"
    echo
    echo -e "${YELLOW}警告：此脚本仅支持在纯净的Debian/Ubuntu系统中执行${NC}"
    echo -e "${YELLOW}在已配置过的服务器中执行可能会导致现有配置丢失${NC}"
    echo
}

# 检查系统环境
check_system() {
    info "检查系统环境..."

    # 检查是否为root用户
    if [ "$EUID" -ne 0 ]; then 
        error "请使用root权限运行此脚本"
        exit 1
    fi

    # 检查系统类型
    if ! command -v apt &> /dev/null; then
        error "此脚本仅支持Debian/Ubuntu系统"
        exit 1
    fi

    # 检查是否为纯净系统
    local services=("nginx" "apache2" "mysql" "redis-server")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet $service; then
            error "检测到 $service 服务已安装，请在纯净系统中运行此脚本"
            exit 1
        fi
    done

    # 检查端口占用
    local ports=(80 443 3306 6379)
    for port in "${ports[@]}"; do
        if netstat -tuln | grep -q ":$port "; then
            error "端口 $port 已被占用"
            exit 1
        fi
    done

    # 检查系统资源
    local total_mem=$(free -m | awk '/^Mem:/{print $2}')
    local free_disk=$(df -m / | awk 'NR==2 {print $4}')

    if [ $total_mem -lt 1024 ]; then
        warn "系统内存小于1GB，可能会影响性能"
    fi

    if [ $free_disk -lt 5120 ]; then
        warn "磁盘剩余空间小于5GB，建议清理磁盘"
    fi

    success "系统环境检查完成"
}

# 创建备份
create_backup() {
    info "创建系统配置备份..."
    mkdir -p "$BACKUP_DIR"
    
    # 备份配置文件
    if [ -d /etc/nginx ]; then
        cp -r /etc/nginx "$BACKUP_DIR/"
    fi
    if [ -d /etc/php ]; then
        cp -r /etc/php "$BACKUP_DIR/"
    fi
    if [ -d /etc/mysql ]; then
        cp -r /etc/mysql "$BACKUP_DIR/"
    fi

    success "备份完成，备份目录: $BACKUP_DIR"
}

# 回滚函数
rollback() {
    error "安装失败，开始回滚..."
    
    # 停止服务
    systemctl stop nginx php${PHP_VERSION}-fpm mysql redis-server 2>/dev/null

    # 卸载软件包
    apt remove --purge -y nginx php${PHP_VERSION}-fpm php${PHP_VERSION}-cli php${PHP_VERSION}-common \
        php${PHP_VERSION}-mysql php${PHP_VERSION}-zip php${PHP_VERSION}-gd php${PHP_VERSION}-mbstring \
        php${PHP_VERSION}-curl php${PHP_VERSION}-xml php${PHP_VERSION}-bcmath php${PHP_VERSION}-json \
        php${PHP_VERSION}-redis mysql-server redis-server

    # 恢复备份
    if [ -d "$BACKUP_DIR" ]; then
        cp -r "$BACKUP_DIR"/* /etc/
    fi

    error "系统已回滚到初始状态"
    exit 1
}

# 安装基础组件
install_base() {
    info "更新系统包..."
    apt update && apt upgrade -y || rollback

    info "安装基础依赖..."
    apt install -y curl wget git unzip net-tools || rollback
}

# 安装和配置PHP
install_php() {
    info "安装PHP及扩展..."
    apt install -y php${PHP_VERSION}-fpm php${PHP_VERSION}-cli php${PHP_VERSION}-common \
        php${PHP_VERSION}-mysql php${PHP_VERSION}-zip php${PHP_VERSION}-gd php${PHP_VERSION}-mbstring \
        php${PHP_VERSION}-curl php${PHP_VERSION}-xml php${PHP_VERSION}-bcmath php${PHP_VERSION}-json \
        php${PHP_VERSION}-redis || rollback

    info "配置PHP..."
    local php_ini="/etc/php/${PHP_VERSION}/fpm/php.ini"
    sed -i 's/upload_max_filesize = 2M/upload_max_filesize = 100M/' $php_ini
    sed -i 's/post_max_size = 8M/post_max_size = 100M/' $php_ini
    sed -i 's/memory_limit = 128M/memory_limit = 256M/' $php_ini
    sed -i 's/;cgi.fix_pathinfo=1/cgi.fix_pathinfo=0/' $php_ini
    
    # 清除禁用函数
    sed -i 's/disable_functions = .*/disable_functions = /' $php_ini

    success "PHP安装和配置完成"
}

# 安装和配置MySQL
install_mysql() {
    info "安装MySQL..."
    apt install -y mysql-server || rollback

    info "配置MySQL..."
    # 设置root密码
    mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$MYSQL_ROOT_PASSWORD';"
    
    # 删除匿名用户
    mysql -e "DELETE FROM mysql.user WHERE User='';"
    
    # 禁止root远程登录
    mysql -e "DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"
    
    # 删除测试数据库
    mysql -e "DROP DATABASE IF EXISTS test;"
    mysql -e "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';"
    
    # 刷新权限
    mysql -e "FLUSH PRIVILEGES;"

    success "MySQL安装和配置完成"
    info "MySQL root密码: $MYSQL_ROOT_PASSWORD"
    echo $MYSQL_ROOT_PASSWORD > "$WEB_ROOT/mysql_root_password.txt"
}

# 安装和配置Nginx
install_nginx() {
    info "安装Nginx..."
    apt install -y nginx || rollback

    info "配置Nginx..."
    cp nginx.conf /etc/nginx/sites-available/iptv-proxy
    ln -s /etc/nginx/sites-available/iptv-proxy /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    success "Nginx安装和配置完成"
}

# 安装Redis
install_redis() {
    info "安装Redis..."
    apt install -y redis-server || rollback

    success "Redis安装完成"
}

# 设置文件权限
set_permissions() {
    info "设置文件权限..."
    
    chown -R www-data:www-data $WEB_ROOT
    find $WEB_ROOT -type f -exec chmod 644 {} \;
    find $WEB_ROOT -type d -exec chmod 755 {} \;
    
    # 设置特殊目录权限
    chmod -R 777 $WEB_ROOT/storage
    chmod -R 777 $WEB_ROOT/public/uploads

    success "文件权限设置完成"
}

# 主函数
main() {
    # 重定向输出到日志文件
    exec 1> >(tee -a "$LOG_FILE") 2>&1
    
    show_banner
    
    # 用户确认
    read -p "是否继续安装？[y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi

    check_system
    create_backup
    install_base
    install_php
    install_mysql
    install_nginx
    install_redis
    set_permissions

    # 重启服务
    info "重启服务..."
    systemctl restart php${PHP_VERSION}-fpm nginx mysql redis-server

    # 设置开机自启
    systemctl enable php${PHP_VERSION}-fpm nginx mysql redis-server

    success "安装完成！"
    echo
    echo "安装信息："
    echo "- Web根目录: $WEB_ROOT"
    echo "- MySQL root密码: $MYSQL_ROOT_PASSWORD"
    echo "- MySQL密码文件位置: $WEB_ROOT/mysql_root_password.txt"
    echo "- 安装日志: $LOG_FILE"
    echo
    echo "请访问 http://您的服务器IP/install.php 继续安装程序"
}

# 执行主函数
main