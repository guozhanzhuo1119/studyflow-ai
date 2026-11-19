package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.studyflow.ai.AiDtos;
import com.studyflow.dto.JobDtos;
import com.studyflow.entity.Chapter;
import com.studyflow.entity.KnowledgePoint;
import com.studyflow.entity.Problem;
import com.studyflow.mapper.KnowledgePointMapper;
import com.studyflow.mapper.ProblemMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * 出题落库：知识点按章内同名复用，题目与知识点同一事务提交，任一失败全部回滚。
 */
@Service
public class GenerationPersistenceService {

    private static final Pattern WHITESPACE = Pattern.compile("\\s+", Pattern.UNICODE_CHARACTER_CLASS);

    private final KnowledgePointMapper knowledgePointMapper;
    private final ProblemMapper problemMapper;
    private final ObjectMapper objectMapper;

    public GenerationPersistenceService(KnowledgePointMapper knowledgePointMapper,
                                        ProblemMapper problemMapper,
                                        ObjectMapper objectMapper) {
        this.knowledgePointMapper = knowledgePointMapper;
        this.problemMapper = problemMapper;
        this.objectMapper = objectMapper;
    }

    public List<String> existingTitles(String chapterId) {
        List<KnowledgePoint> knowledgePoints = knowledgePointMapper.selectList(
                new LambdaQueryWrapper<KnowledgePoint>()
                        .eq(KnowledgePoint::getChapterId, chapterId));
        if (knowledgePoints.isEmpty()) {
            return List.of();
        }
        List<String> ids = knowledgePoints.stream().map(KnowledgePoint::getId).toList();
        List<Problem> problems = problemMapper.selectList(
                new LambdaQueryWrapper<Problem>().in(Problem::getKnowledgePointId, ids));
        List<String> titles = new ArrayList<>(problems.size());
        for (Problem problem : problems) {
            if (problem.getTitle() != null) {
                titles.add(problem.getTitle());
            }
        }
        return titles;
    }

    @Transactional
    public JobDtos.GenerationResult persist(Chapter chapter,
                                            AiDtos.GenerateData data,
                                            int difficulty) {
        List<AiDtos.Question> questions = data.questions();

        List<KnowledgePoint> existing = knowledgePointMapper.selectList(
                new LambdaQueryWrapper<KnowledgePoint>()
                        .eq(KnowledgePoint::getChapterId, chapter.getId()));
        Map<String, KnowledgePoint> knowledgePoints = new HashMap<>();
        for (KnowledgePoint knowledgePoint : existing) {
            knowledgePoints.put(normalizeKnowledgePoint(knowledgePoint.getName()), knowledgePoint);
        }

        LocalDateTime now = LocalDateTime.now();
        String tags = truncate(chapter.getName() + ",AI出题", 200);

        for (AiDtos.Question question : questions) {
            String kpName = normalizeKnowledgePoint(question.knowledgePoint());
            KnowledgePoint knowledgePoint = knowledgePoints.get(kpName);
            if (knowledgePoint == null) {
                knowledgePoint = new KnowledgePoint();
                knowledgePoint.setId("kp-" + shortId());
                knowledgePoint.setChapterId(chapter.getId());
                knowledgePoint.setName(truncate(kpName, 100));
                knowledgePoint.setCreatedAt(now);
                knowledgePointMapper.insert(knowledgePoint);
                knowledgePoints.put(kpName, knowledgePoint);
            }

            Problem problem = new Problem();
            problem.setId("prob-" + shortId());
            problem.setTitle(truncate(question.title(), 200));
            problem.setContent(null);
            problem.setSource("AI 生成");
            problem.setTags(tags);
            problem.setType("single");
            problem.setOptions(writeOptions(question.options()));
            problem.setAnswer(question.answer());
            problem.setExplanation(question.explanation());
            problem.setDifficulty(difficulty);
            problem.setStatus("todo");
            problem.setKnowledgePointId(knowledgePoint.getId());
            problem.setCreatedAt(now);
            problemMapper.insert(problem);
        }

        List<String> knowledgePointIds = knowledgePoints.values().stream()
                .map(KnowledgePoint::getId)
                .toList();
        long total = knowledgePointIds.isEmpty()
                ? 0L
                : problemMapper.selectCount(new LambdaQueryWrapper<Problem>()
                        .in(Problem::getKnowledgePointId, knowledgePointIds));

        return new JobDtos.GenerationResult(
                questions.size(),
                data.dropped(),
                total,
                data.dropReasons() == null ? List.of() : data.dropReasons());
    }

    private String writeOptions(List<String> options) {
        try {
            // 旧库要求 A/B/C/D 顺序的 JSON 数组文本，不能写成 {"1": ...}
            return objectMapper.writeValueAsString(options);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("题目选项序列化失败", ex);
        }
    }

    private static String normalizeKnowledgePoint(String name) {
        return WHITESPACE.matcher(name == null ? "" : name).replaceAll("");
    }

    private static String truncate(String value, int max) {
        if (value == null) {
            return null;
        }
        return value.length() <= max ? value : value.substring(0, max);
    }

    private static String shortId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 8);
    }
}
