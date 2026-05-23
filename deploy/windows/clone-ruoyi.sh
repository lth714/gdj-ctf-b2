#!/bin/bash
# Clone original RuoYi 4.8.3 from Gitee
cd /opt
rm -rf oa-app
git clone --depth 1 -b v4.8.3 https://gitee.com/y_project/RuoYi.git oa-app 2>&1
echo "Clone exit: $?"
ls /opt/oa-app/pom.xml && echo "OK" || echo "FAIL"
