# GDJ CTF 网络拓扑

## 拓扑图

```
                           ┌──────────────┐
                           │   互联网      │
                           └──────┬───────┘
                                  │
                           ┌──────┴───────┐
                           │   br0 (外部)  │  10.0.0.0/24 (DHCP from upstream)
                           └┬──┬──┬──┬──┬─┘
                            │  │  │  │  │
            ┌───────────────┘  │  │  │  └───────────────┐
            │                  │  │  │                  │
       ┌────┴────┐       ┌────┴──┐ │ ┌──┴────┐       ┌──┴──────┐
       │ VM-A1   │       │ VM-B1 │ │ │ VM-C1 │       │ Host    │
       │ DMZ     │       │ DMZ   │ │ │ DMZ   │       │ (KVM)   │
       │ eth0:dhcp│      │ eth0  │ │ │ eth0  │       │         │
       │ eth1:────┼──┐    │ eth1  │ │ │ eth1  │       └─────────┘
       └─────────┘  │    └───────┘ │ └───────┘
                    │              │
          ┌─────────┘     ┌────────┘     ┌─────────┐
          │               │              │         │
    ┌─────┴─────┐   ┌─────┴─────┐  ┌─────┴─────┐   │
    │  br-a     │   │  br-b     │  │  br-c     │   │
    │192.168.100.0/24│   │192.168.110.0/24│  │192.168.120.0/24│   │
    └─────┬─────┘   └─────┬─────┘  └─────┬─────┘   │
          │               │              │         │
    ┌─────┴─────┐   ┌─────┴─────┐  ┌─────┴─────┐   │
    │ VM-A2     │   │ VM-B2     │  │ VM-C2     │   │
    │ Internal  │   │ Internal  │  │ Internal  │   │
    │eth0:192.168.100.2  │eth0:192.168.110.2  │eth0:192.168.120.2  │
    └───────────┘   └───────────┘  └───────────┘   │
                                                    │
    Host access: 192.168.100.254/24 ─────────────────────┘
                 192.168.110.254/24
                 192.168.120.254/24
```

## IP地址分配

| VM | 角色 | 外部IP (br0) | 内部IP (br-X) | 所属场景 |
|---|---|---|---|---|
| VM-A1 | DMZ Web | DHCP | 192.168.100.1/24 | 场景A |
| VM-A2 | Internal DB | — | 192.168.100.2/24 | 场景A |
| VM-B1 | DMZ Monitor | DHCP | 192.168.110.1/24 | 场景B |
| VM-B2 | Internal API | — | 192.168.110.2/24 | 场景B |
| VM-C1 | DMZ OA | DHCP | 192.168.120.1/24 | 场景C |
| VM-C2 | Internal LDAP | — | 192.168.120.2/24 | 场景C |
| Host | KVM宿主机 | DHCP (br0) | 10.0.X.254/24 | 管理 |

## 服务端口矩阵

### 场景A — 融媒体内容管理系统

| 服务 | VM | 监听地址 | 端口 | 访问来源 |
|---|---|---|---|---|
| Nginx | A1 | 0.0.0.0 | 80 | 外部 (br0) |
| Apache/PbootCMS | A1 | 127.0.0.1 | 8080 | localhost via nginx |
| Flask media-api | A1 | 127.0.0.1 | 5000 | localhost via nginx |
| MySQL 8.0 | A2 | 0.0.0.0 | 3306 | 192.168.100.1 only (iptables) |
| Redis | A2 | 0.0.0.0 | 6379 | 192.168.100.1 only (iptables) |
| Confluence 7.13.6 | A2 | 0.0.0.0 | 8090 | 192.168.100.1 only (iptables) |
| SSH | A2 | 0.0.0.0 | 22 | 192.168.100.0/24 |

### 场景B — 广电网络监控仪表盘

| 服务 | VM | 监听地址 | 端口 | 访问来源 |
|---|---|---|---|---|
| Nginx | B1 | 0.0.0.0 | 80 | 外部 (br0) |
| Flask Monitor | B1 | 127.0.0.1 | 5000 | localhost via nginx |
| PostgreSQL 12 | B2 | * | 5432 | 192.168.110.1 only (iptables) |
| Go API Gateway | B2 | 0.0.0.0 | 8080 | 192.168.110.1 only (iptables) |
| Jenkins 2.441 | B2 | 0.0.0.0 | 8081 | 192.168.110.1 only (iptables) |

### 场景C — 内部办公OA系统

| 服务 | VM | 监听地址 | 端口 | 访问来源 |
|---|---|---|---|---|
| Nginx | C1 | 0.0.0.0 | 80 | 外部 (br0) |
| RuoYi OA (Spring Boot) | C1 | 127.0.0.1 | 8080 | localhost via nginx |
| Roundcube (Apache) | C1 | 127.0.0.1 | 8081 | localhost via nginx |
| MySQL 8.0 (本地) | C1 | localhost | 3306 | localhost only |
| OpenLDAP | C2 | 0.0.0.0 | 389 | 192.168.120.1 only (iptables) |
| Samba | C2 | 0.0.0.0 | 445 | 192.168.120.1 only (iptables) |
| MySQL 8.0 | C2 | 0.0.0.0 | 3306 | 192.168.120.1 only (iptables) |
| Drupal 7.57 (Apache) | C2 | 0.0.0.0 | 80 | 192.168.120.1 only (iptables) |

## 防火墙规则

### VM-A1 (DMZ) 入站规则
```
ACCEPT  lo
ACCEPT  ESTABLISHED,RELATED
ACCEPT  tcp/80  (外部 — nginx)
ACCEPT  icmp
DROP    all
```

### VM-A2 (Internal) 入站规则
```
ACCEPT  lo
ACCEPT  ESTABLISHED,RELATED
ACCEPT  tcp/3306  from 192.168.100.1/32  # MySQL
ACCEPT  tcp/6379  from 192.168.100.1/32  # Redis
ACCEPT  tcp/8090  from 192.168.100.1/32  # Confluence
# SSH BLOCKED from 192.168.100.1 (confluence exploit required)
ACCEPT  from 192.168.100.0/24
ACCEPT  icmp
DROP    all
```

### VM-B1 (DMZ) 入站规则
```
ACCEPT  lo
ACCEPT  ESTABLISHED,RELATED
ACCEPT  tcp/80  (外部 — nginx)
ACCEPT  icmp
DROP    all
```

### VM-B2 (Internal) 入站规则
```
ACCEPT  lo
ACCEPT  ESTABLISHED,RELATED
ACCEPT  tcp/5432  from 192.168.110.1/32  # PostgreSQL
ACCEPT  tcp/8080  from 192.168.110.1/32  # API Gateway
ACCEPT  tcp/8081  from 192.168.110.1/32  # Jenkins
# SSH BLOCKED from 192.168.110.1
ACCEPT  from 192.168.110.0/24
ACCEPT  icmp
DROP    all
```

### VM-C1 (DMZ) 入站规则
```
ACCEPT  lo
ACCEPT  ESTABLISHED,RELATED
ACCEPT  tcp/80  (外部 — nginx)
ACCEPT  icmp
DROP    all
```

### VM-C2 (Internal) 入站规则
```
ACCEPT  lo
ACCEPT  ESTABLISHED,RELATED
ACCEPT  tcp/389   from 192.168.120.1/32  # LDAP
ACCEPT  tcp/445   from 192.168.120.1/32  # Samba
ACCEPT  tcp/139   from 192.168.120.1/32  # Samba
ACCEPT  tcp/3306  from 192.168.120.1/32  # MySQL
ACCEPT  tcp/80    from 192.168.120.1/32  # Drupal
# SSH BLOCKED from 192.168.120.1
ACCEPT  from 192.168.120.0/24
ACCEPT  icmp
DROP    all
```

## 凭据汇总

| 服务 | 位置 | 用户 | 密码 |
|---|---|---|---|
| CMS Admin | VM-A1 | admin | Admin@Cms2024 |
| CMS Test | VM-A1 | testuser | Test@123456 |
| MySQL root | VM-A2 | root | R00t@Mysql#2024 |
| MySQL cms | VM-A2 | cmsuser | Cm5Us3r@2024! |
| SSH operator | VM-A2 | operator | 0p3rat0r@GDJ |
| Monitor | VM-B1 | admin | admin123 |
| PostgreSQL monitor | VM-B2 | monitor | M0n1t0r@DB#2024 |
| PostgreSQL monitor_ro | VM-B2 | monitor_ro | M0n1t0rR0@2024! |
| RuoYi admin | VM-C1 | admin | Admin@OA2024 |
| RuoYi test | VM-C1 | test | Test@123456 |
| MySQL oa | VM-C1/C2 | oauser | Oaus3r@2024! |
| LDAP admin | VM-C2 | cn=admin | Ldap@Admin#2024 |
| LDAP operator | VM-C2 | cn=operator | 0p3rat0r@GDJ |
| SSH operator | VM-C2 | operator | 0p3rat0r@GDJ |
| Drupal admin | VM-C2 | admin | 0p3rat0r@GDJ |

## 提权向量

| VM | 用户 | 命令 | 类型 |
|---|---|---|---|
| VM-A1 | operator | `/usr/bin/find` SUID | SUID binary |
| VM-A2 | operator | `/opt/confluence_health_check.sh` chmod 777 + root cron | Writable cron |
| VM-B1 | www-data | `/opt/monitor/cleanup.sh` chmod 777 + root cron | Writable cron |
| VM-B2 | operator | `/opt/jenkins_backup.sh` chmod 777 + root cron | Writable cron |
| VM-C1 | tomcat | `sudo /usr/bin/tee` NOPASSWD | sudo tee |
| VM-C2 | operator | `sudo /usr/bin/find` NOPASSWD | sudo find |
