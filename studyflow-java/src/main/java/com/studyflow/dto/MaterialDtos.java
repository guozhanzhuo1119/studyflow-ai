package com.studyflow.dto;

import com.studyflow.ai.AiDtos;

import java.time.LocalDateTime;
import java.util.List;

public final class MaterialDtos {

    private MaterialDtos() {
    }

    public record MaterialView(
            String id,
            String title,
            String subjectId,
            String fileName,
            String fileType,
            Integer pageCount,
            Integer charCount,
            String quality,
            LocalDateTime createdAt
    ) {
    }

    /** 旧版 upload 响应：_serialize 的全部字段 + warning。 */
    public record MaterialUploadView(
            String id,
            String title,
            String subjectId,
            String fileName,
            String fileType,
            Integer pageCount,
            Integer charCount,
            String quality,
            LocalDateTime createdAt,
            String warning
    ) {
    }

    public record OutlineChapterView(
            String name,
            Integer startPage,
            Integer endPage,
            Integer pageCount,
            Integer chunkCount
    ) {
    }

    public record OutlineResponse(
            MaterialView material,
            List<OutlineChapterView> chapters,
            List<String> warnings
    ) {
    }

    public record OutlineConfirmRequest(
            String subjectId,
            String subjectName,
            List<OutlineConfirmChapter> chapters
    ) {
    }

    public record OutlineConfirmChapter(
            String name,
            Integer startPage,
            Integer endPage
    ) {
    }

    public record ConfirmResponse(
            String subjectId,
            String subjectName,
            boolean subjectCreated,
            List<CreatedChapterView> created,
            List<SkippedChapterView> skipped
    ) {
    }

    public record CreatedChapterView(
            String id,
            String name,
            String subjectId,
            Integer orderNum,
            Integer startPage,
            Integer endPage
    ) {
    }

    public record SkippedChapterView(
            String name,
            String reason
    ) {
    }

    public record ChunksResponse(
            MaterialView material,
            List<ChunkView> chunks
    ) {
    }

    public record ChunkView(
            Integer pageNo,
            Integer seq,
            String content
    ) {
    }

    /** ai_jobs.result_json（parse-material）。 */
    public record OutlineDraft(
            List<AiDtos.OutlineItem> chapters,
            List<String> warnings
    ) {
    }
}
