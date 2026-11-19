package com.studyflow.dto;

/**
 * 对齐旧版 POST /api/problems/search 请求体：{query, top_k}。
 */
public record ProblemSearchRequest(
        String query,
        Integer topK
) {

    public int effectiveTopK() {
        if (topK == null) {
            return 5;
        }
        return Math.max(0, Math.min(topK, 50));
    }
}
