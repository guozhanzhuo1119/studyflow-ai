package com.studyflow.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.studyflow.common.ApiException;
import com.studyflow.dto.JobDtos;
import com.studyflow.entity.AiJob;
import com.studyflow.entity.Chapter;
import com.studyflow.mapper.ChapterMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class AiJobService {

    private static final Logger log = LoggerFactory.getLogger(AiJobService.class);

    private final ChapterMapper chapterMapper;
    private final AiJobStore aiJobStore;
    private final AiJobExecutor aiJobExecutor;
    private final ObjectMapper objectMapper;

    public AiJobService(ChapterMapper chapterMapper,
                        AiJobStore aiJobStore,
                        AiJobExecutor aiJobExecutor,
                        ObjectMapper objectMapper) {
        this.chapterMapper = chapterMapper;
        this.aiJobStore = aiJobStore;
        this.aiJobExecutor = aiJobExecutor;
        this.objectMapper = objectMapper;
    }

    public JobDtos.GenerateJobResponse createGenerateJob(String chapterId,
                                                         JobDtos.GenerateRequest request) {
        Chapter chapter = chapterMapper.selectById(chapterId);
        if (chapter == null) {
            throw new ApiException(404, "章节不存在");
        }

        int count = request == null ? 5 : request.effectiveCount();
        int difficulty = request == null ? 3 : request.effectiveDifficulty();
        if (count < 1 || count > 10) {
            throw new ApiException(400, "count 必须在 1~10 之间");
        }
        if (difficulty < 1 || difficulty > 5) {
            throw new ApiException(400, "difficulty 必须是 1~5 的整数");
        }

        String jobId = aiJobStore.createGenerateJob(chapterId, count, difficulty);
        aiJobExecutor.run(jobId);
        return new JobDtos.GenerateJobResponse(jobId);
    }

    public JobDtos.AiJobView getJob(String jobId) {
        AiJob job = aiJobStore.get(jobId);
        if (job == null) {
            throw new ApiException(404, "任务不存在");
        }

        JsonNode result = null;
        if (job.getResultJson() != null && !job.getResultJson().isBlank()) {
            try {
                result = objectMapper.readTree(job.getResultJson());
            } catch (Exception ex) {
                log.warn("任务 {} 的 result_json 无法解析：{}", jobId, ex.getMessage());
            }
        }
        return new JobDtos.AiJobView(job.getStatus(), result, job.getError());
    }
}
