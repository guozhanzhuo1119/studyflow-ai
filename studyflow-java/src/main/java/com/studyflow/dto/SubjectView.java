package com.studyflow.dto;

import java.time.LocalDateTime;

/**
 * 对齐旧版 routers/subjects.py 的 _serialize：
 * id / name / description / chapter_count / created_at
 */
public record SubjectView(
        String id,
        String name,
        String description,
        long chapterCount,
        LocalDateTime createdAt
) {
}
