package com.ujcms.cms.core.web.support;

import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import javax.servlet.*;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * 解决 /cp/api/** 转发到 /api/** 的问题
 * 前端Vue打包后的API路径使用相对路径 ../api/backend/...
 * 但 /cp/ 页面发出的请求会变成 /cp/api/backend/...
 * 此Filter将 /cp/api/** 转发到 /api/**
 */
@Component
@Order(Integer.MIN_VALUE)
public class CpApiRedirectFilter implements Filter {

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest req = (HttpServletRequest) request;
        HttpServletResponse resp = (HttpServletResponse) response;

        String path = req.getServletPath();
        if (path.startsWith("/cp/api/")) {
            String newPath = path.replaceFirst("^/cp", "");
            req.getRequestDispatcher(newPath).forward(req, resp);
            return;
        }
        chain.doFilter(request, response);
    }
}
