package com.studyflow.controller;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

import java.io.IOException;

/**
 * 前端 dist 由外置目录托管时，把 SPA 的 history 路由 forward 到 index.html。
 * 只匹配前端页面路径；/api/** 与 /uploads/** 不受影响。
 */
@Controller
public class FrontendController {

    @GetMapping({
            "/",
            "/login",
            "/subjects/**",
            "/chapters/**",
            "/knowledge-points/**",
            "/problems/**",
            "/quiz",
            "/chat",
            "/errors",
            "/wrong-book",
            "/materials"
    })
    public void index(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        request.getRequestDispatcher("/index.html").forward(request, response);
    }
}
