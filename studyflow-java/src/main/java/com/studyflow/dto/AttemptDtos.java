package com.studyflow.dto;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public final class AttemptDtos {

    private AttemptDtos() {
    }

    public record CreateRequest(
            String targetType,
            String targetId,
            String result,
            List<String> userAnswers,
            Integer durationSec,
            String errorReason,
            String errorType,
            String source,
            String clientToken
    ) {
    }

    public record Stats(
            int total,
            int correct,
            int wrong,
            int giveup,
            double accuracy
    ) {
    }

    public record OverviewResponse(Map<String, Stats> stats) {
    }

    public record HistoryResponse(Stats stats, List<AttemptHistoryItem> attempts) {
    }

    public record AttemptHistoryItem(
            Long id,
            String result,
            Integer durationSec,
            String errorReason,
            String source,
            LocalDateTime createdAt
    ) {
    }
}
