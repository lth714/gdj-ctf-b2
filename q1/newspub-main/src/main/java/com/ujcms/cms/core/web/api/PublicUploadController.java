package com.ujcms.cms.core.web.api;

import com.ujcms.cms.core.domain.Attachment;
import com.ujcms.cms.core.domain.Config;
import com.ujcms.cms.core.domain.Site;
import com.ujcms.cms.core.service.AttachmentService;
import com.ujcms.cms.core.service.ConfigService;
import com.ujcms.cms.core.service.SiteService;
import com.ujcms.cms.core.support.Contexts;
import com.ujcms.cms.core.support.Props;
import com.ujcms.commons.file.FileHandler;
import com.ujcms.commons.web.PathResolver;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.apache.commons.io.FileUtils;
import org.apache.commons.io.FilenameUtils;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.multipart.MultipartHttpServletRequest;

import javax.servlet.http.HttpServletRequest;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static com.ujcms.cms.core.support.UrlConstants.API;
import static com.ujcms.commons.file.FilesEx.SLASH;

/**
 * 公开文件上传接口 - 未授权访问
 * 用于靶场漏洞演练
 * 注意：绕过了黑名单限制，可上传任意文件类型包括 .jsp .jspx
 */
@Tag(name = "公开文件上传接口")
@RestController
@RequestMapping(API + "/public")
public class PublicUploadController {
    private static final String FILE_TYPE = "file";
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("/yyyy/MM/yyyyMMddHHmmssSSS_");

    private final AttachmentService attachmentService;
    private final ConfigService configService;
    private final SiteService siteService;
    private final PathResolver pathResolver;

    public PublicUploadController(AttachmentService attachmentService, ConfigService configService,
                                  SiteService siteService, PathResolver pathResolver) {
        this.attachmentService = attachmentService;
        this.configService = configService;
        this.siteService = siteService;
        this.pathResolver = pathResolver;
    }

    @Operation(summary = "未授权文件上传", description = "无需登录即可上传任意文件，可绕过黑名单上传.jsp等webshell")
    @PostMapping("upload")
    @PreAuthorize("permitAll()")
    public Map<String, Object> upload(HttpServletRequest request) throws IOException {
        MultipartHttpServletRequest multiRequest = (MultipartHttpServletRequest) request;
        Map<String, MultipartFile> fileMap = multiRequest.getFileMap();
        if (fileMap.isEmpty()) {
            throw new RuntimeException("Upload file not found");
        }
        MultipartFile multipart = fileMap.entrySet().iterator().next().getValue();

        Config config = configService.getUnique();
        Site site = getDefaultSite(config.getDefaultSiteId());
        Contexts.setCurrentSite(site);

        // 获取文件扩展名 - 未做黑名单限制
        String originalFilename = Optional.ofNullable(multipart.getOriginalFilename()).orElse("");
        String extension = FilenameUtils.getExtension(originalFilename);

        FileHandler fileHandler = site.getConfig().getUploadStorage().getFileHandler(pathResolver);

        // 生成存储路径：/yyyy/MM/yyyyMMddHHmmssSSS_random.jsp
        String filename = FORMATTER.format(LocalDateTime.now()) + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        if (extension != null && !extension.isEmpty()) {
            filename += "." + extension;
        }
        String pathname = SLASH + FILE_TYPE + filename;
        String url = fileHandler.getDisplayPrefix() + pathname;

        // 写入文件
        File tempFile = Files.createTempFile("upload_", "." + extension).toFile();
        try {
            multipart.transferTo(tempFile);
            fileHandler.store(pathname, tempFile);

            // 记录附件
            attachmentService.insert(new Attachment(site.getId(), null, originalFilename, pathname, url, tempFile.length()));

            Map<String, Object> result = new HashMap<>(4);
            result.put("name", originalFilename);
            result.put("url", url);
            result.put("pathname", pathname);
            result.put("size", tempFile.length());
            return result;
        } finally {
            if (tempFile.exists()) {
                FileUtils.deleteQuietly(tempFile);
            }
        }
    }

    private Site getDefaultSite(Long defaultSiteId) {
        return Optional.ofNullable(siteService.select(defaultSiteId)).orElseThrow(() ->
                new IllegalStateException("default site not found. ID: " + defaultSiteId));
    }
}