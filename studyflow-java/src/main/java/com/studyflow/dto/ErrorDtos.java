package com.studyflow.dto;

import java.time.LocalDateTime;
import java.util.List;

public final class ErrorDtos {

    private ErrorDtos() {
    }

    public record CreateRequest(
            String problemId,
            String problemTitle,
            String topic,
            String motherProblem,
            String errorType,
            String tag,
            String specificBehavior,
            String firstBreakPoint,
            String decompositionSentence,
            String remedyStatus,
            String remedyAction,
            String userNote,
            Boolean reviewed,
            Integer identifyLatencySec
    ) {
    }

    public record UpdateRequest(
            Boolean reviewed,
            String remedyStatus,
            String remedyAction,
            String userNote
    ) {
    }

    public record RecordView(
            Long id,
            String problemId,
            String problemTitle,
            String topic,
            String motherProblem,
            String errorType,
            String errorTypeName,
            String tag,
            String specificBehavior,
            String firstBreakPoint,
            String decompositionSentence,
            String remedyStatus,
            String remedyAction,
            String userNote,
            Boolean reviewed,
            LocalDateTime createdAt,
            Integer identifyLatencySec
    ) {
    }

    public record CreateResponse(RecordView record, boolean suggestSyntaxTag) {
    }

    public record DecideRequest(List<Boolean> answers, String specificBehavior) {
    }

    public record DecideResponse(String errorType, boolean suggestSyntaxTag) {
    }
}
