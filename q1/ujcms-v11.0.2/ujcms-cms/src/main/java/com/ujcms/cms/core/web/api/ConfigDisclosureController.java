package com.ujcms.cms.core.web.api;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.util.StreamUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * 配置信息泄露接口（靶场专用）
 *
 * @author PONY
 */
@Tag(name = "配置信息接口", description = "靶场漏洞演示：泄露数据库配置等敏感信息")
@RestController
@RequestMapping("/api")
public class ConfigDisclosureController {

    @Value("${spring.datasource.url}")
    private String datasourceUrl;

    @Value("${spring.datasource.username}")
    private String datasourceUsername;

    @Value("${spring.datasource.password}")
    private String datasourcePassword;

    /**
     * 泄露数据库连接配置
     */
    @GetMapping("db-config")
    @Operation(summary = "数据库配置泄露", description = "漏洞：可直接获取数据库账号密码")
    public String getDbConfig() {
        return "spring.datasource.url: " + datasourceUrl + "\n" +
               "spring.datasource.username: " + datasourceUsername + "\n" +
               "spring.datasource.password: " + datasourcePassword;
    }

    /**
     * 泄露完整配置文件内容
     */
    @GetMapping("app-config")
    @Operation(summary = "应用配置文件泄露", description = "漏洞：可直接获取spring.datasource密码等敏感配置")
    public String getAppConfig() throws IOException {
        Resource resource = new ClassPathResource("application.yaml");
        return StreamUtils.copyToString(resource.getInputStream(), StandardCharsets.UTF_8);
    }
}