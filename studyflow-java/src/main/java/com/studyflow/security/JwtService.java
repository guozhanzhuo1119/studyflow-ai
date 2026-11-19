package com.studyflow.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/**
 * 与旧版 app/services/auth.py 保持兼容：
 * HS256、claims 为 user_id / username / exp，默认密钥与有效期一致。
 */
@Component
public class JwtService {

    private final SecretKey key;
    private final long expireMinutes;

    public JwtService(@Value("${studyflow.jwt.secret}") String secret,
                      @Value("${studyflow.jwt.expire-minutes:10080}") long expireMinutes) {
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.expireMinutes = expireMinutes;
    }

    public String createToken(String userId, String username) {
        long now = System.currentTimeMillis();
        return Jwts.builder()
                .claim("user_id", userId)
                .claim("username", username)
                .expiration(new Date(now + expireMinutes * 60_000L))
                .signWith(key)
                .compact();
    }

    public Claims parse(String token) {
        try {
            return Jwts.parser()
                    .verifyWith(key)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (JwtException | IllegalArgumentException ex) {
            return null;
        }
    }
}
