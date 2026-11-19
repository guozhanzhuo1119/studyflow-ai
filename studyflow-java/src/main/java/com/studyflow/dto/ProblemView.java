package com.studyflow.dto;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 对齐旧版 routers/problems.py 的 _serialize。
 * 注意：列表与详情都不下发 answer / explanation。
 */
public record ProblemView(
        String id,
        String title,
        String content,
        String source,
        String tags,
        String type,
        List<Object> options,
        Integer difficulty,
        String status,
        String knowledgePointId,
        String knowledgePointName,
        String chapterId,
        String chapterName,
        String subjectId,
        String subjectName,
        LocalDateTime createdAt
) {
}
