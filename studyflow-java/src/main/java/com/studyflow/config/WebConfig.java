package com.studyflow.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * /uploads/** 静态资源；frontend-dist 配置后占位托管前端打包产物。
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    private static final Logger log = LoggerFactory.getLogger(WebConfig.class);

    private final String uploadsDir;
    private final String frontendDist;

    public WebConfig(@Value("${studyflow.uploads-dir:uploads}") String uploadsDir,
                     @Value("${studyflow.frontend-dist:}") String frontendDist) {
        this.uploadsDir = uploadsDir;
        this.frontendDist = frontendDist;
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        Path uploads = Paths.get(uploadsDir).toAbsolutePath().normalize();
        try {
            Files.createDirectories(uploads);
        } catch (IOException ex) {
            log.warn("无法创建上传目录：{}", uploads, ex);
        }
        registry.addResourceHandler("/uploads/**")
                .addResourceLocations(uploads.toUri().toString());

        if (frontendDist != null && !frontendDist.isBlank()) {
            Path dist = Paths.get(frontendDist).toAbsolutePath().normalize();
            if (Files.isDirectory(dist)) {
                registry.addResourceHandler("/**")
                        .addResourceLocations(dist.toUri().toString());
                log.info("已托管前端打包产物：{}", dist);
            } else {
                log.warn("配置了 frontend-dist 但目录不存在：{}", dist);
            }
        }
    }
}
