package com.studyflow.ai;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.studyflow.common.ApiException;
import com.studyflow.config.AiProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

import java.time.Duration;

/**
 * 访问 studyflow-ai-service 的唯一入口。
 * 统一注入 X-Internal-Token；连接失败 / 5xx 一律抛出 ApiException，不吞异常。
 */
@Component
public class AiClient {

    private static final Logger log = LoggerFactory.getLogger(AiClient.class);

    private final RestClient restClient;
    private final ObjectMapper objectMapper;

    public AiClient(AiProperties properties,
                    ObjectMapper objectMapper,
                    RestClient.Builder restClientBuilder) {
        this.objectMapper = objectMapper;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofSeconds(properties.getConnectTimeoutSeconds()));
        requestFactory.setReadTimeout(Duration.ofSeconds(properties.getReadTimeoutSeconds()));

        // 使用 Spring Boot 自动配置的 Builder，确保复用全局 SNAKE_CASE ObjectMapper
        this.restClient = restClientBuilder
                .baseUrl(properties.getBaseUrl())
                .defaultHeader("X-Internal-Token", properties.getInternalToken())
                .requestFactory(requestFactory)
                .build();

        log.info("AI 服务地址：{}（读超时 {}s）",
                properties.getBaseUrl(), properties.getReadTimeoutSeconds());
    }

    public AiDtos.GenerateData generateQuestions(AiDtos.GenerateRequest request) {
        AiDtos.GenerateData data = post(
                "/ai/generate-questions",
                request,
                new ParameterizedTypeReference<AiDtos.Envelope<AiDtos.GenerateData>>() {
                });
        return requireData(data, "出题");
    }

    public AiDtos.ParseData parseMaterial(AiDtos.ParseRequest request) {
        AiDtos.ParseData data = post(
                "/ai/parse-material",
                request,
                new ParameterizedTypeReference<AiDtos.Envelope<AiDtos.ParseData>>() {
                });
        return requireData(data, "教材解析");
    }

    public AiDtos.VariantData variants(AiDtos.VariantRequest request) {
        AiDtos.VariantData data = post(
                "/ai/variants",
                request,
                new ParameterizedTypeReference<AiDtos.Envelope<AiDtos.VariantData>>() {
                });
        return requireData(data, "变式题推荐");
    }

    public AiDtos.ChatData chat(AiDtos.ChatRequest request) {
        AiDtos.ChatData data = post(
                "/ai/chat",
                request,
                new ParameterizedTypeReference<AiDtos.Envelope<AiDtos.ChatData>>() {
                });
        return requireData(data, "聊天");
    }

    private <T> T post(String path, Object body,
                       ParameterizedTypeReference<AiDtos.Envelope<T>> responseType) {
        try {
            AiDtos.Envelope<T> envelope = restClient.post()
                    .uri(path)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(responseType);

            if (envelope == null) {
                throw new ApiException(502, "AI 服务返回空响应：" + path);
            }
            if (!Boolean.TRUE.equals(envelope.ok())) {
                String message = envelope.error() == null || envelope.error().message() == null
                        ? "未知错误"
                        : envelope.error().message();
                throw new ApiException(502, "AI 服务调用失败：" + message);
            }
            return envelope.data();
        } catch (RestClientResponseException ex) {
            String message = extractErrorMessage(ex.getResponseBodyAsString(), ex.getStatusText());
            log.warn("AI 服务 {} 返回 {}：{}", path, ex.getStatusCode().value(), message);
            // Python 的 401/422 属于 Java 侧配置或入参问题，不把 401 透给前端，避免触发登出
            throw new ApiException(502, "AI 服务调用失败：" + message);
        } catch (ResourceAccessException ex) {
            log.warn("AI 服务不可用（{}）：{}", path, ex.getMessage());
            throw new ApiException(503, "AI 服务不可用，请确认 studyflow-ai-service 已启动");
        } catch (RestClientException ex) {
            log.warn("AI 服务调用异常（{}）：{}", path, ex.getMessage());
            throw new ApiException(502, "AI 服务调用失败：" + ex.getMessage());
        }
    }

    private String extractErrorMessage(String body, String fallback) {
        if (body != null && !body.isBlank()) {
            try {
                AiDtos.Envelope<Object> envelope = objectMapper.readValue(
                        body, new TypeReference<AiDtos.Envelope<Object>>() {
                        });
                if (envelope.error() != null
                        && envelope.error().message() != null
                        && !envelope.error().message().isBlank()) {
                    return envelope.error().message();
                }
            } catch (Exception ignored) {
                // 不是统一错误体，退回原始响应片段
            }
            return body.length() > 300 ? body.substring(0, 300) : body;
        }
        return fallback == null ? "未知错误" : fallback;
    }

    private <T> T requireData(T data, String action) {
        if (data == null) {
            throw new ApiException(502, "AI 服务返回空数据：" + action);
        }
        return data;
    }
}
