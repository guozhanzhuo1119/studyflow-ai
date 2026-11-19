package com.studyflow.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.studyflow.ai.AiClient;
import com.studyflow.ai.AiDtos;
import com.studyflow.common.ApiException;
import com.studyflow.dto.JobDtos;
import com.studyflow.entity.AiJob;
import com.studyflow.entity.Chapter;
import com.studyflow.mapper.ChapterMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * 异步执行出题任务：调 Python -> 全量校验 -> 单事务落库。
 * 任何失败只更新 ai_jobs，不写知识点/题目。
 */
@Service
public class AiJobExecutor {

    private static final Logger log = LoggerFactory.getLogger(AiJobExecutor.class);
    private static final Set<String> VALID_ANSWERS = Set.of("A", "B", "C", "D");

    private final AiJobStore aiJobStore;
    private final ChapterMapper chapterMapper;
    private final ChapterTextService chapterTextService;
    private final GenerationPersistenceService generationPersistenceService;
    private final AiClient aiClient;
    private final ObjectMapper objectMapper;

    public AiJobExecutor(AiJobStore aiJobStore,
                         ChapterMapper chapterMapper,
                         ChapterTextService chapterTextService,
                         GenerationPersistenceService generationPersistenceService,
                         AiClient aiClient,
                         ObjectMapper objectMapper) {
        this.aiJobStore = aiJobStore;
        this.chapterMapper = chapterMapper;
        this.chapterTextService = chapterTextService;
        this.generationPersistenceService = generationPersistenceService;
        this.aiClient = aiClient;
        this.objectMapper = objectMapper;
    }

    @Async("aiTaskExecutor")
    public void run(String jobId) {
        AiJob job = aiJobStore.get(jobId);
        if (job == null || !"pending".equals(job.getStatus())) {
            return;
        }
        aiJobStore.markRunning(jobId);

        try {
            JobDtos.GeneratePayload payload = objectMapper.readValue(
                    job.getRequestJson(), JobDtos.GeneratePayload.class);

            Chapter chapter = chapterMapper.selectById(payload.chapterId());
            if (chapter == null) {
                throw new ApiException(404, "章节不存在");
            }

            String chapterContent = chapterTextService.extract(chapter);
            List<String> existingTitles = generationPersistenceService.existingTitles(chapter.getId());

            AiDtos.GenerateData data = aiClient.generateQuestions(new AiDtos.GenerateRequest(
                    chapter.getName(),
                    chapterContent,
                    payload.count(),
                    payload.difficulty(),
                    existingTitles));

            log.info("出题任务 {} 返回：questions={}, dropped={}, drop_reasons={}",
                    jobId,
                    data.questions() == null ? 0 : data.questions().size(),
                    data.dropped(),
                    data.dropReasons());

            if (data.questions() == null || data.questions().isEmpty()) {
                String reason = joinReasons(data.dropReasons());
                log.warn("出题任务 {} 全部题目被丢弃，不写库：{}", jobId, reason);
                aiJobStore.markFailed(jobId,
                        "生成的题目全部不合格，未写入题库" + (reason.isEmpty() ? "" : "：" + reason));
                return;
            }

            validateQuestions(data.questions());

            JobDtos.GenerationResult result = generationPersistenceService.persist(
                    chapter, data, payload.difficulty());
            aiJobStore.markSuccess(jobId, result);
            log.info("出题任务 {} 成功：generated={}, dropped={}, total_in_chapter={}, drop_reasons={}",
                    jobId, result.generated(), result.dropped(),
                    result.totalInChapter(), result.dropReasons());
        } catch (ApiException ex) {
            log.warn("出题任务 {} 失败：{}", jobId, ex.getMessage());
            aiJobStore.markFailed(jobId, ex.getMessage());
        } catch (Exception ex) {
            log.error("出题任务 {} 异常", jobId, ex);
            aiJobStore.markFailed(jobId, "出题失败：" + ex.getMessage());
        }
    }

    /**
     * Java 侧防御性校验：只要有一题不合规，整批失败，避免写半套题。
     */
    private void validateQuestions(List<AiDtos.Question> questions) {
        for (int index = 0; index < questions.size(); index++) {
            AiDtos.Question question = questions.get(index);
            int number = index + 1;
            if (question == null) {
                throw new ApiException(502, "AI 返回题目不合法：第 " + number + " 题为空");
            }
            if (isBlank(question.title())) {
                throw new ApiException(502, "AI 返回题目不合法：第 " + number + " 题题干为空");
            }
            if (question.options() == null
                    || question.options().size() != 4
                    || question.options().stream().anyMatch(this::isBlank)) {
                throw new ApiException(502, "AI 返回题目不合法：第 " + number + " 题选项不是 4 个");
            }
            String answer = question.answer() == null
                    ? ""
                    : question.answer().strip().toUpperCase(Locale.ROOT);
            if (!VALID_ANSWERS.contains(answer)) {
                throw new ApiException(502, "AI 返回题目不合法：第 " + number + " 题答案不合法");
            }
            if (isBlank(question.explanation())) {
                throw new ApiException(502, "AI 返回题目不合法：第 " + number + " 题解析为空");
            }
            if (isBlank(question.knowledgePoint())) {
                throw new ApiException(502, "AI 返回题目不合法：第 " + number + " 题缺少知识点");
            }
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private String joinReasons(List<String> reasons) {
        return reasons == null || reasons.isEmpty() ? "" : String.join("；", reasons);
    }
}
