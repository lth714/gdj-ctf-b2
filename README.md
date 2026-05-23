# 广电局CTF竞赛 — 完整部署指南 (v4 Open-Source魔改版)

## 项目结构

```
gdj_ctf/
├── README.md
├── scoring/
│   └── scoreboard.xlsx          # 评分表
├── scenario-a/
│   ├── vm-a1-dmz/               # 融媒体CMS DMZ层 (魔改PbootCMS)
│   │   ├── files/
│   │   │   ├── pbootcms/        # PbootCMS (PHP — 已魔改)
│   │   │   ├── media-api/       # Flask媒体API
│   │   │   └── nginx/           # nginx配置
│   │   └── scripts/
│   │       └── setup.sh         # VM初始化脚本
│   └── vm-a2-internal/          # Internal层
│       ├── files/
│       │   ├── iptables/        # 防火墙规则
│       │   └── systemd/         # systemd服务
│       └── scripts/
│           └── setup.sh         # VM初始化脚本
├── scenario-b/
│   ├── vm-b1-dmz/               # 广电监控 DMZ层 (自研Flask)
│   │   ├── files/monitor/       # Flask监控仪表盘
│   │   └── scripts/setup.sh
│   └── vm-b2-internal/          # Internal层
│       ├── files/api-gateway/   # Go API网关
│       └── scripts/setup.sh
└── scenario-c/
    ├── vm-c1-dmz/               # 内部OA DMZ层 (魔改RuoYi)
    │   ├── files/
    │   │   ├── ruoyi/           # RuoYi 4.8.3 (Spring Boot — 已魔改)
    │   │   └── nginx/           # nginx配置
    │   └── scripts/setup.sh
    └── vm-c2-internal/          # Internal层
        ├── files/
        │   ├── iptables/        # 防火墙规则
        │   └── systemd/         # systemd服务
        └── scripts/setup.sh
```

## 魔改说明

| 场景 | DMZ应用 | 原始项目 | 代码量 | 魔改内容 |
|------|---------|---------|:-----:|----------|
| A | 融媒体CMS | PbootCMS v3.x | ~140 PHP文件 | SQL注入(API搜索)、文件上传绕过(UEditor config)、备份泄露、数据库配置 |
| B | 广电监控 | 自研Flask | ~500行Python | SSRF、命令注入、弱口令、环境变量泄露 (保持自研—定制化合理) |
| C | 内部OA | RuoYi 4.8.3 | ~285 Java文件 | JWT alg=none、SSTI(FreeMarker)、SQL注入(CSV导出)、万能验证码 |

## 快速开始

### 1. 创建基础VM模板

在KVM平台上创建Ubuntu Server 20.04基础VM：
- 1 vCPU, 2GB RAM, 15GB 磁盘 (Java服务VM建议 2 vCPU/4GB RAM)
- 网络: 2 NIC (eth0=外部DHCP, eth1=内网静态)
- 安装后运行 `apt update && apt upgrade -y`

### 2. 部署场景A (PbootCMS + Confluence)

```bash
# VM-A1 (DMZ) — PbootCMS魔改版
scp -r scenario-a/vm-a1-dmz/ root@<vm-a1-ip>:/opt/deploy/
ssh root@<vm-a1-ip> "cd /opt/deploy/scripts && bash setup.sh"

# VM-A2 (Internal) — MySQL + Redis + Confluence
scp -r scenario-a/vm-a2-internal/ root@<vm-a2-ip>:/opt/deploy/
ssh root@<vm-a2-ip> "cd /opt/deploy/scripts && bash setup.sh"
```

### 3. 部署场景B (Flask监控 + Jenkins)

```bash
# VM-B1 (DMZ) — Flask监控仪表盘
scp -r scenario-b/vm-b1-dmz/ root@<vm-b1-ip>:/opt/deploy/
ssh root@<vm-b1-ip> "cd /opt/deploy/scripts && bash setup.sh"

# VM-B2 (Internal) — PostgreSQL + Go API + Jenkins
scp -r scenario-b/vm-b2-internal/ root@<vm-b2-ip>:/opt/deploy/
ssh root@<vm-b2-ip> "cd /opt/deploy/scripts && bash setup.sh"
```

### 4. 部署场景C (RuoYi + Drupal)

```bash
# VM-C1 (DMZ) — RuoYi魔改版 + Roundcube
scp -r scenario-c/vm-c1-dmz/ root@<vm-c1-ip>:/opt/deploy/
ssh root@<vm-c1-ip> "cd /opt/deploy/scripts && bash setup.sh"

# VM-C2 (Internal) — LDAP + Samba + MySQL + Drupal
scp -r scenario-c/vm-c2-internal/ root@<vm-c2-ip>:/opt/deploy/
ssh root@<vm-c2-ip> "cd /opt/deploy/scripts && bash setup.sh"
```

### 5. 导出qcow2

```bash
virsh shutdown <vm-name>
qemu-img convert -O qcow2 /var/lib/libvirt/images/<vm-name>.qcow2 \
    /export/<scenario>-<role>.qcow2
```

## 得分速查

| 场景 | DMZ应用 | Internal N-Day | DMZ分 | Internal分 | 合计 |
|------|---------|---------------|:-----:|:----------:|:----:|
| A | 魔改PbootCMS | Confluence CVE-2022-26134 | 410 | 1200 | **1610** |
| B | 自研Flask监控 | Jenkins CVE-2024-23897 | 390 | 1200 | **1590** |
| C | 魔改RuoYi OA | Drupal CVE-2018-7600 | 390 | 1200 | **1590** |
| **总计** | | | **1190** | **3600** | **4790** |

## 场景A得分链 (魔改PbootCMS)

| # | 难度 | 分值 | 攻击路径 |
|:-:|:----:|:----:|----------|
| A-1 | ⭐ | 20 | `/backup/` autoindex → `cms_20240101.sql.gz` → testuser/Test@123456 |
| A-2 | ⭐⭐ | 100 | API搜索 `/api/search/suggest?keyword='` → SQL注入 → admin hash(md5双次) |
| A-3 | ⭐⭐ | 50 | `/config/database.php` → MySQL cmsuser/Cm5Us3r@2024! @ 192.168.100.2 |
| A-4 | ⭐⭐⭐ | 100 | SQLi LOAD_FILE → MySQL root密码 |
| A-5 | ⭐⭐ | 20 | 后台UEditor上传.pht/.phtml → webshell → www-data |
| A-6 | ⭐⭐⭐ | 100 | SUID find → root@VM-A1 |
| A-7 | ⭐⭐⭐⭐ | 700 | 扫描VM-A2:8090 → Confluence CVE-2022-26134 → shell |
| A-8 | ⭐⭐⭐⭐ | 500 | confluence提权 → root@VM-A2 |

## 场景C得分链 (魔改RuoYi)

| # | 难度 | 分值 | 攻击路径 |
|:-:|:----:|:----:|----------|
| C-1 | ⭐ | 20 | `/register` captcha backdoor "gdj2024" → 普通用户注册 |
| C-2 | ⭐⭐ | 100 | `/api/login` JWT alg=none → 伪造admin token |
| C-3 | ⭐⭐ | 50 | `/api/admin/export?department=' UNION` → SQL注入 |
| C-4 | ⭐⭐⭐ | 100 | `application-druid.yml` → LDAP密码 Ldap@Admin#2024 |
| C-5 | ⭐⭐ | 20 | `/mail/preview?content=<#assign ex=...>` → FreeMarker SSTI → shell |
| C-6 | ⭐⭐⭐ | 100 | sudo tee → root@VM-C1 |
| C-7 | ⭐⭐⭐⭐ | 700 | 扫描VM-C2:80 → Drupal CVE-2018-7600 → shell |
| C-8 | ⭐⭐⭐⭐ | 500 | www-data提权 → root@VM-C2 |

## 赛后重置

每台VM上运行：
```bash
# 重置MySQL
mysql -u root -p < /opt/deploy/init_db.sql

# 重置Confluence (场景A)
systemctl stop confluence
rm -rf /var/atlassian/confluence/*
systemctl start confluence

# 重置Jenkins (场景B)
systemctl stop jenkins
rm -rf /var/lib/jenkins/*
systemctl start jenkins

# 重置Drupal (场景C)
mysql -u root -p'R00t@Mysql#2024' -e "DROP DATABASE drupal; CREATE DATABASE drupal;"
# 重新安装Drupal

# 清理上传文件
rm -f /var/www/cms/static/upload/image/*.php /var/www/cms/static/upload/image/*.pht

# 重启服务
systemctl restart nginx apache2 mysql postgresql 2>/dev/null || true
```

## 注意事项

1. **Maven构建**: RuoYi首次构建需下载依赖(约400MB)，确保VM-C1有外网访问
2. **Java版本**: RuoYi需要Java 17+，Ubuntu 20.04需通过`ppa:openjdk-r/ppa`安装，setup.sh已自动处理
3. **Confluence/Jenkins/Drupal**: N-Day应用需要手动下载安装包，详见各VM setup.sh中的INSTALL.txt
4. **iptables**: 每次VM重启后规则通过netfilter-persistent自动恢复
5. **PHP版本**: Ubuntu 20.04原生PHP 7.4，PbootCMS和Drupal均兼容
6. **PostgreSQL**: Ubuntu 20.04默认PostgreSQL 12，VM-B2 setup.sh已适配
7. **截图验证**: 评分时需参赛队伍提供完整的权限截图(双网卡+whoami+id)
