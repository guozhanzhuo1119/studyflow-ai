package com.studyflow.dto;

import java.time.LocalDateTime;

/**
 * 对齐旧版 routers/knowledge_points.py 的 _serialize。
 */
public record KnowledgePointView(
        String id,
        String chapterId,
        String chapterName,
        String subjectId,
        String subjectName,
        String name,
        long problemCount,
        LocalDateTime createdAt
) {
}
