package com.studyflow.dto;

import jakarta.validation.constraints.NotBlank;

import java.time.LocalDateTime;
import java.util.List;

public final class ChatDtos {

    private ChatDtos() {
    }

    public record ChatRequest(
            @NotBlank(message = "消息不能为空") String message,
            String sessionId,
            String subjectId,
            String questionId
    ) {
    }

    public record ChatResponse(String reply, String sessionId) {
    }

    public record ChatMessagesResponse(String sessionId, List<ChatMessageView> messages) {
    }

    public record ChatMessageView(String role, String content) {
    }

    public record ChatSessionsResponse(List<ChatSessionView> sessions) {
    }

    public record ChatSessionView(
            String sessionId,
            String title,
            long messageCount,
            LocalDateTime updatedAt
    ) {
    }
}
