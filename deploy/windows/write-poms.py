#!/usr/bin/env python3
"""Write clean pom.xml files to C1 for RuoYi build"""
import paramiko

host = '192.168.101.140'
user = 'gdadmin'
pwd = 'Gdadmin@123'

# Root pom.xml
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

# Admin pom.xml (NO springdoc, WITH freemarker)
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

# Framework pom.xml (fixed artifact names)
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

        <!-- Shiro使用Spring框架 -->
        <dependency>
            <groupId>org.apache.shiro</groupId>
            <artifactId>shiro-spring</artifactId>
            <classifier>jakarta</classifier>
        </dependency>

        <!-- Shiro核心框架 -->
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

        <!-- 验证码 -->
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

        <!-- thymeleaf模板引擎和shiro框架的整合 -->
        <dependency>
            <groupId>com.github.theborakompanioni</groupId>
            <artifactId>thymeleaf-extras-shiro</artifactId>
        </dependency>

        <!-- 获取系统信息 -->
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

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pwd, timeout=10)

sftp = c.open_sftp()

# Write all pom files
files = {
    '/opt/oa-app/ruoyi/pom.xml': ROOT_POM,
    '/opt/oa-app/ruoyi/ruoyi-admin/pom.xml': ADMIN_POM,
    '/opt/oa-app/ruoyi/ruoyi-framework/pom.xml': FRAMEWORK_POM,
    '/opt/oa-app/ruoyi/ruoyi-generator/pom.xml': GENERATOR_POM,
}

for path, content in files.items():
    with sftp.open(path, 'w') as f:
        f.write(content.encode('utf-8'))
    print(f'Written: {path}')

sftp.close()

# Validate
stdin, stdout, stderr = c.exec_command('cd /opt/oa-app/ruoyi && mvn validate 2>&1 | tail -15')
print('Validation:')
print(stdout.read().decode())

c.close()
print('Done!')
