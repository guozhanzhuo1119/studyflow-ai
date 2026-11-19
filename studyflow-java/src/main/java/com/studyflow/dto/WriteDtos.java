package com.studyflow.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public final class WriteDtos {

    private WriteDtos() {
    }

    public record SubjectRequest(String name, String description) {
    }

    public record ChapterRequest(String subjectId, String name, Integer orderNum) {
    }

    public record KnowledgePointRequest(String chapterId, String name) {
    }

    public record ProblemRequest(String title, String content, String source, String tags,
                                 String knowledgePointId) {
    }

    public record DeleteResponse(String message,
                                 @JsonProperty("deletedProblems") long deletedProblems) {
    }

    public record SubjectDeleteResponse(int code,
                                        String message,
                                        @JsonProperty("deletedProblems") long deletedProblems) {
    }
}
