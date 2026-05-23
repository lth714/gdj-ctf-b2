#!/bin/bash
cd /opt
rm -rf oa-app RuoYi-v4.8.3 /tmp/ruoyi.zip
curl -L -o /tmp/ruoyi.zip "https://gitee.com/y_project/RuoYi/repository/archive/v4.8.3.zip"
unzip -q /tmp/ruoyi.zip -d /opt/
mv /opt/RuoYi* /opt/oa-app
ls /opt/oa-app/pom.xml && echo "OK" || echo "FAIL"
