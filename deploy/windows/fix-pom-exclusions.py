#!/usr/bin/env python3
"""Fix root pom.xml to exclude Spring Boot 4.x modules from springdoc"""
import paramiko

host = '192.168.101.140'
user = 'gdadmin'
pwd = 'Gdadmin@123'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)

# Read current root pom.xml
sftp = c.open_sftp()
with sftp.open('/opt/oa-app/ruoyi/pom.xml', 'r') as f:
    pom = f.read().decode('utf-8')
sftp.close()
print(f"Read pom.xml: {len(pom)} chars")

# Replace the springdoc dependencyManagement entry to add exclusions
old = """            <!-- spring-doc -->
            <dependency>
                <groupId>org.springdoc</groupId>
                <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
                <version>${springdoc.version}</version>
            </dependency>"""

new = """            <!-- spring-doc -->
            <dependency>
                <groupId>org.springdoc</groupId>
                <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
                <version>${springdoc.version}</version>
                <exclusions>
                    <!-- Exclude Spring Boot 4.x modules not in Spring Boot 3 BOM -->
                    <exclusion>
                        <groupId>org.springframework.boot</groupId>
                        <artifactId>spring-boot-webmvc</artifactId>
                    </exclusion>
                    <exclusion>
                        <groupId>org.springframework.boot</groupId>
                        <artifactId>spring-boot-web-server</artifactId>
                    </exclusion>
                    <exclusion>
                        <groupId>org.springframework.boot</groupId>
                        <artifactId>spring-boot-validation</artifactId>
                    </exclusion>
                    <exclusion>
                        <groupId>org.springframework.boot</groupId>
                        <artifactId>spring-boot-jackson</artifactId>
                    </exclusion>
                    <exclusion>
                        <groupId>org.springframework.boot</groupId>
                        <artifactId>spring-boot-servlet</artifactId>
                    </exclusion>
                    <exclusion>
                        <groupId>org.springframework.boot</groupId>
                        <artifactId>spring-boot-http-converter</artifactId>
                    </exclusion>
                </exclusions>
            </dependency>"""

if old in pom:
    pom = pom.replace(old, new)
    print("Replacement applied")
else:
    print("OLD pattern NOT FOUND, checking content...")
    idx = pom.find('spring-doc')
    if idx >= 0:
        print("Found at index", idx, ":", pom[idx:idx+200])

# Write back
sftp = c.open_sftp()
with sftp.open('/opt/oa-app/ruoyi/pom.xml', 'w') as f:
    f.write(pom.encode('utf-8'))
sftp.close()
print("Root pom.xml updated with exclusions")

# Verify
stdin, stdout, stderr = c.exec_command('grep -A30 "spring-doc" /opt/oa-app/ruoyi/pom.xml | head -35')
print("Verification:")
print(stdout.read().decode())

c.close()
