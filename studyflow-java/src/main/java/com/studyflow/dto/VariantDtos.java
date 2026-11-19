package com.studyflow.dto;

import com.studyflow.ai.AiDtos;

import java.time.LocalDateTime;
import java.util.List;

public final class VariantDtos {

    private VariantDtos() {
    }

    public record RecommendRequest(String problemId, Integer count) {

        public int effectiveCount() {
            return count == null ? 5 : count;
        }
    }

    public record RecommendResponse(
            String problemId,
            String problemTitle,
            List<AiDtos.VariantItem> recommendations
    ) {
    }

    public record VariantCreateRequest(
            String problemId,
            String title,
            String content,
            String difficulty,
            String link,
            String reason
    ) {
    }

    public record SaveFromRecommendationRequest(
            String problemId,
            List<VariantSaveItem> recommendations
    ) {
    }

    public record VariantSaveItem(
            String title,
            String content,
            String difficulty,
            String link,
            String reason
    ) {
    }

    public record SaveVariantsResponse(int saved, List<VariantView> variants) {
    }

    public record VariantView(
            String id,
            String problemId,
            String problemTitle,
            String title,
            String content,
            String difficulty,
            String link,
            String reason,
            String origin,
            LocalDateTime createdAt
    ) {
    }
}
