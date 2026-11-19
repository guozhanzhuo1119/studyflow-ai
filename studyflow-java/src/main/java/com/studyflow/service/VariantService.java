package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.studyflow.ai.AiClient;
import com.studyflow.ai.AiDtos;
import com.studyflow.common.ApiException;
import com.studyflow.dto.VariantDtos;
import com.studyflow.entity.Chapter;
import com.studyflow.entity.KnowledgePoint;
import com.studyflow.entity.Problem;
import com.studyflow.entity.Subject;
import com.studyflow.entity.Variant;
import com.studyflow.mapper.ChapterMapper;
import com.studyflow.mapper.KnowledgePointMapper;
import com.studyflow.mapper.ProblemMapper;
import com.studyflow.mapper.SubjectMapper;
import com.studyflow.mapper.VariantMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Service
public class VariantService {

    private final AiClient aiClient;
    private final VariantMapper variantMapper;
    private final ProblemMapper problemMapper;
    private final KnowledgePointMapper knowledgePointMapper;
    private final ChapterMapper chapterMapper;
    private final SubjectMapper subjectMapper;
    private final ObjectMapper objectMapper;

    public VariantService(AiClient aiClient,
                          VariantMapper variantMapper,
                          ProblemMapper problemMapper,
                          KnowledgePointMapper knowledgePointMapper,
                          ChapterMapper chapterMapper,
                          SubjectMapper subjectMapper,
                          ObjectMapper objectMapper) {
        this.aiClient = aiClient;
        this.variantMapper = variantMapper;
        this.problemMapper = problemMapper;
        this.knowledgePointMapper = knowledgePointMapper;
        this.chapterMapper = chapterMapper;
        this.subjectMapper = subjectMapper;
        this.objectMapper = objectMapper;
    }

    public VariantDtos.RecommendResponse recommend(VariantDtos.RecommendRequest request) {
        Problem problem = requireProblem(request.problemId(), "题目不存在");
        int count = request.effectiveCount();
        if (count < 1 || count > 10) {
            throw new ApiException(400, "count 必须在 1~10 之间");
        }

        KnowledgePoint knowledgePoint = problem.getKnowledgePointId() == null
                ? null
                : knowledgePointMapper.selectById(problem.getKnowledgePointId());
        Chapter chapter = knowledgePoint == null || knowledgePoint.getChapterId() == null
                ? null
                : chapterMapper.selectById(knowledgePoint.getChapterId());
        Subject subject = chapter == null || chapter.getSubjectId() == null
                ? null
                : subjectMapper.selectById(chapter.getSubjectId());

        AiDtos.Hierarchy hierarchy = new AiDtos.Hierarchy(
                subject == null ? null : subject.getName(),
                chapter == null ? null : chapter.getName(),
                knowledgePoint == null ? null : knowledgePoint.getName());

        AiDtos.VariantData data = aiClient.variants(new AiDtos.VariantRequest(
                problem.getTitle(),
                parseOptions(problem.getOptions()),
                problem.getAnswer(),
                problem.getExplanation(),
                count,
                hierarchy,
                problem.getSource(),
                problem.getTags()));

        List<AiDtos.VariantItem> recommendations = data.variants() == null
                ? List.of()
                : data.variants();
        return new VariantDtos.RecommendResponse(
                problem.getId(), problem.getTitle(), recommendations);
    }

    public VariantDtos.VariantView get(String variantId) {
        Variant variant = variantMapper.selectById(variantId);
        if (variant == null) {
            throw new ApiException(404, "变题不存在");
        }
        return toView(variant);
    }

    public List<VariantDtos.VariantView> list(String problemId) {
        LambdaQueryWrapper<Variant> query = new LambdaQueryWrapper<>();
        if (problemId != null && !problemId.isBlank()) {
            query.eq(Variant::getProblemId, problemId);
        }
        List<Variant> variants = variantMapper.selectList(query);
        List<VariantDtos.VariantView> views = new ArrayList<>(variants.size());
        for (Variant variant : variants) {
            views.add(toView(variant));
        }
        return views;
    }

    @Transactional
    public VariantDtos.VariantView create(VariantDtos.VariantCreateRequest request) {
        Problem problem = requireProblem(request.problemId(), "母题不存在");
        if (request.title() == null || request.title().isBlank()) {
            throw new ApiException(400, "变题标题不能为空");
        }
        Variant variant = newVariant(problem.getId(), request.title(), request.content(),
                request.difficulty(), request.link(), request.reason(), "manual");
        variantMapper.insert(variant);
        return toView(variant, problem.getTitle());
    }

    @Transactional
    public VariantDtos.VariantView update(String variantId, VariantDtos.VariantCreateRequest request) {
        Variant variant = variantMapper.selectById(variantId);
        if (variant == null) {
            throw new ApiException(404, "变题不存在");
        }
        Problem problem = requireProblem(request.problemId(), "母题不存在");
        variant.setProblemId(request.problemId());
        variant.setTitle(request.title());
        variant.setContent(request.content());
        variant.setDifficulty(request.difficulty());
        variant.setLink(request.link());
        variant.setReason(request.reason());
        variantMapper.updateById(variant);
        return toView(variant, problem.getTitle());
    }

    public void delete(String variantId) {
        Variant variant = variantMapper.selectById(variantId);
        if (variant == null) {
            throw new ApiException(404, "变题不存在");
        }
        variantMapper.deleteById(variantId);
    }

    @Transactional
    public VariantDtos.SaveVariantsResponse saveFromRecommendation(
            VariantDtos.SaveFromRecommendationRequest request) {
        Problem problem = requireProblem(request.problemId(), "母题不存在");
        if (request.recommendations() == null || request.recommendations().isEmpty()) {
            throw new ApiException(400, "推荐列表为空");
        }

        List<VariantDtos.VariantView> saved = new ArrayList<>(request.recommendations().size());
        for (VariantDtos.VariantSaveItem item : request.recommendations()) {
            if (item == null || item.title() == null || item.title().isBlank()) {
                throw new ApiException(400, "推荐标题不能为空");
            }
            Variant variant = newVariant(
                    problem.getId(),
                    item.title(),
                    item.content(),
                    item.difficulty(),
                    item.link(),
                    item.reason(),
                    "ai");
            variantMapper.insert(variant);
            saved.add(toView(variant, problem.getTitle()));
        }
        return new VariantDtos.SaveVariantsResponse(saved.size(), saved);
    }

    private Variant newVariant(String problemId,
                               String title,
                               String content,
                               String difficulty,
                               String link,
                               String reason,
                               String origin) {
        Variant variant = new Variant();
        variant.setId("var-" + shortId());
        variant.setProblemId(problemId);
        variant.setTitle(truncate(title, 200));
        variant.setContent(content);
        variant.setDifficulty(truncate(difficulty, 20));
        variant.setLink(truncate(link, 300));
        variant.setReason(reason);
        variant.setOrigin(origin);
        variant.setCreatedAt(LocalDateTime.now());
        return variant;
    }

    private VariantDtos.VariantView toView(Variant variant) {
        Problem problem = problemMapper.selectById(variant.getProblemId());
        return toView(variant, problem == null ? null : problem.getTitle());
    }

    private VariantDtos.VariantView toView(Variant variant, String problemTitle) {
        return new VariantDtos.VariantView(
                variant.getId(),
                variant.getProblemId(),
                problemTitle,
                variant.getTitle(),
                variant.getContent(),
                variant.getDifficulty(),
                variant.getLink(),
                variant.getReason(),
                variant.getOrigin(),
                variant.getCreatedAt());
    }

    private Problem requireProblem(String problemId, String message) {
        Problem problem = problemId == null ? null : problemMapper.selectById(problemId);
        if (problem == null) {
            throw new ApiException(404, message);
        }
        return problem;
    }

    private List<String> parseOptions(String raw) {
        if (raw == null || raw.isBlank()) {
            return List.of();
        }
        try {
            List<Object> parsed = objectMapper.readValue(raw, new TypeReference<List<Object>>() {
            });
            if (parsed == null) {
                return List.of();
            }
            List<String> options = new ArrayList<>(parsed.size());
            for (Object item : parsed) {
                options.add(item == null ? "" : String.valueOf(item));
            }
            return options;
        } catch (Exception ex) {
            return List.of();
        }
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
