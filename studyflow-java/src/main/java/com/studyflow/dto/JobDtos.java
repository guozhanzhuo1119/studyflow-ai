package com.studyflow.dto;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;

public final class JobDtos {

    private JobDtos() {
    }

    /** POST /api/chapters/{id}/generate 请求体 */
    public record GenerateRequest(Integer count, Integer difficulty) {

        public int effectiveCount() {
            return count == null ? 5 : count;
        }

        public int effectiveDifficulty() {
            return difficulty == null ? 3 : difficulty;
        }
    }

    public record GenerateJobResponse(String jobId) {
    }

    public record AiJobView(String status, JsonNode result, String error) {
    }

    /** ai_jobs.request_json */
    public record GeneratePayload(String chapterId, int count, int difficulty) {
    }

    /** ai_jobs.result_json（出题成功） */
    public record GenerationResult(
            int generated,
            int dropped,
            long totalInChapter,
            List<String> dropReasons
    ) {
    }
}
