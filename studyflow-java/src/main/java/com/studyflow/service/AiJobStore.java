package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.studyflow.dto.JobDtos;
import com.studyflow.entity.AiJob;
import com.studyflow.mapper.AiJobMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.UUID;

@Service
public class AiJobStore {

    private final AiJobMapper aiJobMapper;
    private final ObjectMapper objectMapper;

    public AiJobStore(AiJobMapper aiJobMapper, ObjectMapper objectMapper) {
        this.aiJobMapper = aiJobMapper;
        this.objectMapper = objectMapper;
    }

    public String createGenerateJob(String chapterId, int count, int difficulty) {
        AiJob job = new AiJob();
        job.setId("job-" + shortId());
        job.setType("generate-questions");
        job.setStatus("pending");
        job.setRequestJson(writeJson(new JobDtos.GeneratePayload(chapterId, count, difficulty)));
        job.setCreatedAt(LocalDateTime.now());
        aiJobMapper.insert(job);
        return job.getId();
    }

    public AiJob get(String jobId) {
        return aiJobMapper.selectById(jobId);
    }

    public void markRunning(String jobId) {
        aiJobMapper.update(null, new LambdaUpdateWrapper<AiJob>()
                .eq(AiJob::getId, jobId)
                .eq(AiJob::getStatus, "pending")
                .set(AiJob::getStatus, "running"));
    }

    public void markSuccess(String jobId, Object result) {
        aiJobMapper.update(null, new LambdaUpdateWrapper<AiJob>()
                .eq(AiJob::getId, jobId)
                .set(AiJob::getStatus, "success")
                .set(AiJob::getResultJson, writeJson(result))
                .set(AiJob::getFinishedAt, LocalDateTime.now()));
    }

    public void markFailed(String jobId, String error) {
        aiJobMapper.update(null, new LambdaUpdateWrapper<AiJob>()
                .eq(AiJob::getId, jobId)
                .set(AiJob::getStatus, "failed")
                .set(AiJob::getError, error)
                .set(AiJob::getFinishedAt, LocalDateTime.now()));
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("AI 任务 JSON 序列化失败", ex);
        }
    }

    private static String shortId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 8);
    }
}
