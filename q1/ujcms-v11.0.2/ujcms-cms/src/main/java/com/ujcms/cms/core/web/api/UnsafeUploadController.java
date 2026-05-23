package com.ujcms.cms.core.web.api;

import com.ujcms.cms.core.domain.Config;
import com.ujcms.cms.core.domain.Site;
import com.ujcms.cms.core.service.AttachmentService;
import com.ujcms.cms.core.service.ConfigService;
import com.ujcms.cms.core.service.SiteService;
import com.ujcms.cms.core.support.Contexts;
import com.ujcms.cms.core.support.Props;
import com.ujcms.cms.core.web.backendapi.AbstractUploadController;
import com.ujcms.common.image.ImageHandler;
import com.ujcms.common.web.PathResolver;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ws.schild.jave.EncoderException;

import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.util.Map;
import java.util.Optional;

import static com.ujcms.cms.core.support.UrlConstants.API;
import static com.ujcms.cms.core.support.UrlConstants.FRONTEND_API;
import static com.ujcms.common.web.Uploads.AVATAR_TYPE;

/**
 * 未授权文件上传漏洞演示接口（靶场专用）
 *
 * @author PONY
 */
@Tag(name = "未授权上传接口", description = "靶场漏洞演示：存在未授权文件上传可直接getshell")
@RestController
@RequestMapping({API + "/upload", FRONTEND_API + "/upload"})
public class UnsafeUploadController extends AbstractUploadController {
    private final ConfigService configService;
    private final SiteService siteService;

    public UnsafeUploadController(AttachmentService attachmentService, ImageHandler imageHandler, PathResolver pathResolver,
                            ConfigService configService, SiteService siteService, Props props) {
        super(attachmentService, imageHandler, pathResolver, props);
        this.configService = configService;
        this.siteService = siteService;
    }

    /**
     * 未授权头像上传（漏洞点：移除了 @PreAuthorize("isAuthenticated()") 注解）
     * 直接可上传任意文件，包括jsp webshell
     * 注意：由于系统配置了 jsp-allowed=true 且清空了扩展名黑名单，jsp文件可成功上传并解析
     */
    @PostMapping("avatar-upload")
    @Operation(summary = "未授权头像上传", description = "漏洞：移除权限校验 + 清空扩展名黑名单 = 可直接上传jsp webshell")
    public Map<String, Object> avatarUpload(HttpServletRequest request) throws EncoderException, IOException {
        Config config = configService.getUnique();
        Site site = getDefaultSite(config.getDefaultSiteId());
        Contexts.setCurrentSite(site);
        // 靶场漏洞：强制设置一个匿名用户ID，避免 NPE
        Long anonymousUserId = 1L;
        Config.Upload upload = config.getUpload();
        // 漏洞点：清空了扩展名黑名单 (ujcms.uploads-extension-blacklist=)
        // 同时 jsp-allowed=true 允许JSP解析
        // 上传路径示例：/uploads/avatar/1/xxx.jsp
        return doUpload(request, upload.getImageLimitByte(), upload.getImageTypes(), AVATAR_TYPE, null, anonymousUserId);
    }

    private Site getDefaultSite(Long defaultSiteId) {
        return Optional.ofNullable(siteService.select(defaultSiteId)).orElseThrow(() ->
                new IllegalStateException("default site not found. ID: " + defaultSiteId));
    }
}