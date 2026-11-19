package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.studyflow.common.ApiException;
import com.studyflow.dto.LoginRequest;
import com.studyflow.dto.MeResponse;
import com.studyflow.dto.RegisterRequest;
import com.studyflow.dto.TokenResponse;
import com.studyflow.entity.User;
import com.studyflow.mapper.UserMapper;
import com.studyflow.security.JwtService;
import io.jsonwebtoken.Claims;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.HexFormat;
import java.util.UUID;

@Service
public class AuthService {

    private final UserMapper userMapper;
    private final JwtService jwtService;

    public AuthService(UserMapper userMapper, JwtService jwtService) {
        this.userMapper = userMapper;
        this.jwtService = jwtService;
    }

    public TokenResponse register(RegisterRequest request) {
        Long existing = userMapper.selectCount(
                new LambdaQueryWrapper<User>().eq(User::getUsername, request.username()));
        if (existing != null && existing > 0) {
            throw new ApiException(400, "用户名已存在");
        }

        User user = new User();
        user.setId("user-" + shortUuid());
        user.setUsername(request.username());
        // 旧库与旧接口使用 SHA-256，保持一致，避免既有账号无法登录
        user.setPasswordHash(sha256Hex(request.password()));
        user.setEmail(request.email());
        user.setCreatedAt(LocalDateTime.now());

        try {
            userMapper.insert(user);
        } catch (DuplicateKeyException ex) {
            throw new ApiException(400, "用户名已存在");
        }
        return tokenResponse(user);
    }

    public TokenResponse login(LoginRequest request) {
        User user = userMapper.selectOne(
                new LambdaQueryWrapper<User>().eq(User::getUsername, request.username()));
        if (user == null || !passwordMatches(request.password(), user.getPasswordHash())) {
            throw new ApiException(401, "用户名或密码错误");
        }
        return tokenResponse(user);
    }

    public MeResponse me(String token) {
        Claims claims = jwtService.parse(token);
        if (claims == null) {
            throw new ApiException(401, "无效的 token");
        }
        Object userIdClaim = claims.get("user_id");
        String userId = userIdClaim == null ? null : String.valueOf(userIdClaim);
        User user = userId == null ? null : userMapper.selectById(userId);
        if (user == null) {
            throw new ApiException(404, "用户不存在");
        }
        return new MeResponse(user.getId(), user.getUsername(), user.getEmail());
    }

    private TokenResponse tokenResponse(User user) {
        String token = jwtService.createToken(user.getId(), user.getUsername());
        return new TokenResponse(token, "bearer", user.getId(), user.getUsername());
    }

    private static boolean passwordMatches(String plainPassword, String storedHash) {
        if (storedHash == null) {
            return false;
        }
        byte[] expected = sha256Hex(plainPassword).getBytes(StandardCharsets.US_ASCII);
        byte[] actual = storedHash.getBytes(StandardCharsets.US_ASCII);
        return MessageDigest.isEqual(expected, actual);
    }

    private static String sha256Hex(String text) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("JVM 不支持 SHA-256", ex);
        }
    }

    private static String shortUuid() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 8);
    }
}
