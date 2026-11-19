package com.studyflow.dto;

import java.util.List;

/**
 * 对齐旧版 POST /api/problems/search 响应：{query, total, results}。
 */
public record ProblemSearchResponse(
        String query,
        int total,
        List<ProblemSearchResult> results
) {
}
