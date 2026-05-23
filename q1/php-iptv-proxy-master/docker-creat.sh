
#!/bin/bash

# 创建 docker 目录
mkdir -p docker

# 创建 Dockerfile
cat > Dockerfile << 'EOL'
# 使用官方PHP-FPM镜像作为基础镜像
FROM php:8.1-fpm

# 设置工作目录
WORKDIR /var/www/html

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    libpng-dev \
    libonig-dev \
    libxml2-dev \
    zip \
    unzip \
    nginx \
    supervisor

# 安装PHP扩展
RUN docker-php-ext-install pdo_mysql mbstring exif pcntl bcmath gd

# 安装Redis扩展
RUN pecl install redis && docker-php-ext-enable redis

# 复制项目文件
COPY . /var/www/html

# 设置文件权限
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html/storage

# 复制Nginx配置
COPY docker/nginx.conf /etc/nginx/sites-available/default

# 复制Supervisor配置
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 暴露端口
EXPOSE 80 9261

# 启动Supervisor
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EOL

# 创建 docker-compose.yml
cat > docker-compose.yml << 'EOL'
version: '3'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: iptv-proxy-app
    restart: unless-stopped
    ports:
      - "80:80"
      - "9261:9261"
    volumes:
      - ./:/var/www/html
      - ./storage/logs:/var/www/html/storage/logs
    depends_on:
      - mysql
      - redis
    networks:
      - iptv-network

  mysql:
    image: mysql:8.0
    container_name: iptv-proxy-mysql
    restart: unless-stopped
    environment:
      MYSQL_DATABASE: iptv_proxy
      MYSQL_USER: iptv_proxy
      MYSQL_PASSWORD: ${DB_PASSWORD}
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
    volumes:
      - mysql-data:/var/lib/mysql
    networks:
      - iptv-network

  redis:
    image: redis:alpine
    container_name: iptv-proxy-redis
    restart: unless-stopped
    volumes:
      - redis-data:/data
    networks:
      - iptv-network

networks:
  iptv-network:
    driver: bridge

volumes:
  mysql-data:
  redis-data:
EOL

# 创建 nginx.conf
cat > docker/nginx.conf << 'EOL'
server {
    listen 80;
    server_name _;
    root /var/www/html/public;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass 127.0.0.1:9000;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
EOL

# 创建 supervisord.conf
cat > docker/supervisord.conf << 'EOL'
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:php-fpm]
command=/usr/local/sbin/php-fpm
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/php-fpm.err.log
stdout_logfile=/var/log/supervisor/php-fpm.out.log

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/nginx.err.log
stdout_logfile=/var/log/supervisor/nginx.out.log

[program:iptv-proxy]
command=php /var/www/html/bin/proxy.php
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/iptv-proxy.err.log
stdout_logfile=/var/log/supervisor/iptv-proxy.out.log
EOL

# 创建 .env
cat > .env << 'EOL'
DB_PASSWORD=your_db_password
DB_ROOT_PASSWORD=your_root_password
EOL

# 创建 .dockerignore
cat > .dockerignore << 'EOL'
.git
.env
.gitignore
README.md
storage/*.key
vendor
node_modules
EOL

# 设置文件权限
chmod 644 docker-compose.yml Dockerfile .env .dockerignore
chmod 644 docker/nginx.conf docker/supervisord.conf

echo "Docker 配置文件创建完成！"
echo "请修改 .env 文件中的数据库密码，然后运行 docker-compose up -d 启动服务。"