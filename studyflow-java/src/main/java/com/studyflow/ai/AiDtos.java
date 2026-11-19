package com.studyflow.ai;

import java.util.List;

/**
 * Python /ai/** 的请求与响应结构。
 * Java 侧字段 camelCase，由全局 SNAKE_CASE 与 Python 的 snake_case 自动互转。
 */
public final class AiDtos {

    private AiDtos() {
    }

    public record Envelope<T>(Boolean ok, T data, Error error) {
    }

    public record Error(String code, String message) {
    }

    // ---------- 出题 ----------

    public record GenerateRequest(
            String chapterTitle,
            String chapterContent,
            int count,
            int difficulty,
            List<String> existingTitles
    ) {
    }

    public record GenerateData(
            List<Question> questions,
            int dropped,
            List<String> dropReasons
    ) {
    }

    public record Question(
            String title,
            List<String> options,
            String answer,
            String explanation,
            String knowledgePoint
    ) {
    }

    // ---------- 教材解析 ----------

    public record ParseRequest(
            String filename,
            String contentBase64,
            String text,
            String title
    ) {
    }

    public record ParseData(
            String title,
            String fileType,
            Integer pageCount,
            Integer charCount,
            String quality,
            List<Chunk> chunks,
            List<OutlineItem> outline,
            List<String> warnings
    ) {
    }

    public record Chunk(
            Integer pageNo,
            Integer seq,
            String content,
            Integer charCount
    ) {
    }

    public record OutlineItem(
            String name,
            Integer startPage,
            Integer endPage,
            Integer pageCount,
            Integer chunkCount
    ) {
    }

    // ---------- 变式题 ----------

    public record VariantRequest(
            String stem,
            List<String> options,
            String answer,
            String explanation,
            int count,
            Hierarchy hierarchy,
            String source,
            String tags
    ) {
    }

    public record Hierarchy(
            String subjectName,
            String chapterName,
            String knowledgePointName
    ) {
    }

    public record VariantData(
            List<VariantItem> variants,
            int dropped
    ) {
    }

    public record VariantItem(
            String title,
            String difficulty,
            String link,
            String reason
    ) {
    }

    // ---------- 聊天 ----------

    public record ChatRequest(
            String persona,
            ChatQuestion question,
            List<ChatHistoryItem> history,
            String message
    ) {
    }

    public record ChatQuestion(
            String title,
            List<String> options,
            String userAnswer,
            String correctAnswer,
            String explanation
    ) {
    }

    public record ChatHistoryItem(
            String role,
            String content
    ) {
    }

    public record ChatData(String reply) {
    }
}
