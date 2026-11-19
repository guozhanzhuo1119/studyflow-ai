package com.studyflow.dto;

/**
 * 对齐旧版 FAISS 检索结果字段（不含 answer / explanation），
 * 本期由 MySQL 关键词检索产生，score 仅为排序用的简单置信度。
 */
public record ProblemSearchResult(
        String id,
        String title,
        String source,
        String tags,
        String knowledgePointId,
        String knowledgePointName,
        String chapterName,
        String subjectName,
        String status,
        double score
) {
}
