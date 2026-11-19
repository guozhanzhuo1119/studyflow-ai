package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.studyflow.common.ApiException;
import com.studyflow.dto.ProblemSearchRequest;
import com.studyflow.dto.ProblemSearchResponse;
import com.studyflow.dto.ProblemSearchResult;
import com.studyflow.dto.ProblemView;
import com.studyflow.entity.Chapter;
import com.studyflow.entity.KnowledgePoint;
import com.studyflow.entity.Problem;
import com.studyflow.entity.Subject;
import com.studyflow.mapper.ChapterMapper;
import com.studyflow.mapper.KnowledgePointMapper;
import com.studyflow.mapper.ProblemMapper;
import com.studyflow.mapper.SubjectMapper;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

@Service
public class ProblemService {

    private static final TypeReference<List<Object>> OPTIONS_TYPE = new TypeReference<>() {
    };

    private final ProblemMapper problemMapper;
    private final KnowledgePointMapper knowledgePointMapper;
    private final ChapterMapper chapterMapper;
    private final SubjectMapper subjectMapper;
    private final ObjectMapper objectMapper;

    public ProblemService(ProblemMapper problemMapper,
                          KnowledgePointMapper knowledgePointMapper,
                          ChapterMapper chapterMapper,
                          SubjectMapper subjectMapper,
                          ObjectMapper objectMapper) {
        this.problemMapper = problemMapper;
        this.knowledgePointMapper = knowledgePointMapper;
        this.chapterMapper = chapterMapper;
        this.subjectMapper = subjectMapper;
        this.objectMapper = objectMapper;
    }

    public List<ProblemView> list(String knowledgePointId) {
        LambdaQueryWrapper<Problem> query = new LambdaQueryWrapper<>();
        if (knowledgePointId != null && !knowledgePointId.isEmpty()) {
            query.eq(Problem::getKnowledgePointId, knowledgePointId);
        }

        List<Problem> problems = problemMapper.selectList(query);
        List<ProblemView> views = new ArrayList<>(problems.size());
        for (Problem problem : problems) {
            views.add(toView(problem));
        }
        return views;
    }

    public ProblemView get(String problemId) {
        Problem problem = problemMapper.selectById(problemId);
        if (problem == null) {
            throw new ApiException(404, "题目不存在");
        }
        return toView(problem);
    }

    /**
     * 本期以 MySQL 关键词检索替代 FAISS（方案 §14.11），响应结构保持旧版。
     */
    public ProblemSearchResponse search(ProblemSearchRequest request) {
        String query = request.query() == null ? "" : request.query();
        String matchText = query.trim();
        if (matchText.isEmpty()) {
            return new ProblemSearchResponse(query, 0, List.of());
        }

        int topK = request.effectiveTopK();
        if (topK == 0) {
            return new ProblemSearchResponse(query, 0, List.of());
        }

        // 多取一些候选，按标题命中优先排序后再截断
        int fetch = Math.min(Math.max(topK * 5, topK), 200);
        LambdaQueryWrapper<Problem> wrapper = new LambdaQueryWrapper<>();
        wrapper.and(w -> w.like(Problem::getTitle, matchText)
                .or()
                .like(Problem::getContent, matchText));
        wrapper.last("LIMIT " + fetch);

        List<Problem> matched = problemMapper.selectList(wrapper);
        List<ProblemSearchResult> results = matched.stream()
                .map(problem -> toSearchResult(problem, matchText))
                .sorted(Comparator.comparingDouble(ProblemSearchResult::score).reversed())
                .limit(topK)
                .toList();

        return new ProblemSearchResponse(query, results.size(), results);
    }

    private ProblemView toView(Problem problem) {
        KnowledgePoint knowledgePoint = knowledgePoint(problem);
        Chapter chapter = knowledgePoint == null ? null
                : chapter(knowledgePoint.getChapterId());
        Subject subject = chapter == null ? null
                : subject(chapter.getSubjectId());

        return new ProblemView(
                problem.getId(),
                problem.getTitle(),
                problem.getContent(),
                problem.getSource(),
                problem.getTags(),
                problem.getType(),
                parseOptions(problem.getOptions()),
                problem.getDifficulty(),
                problem.getStatus(),
                problem.getKnowledgePointId(),
                knowledgePoint == null ? null : knowledgePoint.getName(),
                chapter == null ? null : chapter.getId(),
                chapter == null ? null : chapter.getName(),
                subject == null ? null : subject.getId(),
                subject == null ? null : subject.getName(),
                problem.getCreatedAt());
    }

    private ProblemSearchResult toSearchResult(Problem problem, String matchText) {
        KnowledgePoint knowledgePoint = knowledgePoint(problem);
        Chapter chapter = knowledgePoint == null ? null
                : chapter(knowledgePoint.getChapterId());
        Subject subject = chapter == null ? null
                : subject(chapter.getSubjectId());

        String title = problem.getTitle() == null ? "" : problem.getTitle();
        double score = title.toLowerCase(Locale.ROOT).contains(matchText.toLowerCase(Locale.ROOT))
                ? 1.0
                : 0.5;

        return new ProblemSearchResult(
                problem.getId(),
                problem.getTitle(),
                problem.getSource(),
                problem.getTags(),
                problem.getKnowledgePointId(),
                knowledgePoint == null ? null : knowledgePoint.getName(),
                chapter == null ? null : chapter.getName(),
                subject == null ? null : subject.getName(),
                problem.getStatus(),
                score);
    }

    private KnowledgePoint knowledgePoint(Problem problem) {
        return problem.getKnowledgePointId() == null
                ? null
                : knowledgePointMapper.selectById(problem.getKnowledgePointId());
    }

    private Chapter chapter(String chapterId) {
        return chapterId == null ? null : chapterMapper.selectById(chapterId);
    }

    private Subject subject(String subjectId) {
        return subjectId == null ? null : subjectMapper.selectById(subjectId);
    }

    /** options 列存 JSON 文本；历史题目为空或非法时返回空数组。 */
    private List<Object> parseOptions(String raw) {
        if (raw == null || raw.isBlank()) {
            return List.of();
        }
        try {
            List<Object> parsed = objectMapper.readValue(raw, OPTIONS_TYPE);
            return parsed == null ? List.of() : parsed;
        } catch (JsonProcessingException ex) {
            return List.of();
        }
    }
}
