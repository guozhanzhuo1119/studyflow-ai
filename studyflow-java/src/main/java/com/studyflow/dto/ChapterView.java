package com.studyflow.dto;

import java.time.LocalDateTime;

/**
 * 对齐旧版 routers/chapters.py 的 _serialize。
 */
public record ChapterView(
        String id,
        String subjectId,
        String subjectName,
        String name,
        Integer orderNum,
        long knowledgePointCount,
        LocalDateTime createdAt
) {
}
