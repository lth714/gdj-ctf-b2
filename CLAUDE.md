# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GDJ CTF 竞赛平台 — 三个独立场景(A/B/C)的红队攻防CTF环境。每个场景包含一台DMZ VM和一台Internal VM，模拟真实企业网络拓扑。所有漏洞均为预留后门/魔改源码实现，非真实0-day。

## Key Architecture

**三层网络隔离模型:**
- DMZ层 (对外): Nginx反向代理 + 魔改Web应用，仅开放80端口
- 内网层: 数据库/缓存/知识库等支撑服务，iptables仅允许对应DMZ来源访问
- 横向移动: DMZ→Internal通过N-Day漏洞获取shell，SSH端口在DMZ侧被DROP

**三个场景独立网络段:** A=192.168.100.0/24, B=192.168.110.0/24, C=192.168.120.0/24

**VM命名规范:** `vm-{场景}-{角色}` (如 vm-a1-dmz, vm-a2-internal)

## Directory Structure

```
scenario-{a,b,c}/vm-{X}-{role}/
├── files/          # 应用源码、配置文件、模板
└── scripts/        # VM初始化setup.sh脚本
deploy/windows/     # 宿主机侧Python自动化部署脚本 (SSH + paramiko)
docs/               # NETWORK.md (拓扑/防火墙/凭据), VERIFICATION.md (攻击链验证), *-SCENARIO-REPRODUCTION.md (复现手册)
scoring/            # 评分表
vms/                # QEMU磁盘镜像存放目录
```

## Common Operations

### SSH连接VM
```bash
ssh -o StrictHostKeyChecking=no gdadmin@<IP>
# 密码: Gdadmin@123 (见 ssh-config.json)
```
`ssh-config.json` 记录所有VM的IP、用户名、密码。

### 部署脚本执行 (Windows宿主机)
所有部署脚本位于 `deploy/windows/`，使用Python + paramiko通过SSH远程执行部署/修复操作：
```bash
python3 deploy/windows/deploy-a1.py    # 部署VM-A1
python3 deploy/windows/<script>.py     # 其他VM同理
```
这些脚本的实现模式：`paramiko.SSHClient()` 连接VM → `exec_command()` 远程执行shell命令 → 打印输出。

### 场景文件传输
```bash
scp -r scenario-a/vm-a1-dmz/files/ gdadmin@<ip>:/opt/deploy/files/
scp -r scenario-a/vm-a1-dmz/scripts/ gdadmin@<ip>:/opt/deploy/scripts/
ssh gdadmin@<ip> "cd /opt/deploy/scripts && sudo bash setup.sh"
```

## Attack Summaries (for quick reference)

**场景A — 融媒体CMS (PbootCMS魔改):**
- A-1/A-3: 备份文件泄露 (`/backup/` autoindex, `/config/database.php` 源码泄露)
- A-2: SQL注入 (搜索框 UNION注入提取ay_user表)
- A-4: SQLi LOAD_FILE 读取MySQL root配置文件
- A-5: UEditor文件上传绕过 (.phtml白名单, config.json中imageAllowFiles含.pht/.phtml)
- A-6: SUID find提权 (`/usr/bin/find` SUID bit)
- A-7: Confluence CVE-2022-26134 OGNL注入 (A2:8090, 需从A1跳板)
- A-8: Cron脚本劫持提权 (`/opt/confluence_health_check.sh` 777, root cron每10分钟)

**场景B — 广电监控 (自研Flask):**
- B-1/B-2: 弱口令 `admin/admin123` + SSRF (`?page=probe&target=`) 探测内网Go API
- B-3: Go API命令注入 (`/api/diag?cmd=ping&target=;CMD`, `strings.HasPrefix`白名单绕过)
- B-4/B-5: 配置文件/环境变量泄露PG凭据
- B-6: Cron脚本提权 (`/opt/monitor/cleanup.sh` 777, root cron每5分钟)
- B-7: Jenkins CVE-2024-23897 CLI文件读取 → Groovy RCE (B2:8081)
- B-8: Cron脚本提权 (`/opt/jenkins_backup.sh` 777, root cron凌晨2点)

**场景C — OA系统 (RuoYi 4.8.3魔改):**
- C-1/C-2: 注册验证码后门 `gdj2024` + JWT alg=none伪造admin
- C-3: SQL注入 (`/api/login` UNION注入, C2 MySQL oa库, 密码明文存储)
- C-4: Druid配置泄露 (`/druid/datasource.json`, 含LDAP/SMTP/MySQL凭据)
- C-5: FreeMarker SSTI → RCE (`/mail/preview`, `freemarker.template.utility.Execute`)
- C-6: sudo tee提权 (tomcat NOPASSWD tee → 写cron/ssh key)
- C-7: Drupal CVE-2018-7600 (Drupalgeddon2, C2:80)
- C-8: sudo find提权 (operator NOPASSWD find, C2)

## Critical Credentials Reference

| Context | Details |
|---------|---------|
| All VM SSH | `gdadmin` / `Gdadmin@123` |
| SSH operator (A2/B2/C2) | `operator` / `0p3rat0r@GDJ` |
| MySQL root (A2/C1) | `root` / `R00t@Mysql#2024` |
| MySQL app user | `cmsuser`/`Cm5Us3r@2024!` (A2), `oauser`/`Oaus3r@2024!` (C2) |
| LDAP (C2) | `cn=admin,dc=gdj,dc=local` / `Ldap@Admin#2024` |
| PbootCMS admin | `admin` / `Admin@Cms2024` (MD5²: `f0916d59b2d497402968dbdd3641ddbe`) |
| Flask Monitor (B1) | `admin` / `admin123` (SHA256 hashed in USERS dict) |
| RuoYi admin | `admin` / `admin123` |

Full table in [docs/NETWORK.md](docs/NETWORK.md#凭据汇总).

## Documentation Files

- [README.md](README.md) — 部署快速开始、魔改说明、得分速查
- [docs/NETWORK.md](docs/NETWORK.md) — 完整网络拓扑、服务端口矩阵、防火墙规则、凭据汇总、提权向量
- [docs/VERIFICATION.md](docs/VERIFICATION.md) — 24条攻击链的验证命令（含curl POC、预期输出）
- [docs/A-SCENARIO-REPRODUCTION.md](docs/A-SCENARIO-REPRODUCTION.md) — 场景A Yakit/Burp详细复现步骤
- [docs/B-SCENARIO-REPRODUCTION.md](docs/B-SCENARIO-REPRODUCTION.md) — 场景B详细复现步骤
- [docs/C-SCENARIO-REPRODUCTION.md](docs/C-SCENARIO-REPRODUCTION.md) — 场景C详细复现步骤

## Platform Constraints

- **宿主机环境:** Windows 11 + QEMU 9.0.50 (WHPX加速) + TAP网桥
- **VM OS:** Ubuntu Server 20.04
- **应用栈:** PHP 7.4 (PbootCMS/Drupal), Python 3.8+ (Flask media-api/monitor), Java 17 (RuoYi Spring Boot), Go (API Gateway)
- **数据库:** MySQL 8.0, PostgreSQL 12, Redis
- **Web服务器:** Nginx (反向代理) + Apache (后端PHP)
- **关键文件路径 (VM内部):** `/opt/deploy/` (部署目录), `/opt/ops/access.txt` (凭据文件), `/opt/monitor/` (监控应用), `/var/www/cms/` (CMS根目录)
