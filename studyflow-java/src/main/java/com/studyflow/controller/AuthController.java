package com.studyflow.controller;

import com.studyflow.dto.LoginRequest;
import com.studyflow.dto.MeResponse;
import com.studyflow.dto.RegisterRequest;
import com.studyflow.dto.TokenResponse;
import com.studyflow.service.AuthService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/register")
    public TokenResponse register(@Valid @RequestBody RegisterRequest request) {
        return authService.register(request);
    }

    @PostMapping("/login")
    public TokenResponse login(@Valid @RequestBody LoginRequest request) {
        return authService.login(request);
    }

    /**
     * 前端调用方式为 GET /api/auth/me?token=xxx，必须支持 query 参数。
     */
    @GetMapping("/me")
    public MeResponse me(@RequestParam("token") String token) {
        return authService.me(token);
    }
}
