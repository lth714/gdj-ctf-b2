#!/bin/bash
# VM-B1 DMZ — Flask Monitor Dashboard + Nginx
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=== Fix DNS ==="
echo "nameserver 114.114.114.114" > /etc/resolv.conf
echo "nameserver 223.5.5.5" >> /etc/resolv.conf

echo "=== Fix apt source (aliyun) ==="
sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
apt update

echo "=== Install packages ==="
apt install -y nginx python3 python3-pip openssh-server curl wget netcat-openbsd iptables-persistent 2>&1 | tail -3

echo "=== Install Python deps ==="
python3 -m pip install flask gunicorn requests 2>&1 | tail -3

echo "=== Deploy Monitor Dashboard ==="
mkdir -p /opt/monitor/logs /opt/configs
cat > /opt/monitor/app.py << 'PYEOF'
"""广电网络监控仪表盘 — Flask application with intentional SSRF vulnerability."""
from flask import Flask, render_template_string, request, redirect, url_for, make_response, jsonify
import requests
import hashlib
import time

app = Flask(__name__)
app.secret_key = 'GDJ_monitor_secret_2024'

# Hardcoded users (weak password: admin/admin123)
USERS = {
    'admin': {'password': '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'role': 'viewer'},
    'operator': {'password': 'ecbcd5897f108cd4b38ba42b73e54c19a4399c71b66f124f9d0718f9de4d1a98', 'role': 'admin'},
}

# Simulated monitoring data
NODES = {
    '播出服务器-01': {'status': 'online', 'cpu': 45, 'mem': 62, 'uptime': '15d 3h'},
    '播出服务器-02': {'status': 'online', 'cpu': 32, 'mem': 48, 'uptime': '7d 12h'},
    '编码器-01': {'status': 'online', 'cpu': 78, 'mem': 85, 'uptime': '30d 1h'},
    '编码器-02': {'status': 'warning', 'cpu': 91, 'mem': 73, 'uptime': '3d 8h'},
    '发射台-主': {'status': 'online', 'cpu': 22, 'mem': 35, 'uptime': '60d 5h'},
    '发射台-备': {'status': 'offline', 'cpu': 0, 'mem': 0, 'uptime': '-'},
    '信号中继-A': {'status': 'online', 'cpu': 55, 'mem': 67, 'uptime': '22d 8h'},
    '信号中继-B': {'status': 'online', 'cpu': 41, 'mem': 51, 'uptime': '22d 8h'},
}

PAGE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>广电网络监控系统</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:"Microsoft YaHei",Arial,sans-serif;background:#0f1923;color:#d1d8e0}
header{background:#1a2732;padding:0 20px;display:flex;justify-content:space-between;align-items:center;height:52px;border-bottom:2px solid #2980b9}
header .logo{font-size:18px;font-weight:bold;color:#3498db}
header .user{font-size:13px;color:#7f8c8d}
nav{background:#15202b;padding:10px 20px;border-bottom:1px solid #1e2d3a}
nav a{color:#7f8c8d;text-decoration:none;margin-right:20px;font-size:14px}
nav a:hover{color:#3498db}
nav a.active{color:#3498db;border-bottom:2px solid #3498db;padding-bottom:6px}
.container{max-width:1400px;margin:20px auto;padding:0 20px}
.card{background:#17242d;border-radius:6px;padding:20px;margin-bottom:20px;border:1px solid #1e2d3a}
.card h2{font-size:16px;color:#3498db;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #1e2d3a}
table{width:100%;border-collapse:collapse}
th,td{padding:10px 14px;text-align:left;border-bottom:1px solid #1e2d3a;font-size:13px}
th{background:#1a2732;color:#bdc3c7;font-weight:600}
tr:hover{background:#1a2732}
.status-online{color:#27ae60}
.status-warning{color:#f39c12}
.status-offline{color:#c0392b}
.btn{padding:8px 16px;border:none;border-radius:4px;cursor:pointer;font-size:13px;text-decoration:none}
.btn-primary{background:#2980b9;color:#fff}
.btn-primary:hover{background:#3498db}
.btn-danger{background:#c0392b;color:#fff}
input,select{padding:8px 12px;border:1px solid #34495e;background:#0f1923;color:#d1d8e0;border-radius:4px;font-size:13px;margin-bottom:8px;width:100%}
label{font-size:13px;color:#7f8c8d;display:block;margin-bottom:4px}
.alert{padding:12px;border-radius:4px;margin-bottom:12px;font-size:13px}
.alert-error{background:#3d1a1a;border:1px solid #c0392b;color:#e74c3c}
.alert-success{background:#1a3d2a;border:1px solid #27ae60;color:#2ecc71}
.alert-info{background:#1a2a3d;border:1px solid #2980b9;color:#3498db}
pre{background:#0a1219;padding:12px;border-radius:4px;overflow-x:auto;font-size:12px;color:#bdc3c7;border:1px solid #1e2d3a}
.row{display:flex;gap:20px}
.col{flex:1}
.metric{text-align:center;padding:20px}
.metric .value{font-size:36px;font-weight:bold}
.metric .label{font-size:12px;color:#7f8c8d}
</style>
</head>
<body>
<header>
<div class="logo">广电网络监控系统 v3.2</div>
<div class="user">{% if user %}当前用户: {{ user }} ({{ role }}) | <a href="?logout=1" style="color:#2980b9">退出</a>{% else %}未登录{% endif %}</div>
</header>
<nav>
<a href="?" class="{% if page == "dashboard" %}active{% endif %}">仪表盘</a>
<a href="?page=probe" class="{% if page == "probe" %}active{% endif %}">网络探测</a>
{% if role == "admin" %}<a href="?page=admin" class="{% if page == "admin" %}active{% endif %}">管理面板</a>{% endif %}
</nav>
<div class="container">
{{ content|safe }}
</div>
</body>
</html>'''

LOGIN_PAGE = '''
<div class="card" style="max-width:400px;margin:60px auto">
<h2>系统登录</h2>
<form method="post">
<label>用户名</label><input type="text" name="username" placeholder="用户名">
<label>密码</label><input type="password" name="password" placeholder="密码">
<button type="submit" class="btn btn-primary" style="width:100%;margin-top:8px">登录</button>
</form>
</div>'''

DASHBOARD = '''
<div class="card"><h2>系统概览</h2>
<div class="row">
<div class="col"><div class="card metric"><div class="value" style="color:#27ae60">8</div><div class="label">监控节点总数</div></div></div>
<div class="col"><div class="card metric"><div class="value" style="color:#27ae60">6</div><div class="label">在线节点</div></div></div>
<div class="col"><div class="card metric"><div class="value" style="color:#f39c12">1</div><div class="label">告警节点</div></div></div>
<div class="col"><div class="card metric"><div class="value" style="color:#c0392b">1</div><div class="label">离线节点</div></div></div>
</div></div>
<div class="card"><h2>节点列表</h2>
<table>
<tr><th>节点名称</th><th>状态</th><th>CPU</th><th>内存</th><th>运行时间</th></tr>
{% for name, info in nodes.items() %}
<tr>
<td>{{ name }}</td>
<td class="status-{{ info.status }}">{% if info.status == "online" %}● 在线{% elif info.status == "warning" %}▲ 告警{% else %}■ 离线{% endif %}</td>
<td>{{ info.cpu }}%</td><td>{{ info.mem }}%</td><td>{{ info.uptime }}</td>
</tr>
{% endfor %}
</table></div>'''

PROBE_PAGE = '''
<div class="card"><h2>网络连通性探测</h2>
<p style="font-size:13px;color:#7f8c8d;margin-bottom:16px">检测目标节点或服务的网络连通状态</p>
<form method="get" action="?page=probe">
<input type="hidden" name="page" value="probe">
<label>目标地址 (IP或URL)</label>
<input type="text" name="target" placeholder="例如: 192.168.1.1 或 http://192.168.110.2:8080/api/health" value="{{ target }}">
<button type="submit" class="btn btn-primary">探测</button>
</form>
{% if probe_result %}<pre>{{ probe_result }}</pre>{% endif %}
{% if probe_error %}<div class="alert alert-error">{{ probe_error }}</div>{% endif %}
</div>'''

ADMIN_PAGE = '''
<div class="card"><h2>管理员控制面板</h2>
<div class="alert alert-success">当前登录: <strong>{{ user }}</strong> — 管理员权限</div>
</div>
<div class="card"><h2>系统管理</h2>
<table>
<tr><th>功能</th><th>说明</th><th>操作</th></tr>
<tr><td>节点管理</td><td>添加/删除监控节点</td><td><a href="#" class="btn btn-primary">管理</a></td></tr>
<tr><td>告警配置</td><td>配置告警阈值和通知</td><td><a href="#" class="btn btn-primary">配置</a></td></tr>
<tr><td>数据导出</td><td>导出监控历史数据</td><td><a href="#" class="btn btn-primary">导出</a></td></tr>
<tr><td>系统设置</td><td>全局参数配置</td><td><a href="#" class="btn btn-primary">设置</a></td></tr>
</table></div>'''


def check_auth():
    """Simple session-like auth via cookie (weak)."""
    username = request.cookies.get('auth_user')
    role = request.cookies.get('auth_role')
    if username and role:
        return username, role
    return None, None


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.args.get('logout'):
        resp = make_response(redirect(url_for('index')))
        resp.delete_cookie('auth_user')
        resp.delete_cookie('auth_role')
        return resp

    user, role = check_auth()

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        pwhash = hashlib.sha256(password.encode()).hexdigest()

        if username in USERS and USERS[username]['password'] == pwhash:
            role = USERS[username]['role']
            resp = make_response(redirect(url_for('index')))
            resp.set_cookie('auth_user', username)
            resp.set_cookie('auth_role', role)
            return resp
        else:
            content = '<div class="alert alert-error">用户名或密码错误</div>' + LOGIN_PAGE
            return render_template_string(PAGE, user=None, role=None, page='login', content=content)

    if not user:
        return render_template_string(PAGE, user=None, role=None, page='login', content=LOGIN_PAGE)

    page = request.args.get('page', 'dashboard')
    content = ''
    probe_result = ''
    probe_error = ''
    target = ''

    if page == 'probe':
        target = request.args.get('target', '')
        if target:
            try:
                # VULNERABLE: SSRF — no URL validation on target parameter
                r = requests.get(target, timeout=10, allow_redirects=False)
                probe_result = f'HTTP {r.status_code}\n\n{r.text[:2000]}'
            except requests.exceptions.SSLError as e:
                probe_error = f'SSL错误: {str(e)}'
            except requests.exceptions.ConnectionError as e:
                probe_error = f'连接失败: {str(e)}'
            except Exception as e:
                probe_error = f'探测异常: {str(e)}'

        content = render_template_string(
            PROBE_PAGE, target=target, probe_result=probe_result, probe_error=probe_error
        )

    elif page == 'admin':
        if role != 'admin':
            content = '<div class="alert alert-error">权限不足。需要管理员权限。</div>'
        else:
            content = render_template_string(ADMIN_PAGE, user=user)

    else:
        content = render_template_string(DASHBOARD, nodes=NODES)

    return render_template_string(PAGE, user=user, role=role, page=page, content=content)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
PYEOF

chown -R www-data:www-data /opt/monitor

echo "=== Monitor systemd service ==="
cat > /etc/systemd/system/monitor-dashboard.service << 'EOF'
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
EOF

systemctl daemon-reload
systemctl enable monitor-dashboard --now
echo "Monitor: $(systemctl is-active monitor-dashboard)"

echo "=== Nginx reverse proxy ==="
cat > /etc/nginx/sites-available/monitor.conf << 'EOF'
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

ln -sf /etc/nginx/sites-available/monitor.conf /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/default.old
nginx -t && systemctl restart nginx
echo "Nginx: $(systemctl is-active nginx)"

echo "=== Cron privesc vector ==="
cat > /opt/monitor/cleanup.sh << 'EOF'
#!/bin/bash
# Monitor data cleanup script — runs periodically
find /opt/monitor/logs -name "*.old" -mtime +7 -delete 2>/dev/null
EOF
chmod 777 /opt/monitor/cleanup.sh
echo "*/5 * * * * root /opt/monitor/cleanup.sh" > /etc/cron.d/monitor-cleanup

echo "=== API config file (credential bait for B-4/B-5) ==="
cat > /opt/configs/api_config.yaml << 'EOF'
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
EOF
chmod 644 /opt/configs/api_config.yaml

echo "=== Create operator user ==="
useradd -m -s /bin/bash operator 2>/dev/null || true
echo 'operator:0p3rat0r@GDJ' | chpasswd
usermod -aG sudo operator
echo "operator: $(id operator 2>&1)"

echo "=== SSH config ==="
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config 2>/dev/null || true
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config 2>/dev/null || true
systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true

echo "=== iptables DMZ ==="
mkdir -p /etc/iptables
cat > /etc/iptables/rules.v4 << 'IPTEOF'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p tcp --dport 80 -j ACCEPT
-A INPUT -p icmp -j ACCEPT
COMMIT
IPTEOF

iptables-restore < /etc/iptables/rules.v4

cat > /etc/rc.local << 'EOF'
#!/bin/bash
/sbin/iptables-restore < /etc/iptables/rules.v4
exit 0
EOF
chmod +x /etc/rc.local

echo ""
echo "=== VERIFICATION ==="
echo "Nginx: $(systemctl is-active nginx)"
echo "Monitor: $(systemctl is-active monitor-dashboard)"
echo "operator: $(id operator 2>&1)"
echo "iptables: $(iptables -L INPUT -n | head -1)"
echo "Port 80: $(ss -tlnp | grep ':80 ' | wc -l) listening"
echo "Port 5000: $(ss -tlnp | grep ':5000 ' | wc -l) listening"
echo ""
echo "[✓] VM-B1 setup complete."
echo "    Monitor: http://192.168.100.1/"
echo "    SSH:     operator@192.168.101.134 (0p3rat0r@GDJ)"
echo "    Admin:   admin / admin123"
