# IPTV 代理系统

一个功能强大的 IPTV 代理系统，支持频道管理、实时监控、带宽控制、日志记录等功能。

## 主要功能

### 1. 频道管理
- 添加、编辑、删除频道
- 批量导入频道（支持 m3u/m3u8/txt 格式）
- 频道分组管理
- 频道状态监控
- 批量检查频道可用性
- 自定义每页显示记录数（10/20/50/100条）
- 频道代理地址自动生成
- 频道在线状态检测
- 频道延迟监测
- 频道带宽监控（上行/下行）
- 频道连接数统计

### 2. 系统监控
- 实时监控频道状态
- 显示频道延迟
- 显示频道带宽使用情况
  - 上行带宽监控
  - 下行带宽监控
  - 总带宽统计
- 显示频道连接数
- Redis 缓存监控
- 系统性能监控
  - CPU 使用率
  - 内存使用情况
  - 磁盘使用情况
  - 系统负载

### 3. 日志管理
- 操作日志记录
  - 频道创建记录
  - 频道导入记录
  - 频道修改记录
  - 频道删除记录
  - 系统设置修改记录
- 错误日志记录
  - 连接错误记录
  - 超时错误记录
  - HTTP错误记录
  - 系统错误记录
- 日志查询功能
  - 时间范围筛选
  - 日志类型筛选
  - 关键词搜索

### 4. 系统设置
- 基本设置
  - 站点名称设置
  - 最大错误次数设置
- 代理服务器设置
  - 监听地址配置
  - 监听端口配置
  - 连接超时设置
  - 缓冲区大小设置
- 缓存设置
  - 缓存时间设置
  - 分片大小设置
- Redis设置
  - Redis服务器配置
  - Redis端口配置
  - Redis密码配置
- 监控设置
  - 监控刷新间隔
  - 状态检查间隔
- 带宽控制设置
  - 全局带宽限制
  - 单频道带宽限制
  - 上行带宽限制
  - 下行带宽限制

## 目录结构

```
├── config/                 # 配置文件目录
│   └── config.php         # 主配置文件
├── install/               # 安装相关文件
│   ├── deploy.sh         # 部署脚本
│   ├── install.php       # 安装程序
│   ├── install.sh        # 安装脚本
│   ├── templates/        # 安装模板
│   └── test.php          # 环境测试脚本
├── public/               # 公共访问目录
│   ├── css/             # CSS文件
│   ├── js/              # JavaScript文件
│   ├── index.php        # 入口文件
│   └── login.php        # 登录页面
├── src/                  # 源代码目录
│   ├── Core/            # 核心类
│   │   ├── Auth.php     # 认证类
│   │   ├── Config.php   # 配置类
│   │   ├── Database.php # 数据库类
│   │   └── Redis.php    # Redis类
│   ├── Models/          # 数据模型
│   └── views/           # 视图文件
│       ├── admin/       # 管理后台视图
│       ├── index.php    # 首页视图
│       └── navbar.php   # 导航栏视图
├── storage/              # 存储目录
│   ├── cache/           # 缓存目录
│   └── logs/            # 日志目录
└── vendor/              # 第三方依赖
```

## 文件说明

### 核心文件
- `src/Core/Config.php`: 配置管理类，处理系统配置的读取和保存
- `src/Core/Database.php`: 数据库操作类，提供数据库连接和基本操作
- `src/Core/Redis.php`: Redis操作类，处理缓存和实时数据
- `src/Core/Auth.php`: 认证类，处理用户登录和权限验证

### 视图文件
- `src/views/index.php`: 系统首页，显示系统概览
- `src/views/admin/channels/index.php`: 频道管理页面
- `src/views/admin/channels/edit.php`: 频道编辑页面
- `src/views/admin/channels/import.php`: 频道导入页面
- `src/views/admin/monitor/index.php`: 系统监控页面
- `src/views/admin/settings/index.php`: 系统设置页面
- `src/views/admin/logs/index.php`: 日志管理页面

### 安装文件
- `install/install.php`: 安装程序主文件
- `install/deploy.sh`: 系统部署脚本
- `install/test.php`: 环境检测脚本

## 功能实现逻辑

### 1. 频道管理实现
- 频道数据存储在MySQL数据库中
- 使用PDO进行数据库操作
- 频道状态实时更新到Redis缓存
- 支持批量操作和异步处理

### 2. 带宽监控实现
- 实时监控每个频道的带宽使用
- 分别统计上行和下行带宽
- 数据存储在Redis中实现实时更新
- 定期同步到MySQL数据库存档

### 3. 连接数管理实现
- 使用Redis存储实时连接信息
- 支持按IP统计连接数
- 支持按频道统计连接数
- 定时清理过期连接记录

### 4. 缓存机制实现
- 使用Redis作为缓存服务器
- 支持数据分片存储
- 自动清理过期缓存
- 缓存预热机制

## 安装要求

### 系统要求
- Linux/Unix 系统
- PHP 7.4+
- MySQL 5.7+
- Redis 6.0+
- Nginx/Apache

### PHP扩展要求
- PDO
- PDO_MySQL
- Redis
- Curl
- JSON
- MBString

### 推荐配置
- CPU: 2核心以上
- 内存: 4GB以上
- 硬盘: 50GB以上
- 带宽: 100Mbps以上

## 安装步骤

1. 环境准备
```bash
# 运行环境检测
php install/test.php

# 安装依赖
./install/install.sh
```

2. 配置文件设置
```bash
# 复制配置文件
cp config/config.example.php config/config.php

# 修改配置文件
vim config/config.php
```

3. 数据库配置
```sql
-- 创建数据库
CREATE DATABASE iptv_proxy;

-- 导入数据库结构
mysql -u root -p iptv_proxy < install/database.sql
```

4. 启动服务
```bash
# 部署服务
./install/deploy.sh

# 启动服务
systemctl start nginx
systemctl start php-fpm
systemctl start redis
```

## 注意事项

### 1. 性能优化
- 建议使用Redis缓存
- 适当配置检查间隔
- 合理设置缓存时间
- 定期清理日志文件
- 优化数据库查询

### 2. 安全建议
- 修改默认密码
- 限制管理员访问IP
- 定期备份数据
- 设置文件权限
- 使用HTTPS协议

### 3. 维护建议
- 定期清理日志
- 监控系统资源
- 及时更新系统
- 定期检查频道
- 备份重要数据

## 常见问题

1. 安装失败
- 检查环境要求
- 检查文件权限
- 查看错误日志

2. 频道无法播放
- 检查源地址可用性
- 检查网络连接
- 查看错误日志
- 检查带宽使用情况

3. 系统性能问题
- 检查服务器负载
- 优化Redis配置
- 调整PHP配置
- 优化MySQL查询

## 更新日志

### v1.0.0 (2024-01-20)
- 初始版本发布
- 基本功能实现

### v1.1.0 (2024-01-25)
- 添加带宽监控功能
- 优化连接数统计
- 改进用户界面
- 修复已知问题

## 许可证

MIT License

## 技术支持

- 问题反馈：提交Issue
- 功能建议：提交Pull Request
- 技术讨论：参与Discussions 
- 

可在程序根目录执行：docker-compose up -d