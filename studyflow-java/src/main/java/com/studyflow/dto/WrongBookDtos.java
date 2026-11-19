package com.studyflow.dto;

import java.time.LocalDateTime;
import java.util.List;

public final class WrongBookDtos {

    private WrongBookDtos() {
    }

    public record Item(
            Long id,
            String targetType,
            String targetId,
            String title,
            Integer wrongCount,
            Boolean mastered,
            LocalDateTime lastWrongAt,
            LocalDateTime masteredAt,
            String knowledgePointId,
            String knowledgePointName,
            String chapterId,
            String chapterName,
            String subjectId,
            String subjectName
    ) {
    }

    public record ListResponse(List<Item> items, long total, long unmastered) {
    }
}
