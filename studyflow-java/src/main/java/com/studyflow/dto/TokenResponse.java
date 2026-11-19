package com.studyflow.dto;

/**
 * 登录/注册响应，字段名由全局 SNAKE_CASE 转成：
 * access_token / token_type / user_id / username
 */
public record TokenResponse(
        String accessToken,
        String tokenType,
        String userId,
        String username
) {
}
