package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.studyflow.common.ApiException;
import com.studyflow.dto.ErrorDtos;
import com.studyflow.entity.Attempt;
import com.studyflow.entity.ErrorAnalysis;
import com.studyflow.error.ErrorCatalog;
import com.studyflow.mapper.AttemptMapper;
import com.studyflow.mapper.ErrorAnalysisMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 错因档案：CRUD、决策树、统计。全部是 Java 规则，不调用 AI 服务。
 */
@Service
public class ErrorService {

    private static final List<String> DECOMPOSE_KEYWORDS = List.of("=", "母题", "改");

    private final ErrorAnalysisMapper errorAnalysisMapper;
    private final AttemptMapper attemptMapper;

    public ErrorService(ErrorAnalysisMapper errorAnalysisMapper, AttemptMapper attemptMapper) {
        this.errorAnalysisMapper = errorAnalysisMapper;
        this.attemptMapper = attemptMapper;
    }

    public Map<String, Object> meta(String topic) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("error_types", ErrorCatalog.errorTypesForApi());
        result.put("tags", List.of(ErrorCatalog.syntaxTag()));
        result.put("remedy_status", ErrorCatalog.REMEDY_STATUSES);
        result.put("decision_tree", ErrorCatalog.DECISION_TREE);
        result.put("presets", ErrorCatalog.presets(topic));
        return result;
    }

    public ErrorDtos.DecideResponse decide(ErrorDtos.DecideRequest request) {
        if (request == null || request.answers() == null || request.answers().isEmpty()) {
            throw new ApiException(400, "answers 至少需要 1 个回答");
        }
        String errorType = ErrorCatalog.applyDecisionTree(request.answers());
        boolean suggest = "OPERATE".equals(errorType)
                && ErrorCatalog.suggestSyntaxTag(request.specificBehavior());
        return new ErrorDtos.DecideResponse(errorType, suggest);
    }

    public Map<String, Object> statistics(boolean practiceMode) {
        List<ErrorAnalysis> rows = errorAnalysisMapper.selectList(null);
        List<Attempt> attempts = attemptMapper.selectList(null);

        Map<String, Integer> distribution = new LinkedHashMap<>();
        for (String code : ErrorCatalog.ERROR_TYPES.keySet()) {
            distribution.put(code, 0);
        }
        for (ErrorAnalysis row : rows) {
            Integer current = distribution.get(row.getErrorType());
            if (current != null) {
                distribution.put(row.getErrorType(), current + 1);
            }
        }

        List<Integer> latencies = new ArrayList<>();
        for (ErrorAnalysis row : rows) {
            if (row.getIdentifyLatencySec() != null) {
                latencies.add(row.getIdentifyLatencySec());
            }
        }
        Double latencyAvg = latencies.isEmpty()
                ? null
                : round1(latencies.stream().mapToInt(Integer::intValue).average().orElse(0));

        int decomposeTotal = 0;
        int decomposeCovered = 0;
        int pending = 0;
        for (ErrorAnalysis row : rows) {
            if ("DECOMPOSE".equals(row.getErrorType())) {
                decomposeTotal++;
                if (row.getDecompositionSentence() != null && !row.getDecompositionSentence().isEmpty()) {
                    decomposeCovered++;
                }
            }
            if (ErrorCatalog.REMEDY_PENDING.equals(row.getRemedyStatus())) {
                pending++;
            }
        }

        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("error_distribution", distribution);
        stats.put("identify_latency_avg_sec", latencyAvg);
        stats.put("decomposition_coverage", decomposeCovered + "/" + decomposeTotal);
        stats.put("remedy_pending_count", pending);
        stats.put("total", rows.size());
        stats.put("attempt_total", attempts.size());

        if (!practiceMode) {
            List<Attempt> graded = attempts.stream()
                    .filter(a -> "correct".equals(a.getResult()) || "wrong".equals(a.getResult()))
                    .toList();
            Double accuracy = graded.isEmpty()
                    ? null
                    : round4((double) graded.stream().filter(a -> "correct".equals(a.getResult())).count()
                    / graded.size());

            List<Integer> durations = attempts.stream()
                    .map(Attempt::getDurationSec)
                    .filter(d -> d != null && d != 0)
                    .toList();
            Double avgTime = durations.isEmpty()
                    ? null
                    : round1(durations.stream().mapToInt(Integer::intValue).average().orElse(0));

            List<Attempt> sorted = new ArrayList<>(attempts);
            sorted.sort((a, b) -> Long.compare(a.getId(), b.getId()));
            List<Attempt> recent = sorted.size() <= 10
                    ? sorted
                    : sorted.subList(sorted.size() - 10, sorted.size());
            List<Attempt> recentGraded = recent.stream()
                    .filter(a -> "correct".equals(a.getResult()) || "wrong".equals(a.getResult()))
                    .toList();
            Double stability = recentGraded.isEmpty()
                    ? null
                    : round4((double) recentGraded.stream()
                    .filter(a -> "correct".equals(a.getResult())).count() / recentGraded.size());

            stats.put("accuracy", accuracy);
            stats.put("avg_time_sec", avgTime);
            stats.put("stability", stability);
        }
        return stats;
    }

    public List<ErrorDtos.RecordView> list(String problemId, String errorType, Boolean reviewed) {
        LambdaQueryWrapper<ErrorAnalysis> query = new LambdaQueryWrapper<>();
        if (problemId != null && !problemId.isBlank()) {
            query.eq(ErrorAnalysis::getProblemId, problemId);
        }
        if (errorType != null && !errorType.isBlank()) {
            query.eq(ErrorAnalysis::getErrorType, errorType);
        }
        if (reviewed != null) {
            query.eq(ErrorAnalysis::getReviewed, reviewed);
        }
        query.orderByDesc(ErrorAnalysis::getCreatedAt).orderByDesc(ErrorAnalysis::getId);

        List<ErrorAnalysis> rows = errorAnalysisMapper.selectList(query);
        List<ErrorDtos.RecordView> views = new ArrayList<>(rows.size());
        for (ErrorAnalysis row : rows) {
            views.add(toView(row));
        }
        return views;
    }

    public ErrorDtos.CreateResponse create(ErrorDtos.CreateRequest request) {
        Validated validated = validateCreate(request);

        ErrorAnalysis row = new ErrorAnalysis();
        row.setProblemId(request.problemId());
        row.setProblemTitle(request.problemTitle());
        row.setTopic(request.topic());
        row.setMotherProblem(request.motherProblem());
        row.setErrorType(validated.errorType());
        row.setTag(validated.tag());
        row.setSpecificBehavior(request.specificBehavior());
        row.setFirstBreakPoint(validated.firstBreakPoint());
        row.setDecompositionSentence(request.decompositionSentence());
        row.setRemedyStatus(validated.remedyStatus());
        row.setRemedyAction(request.remedyAction());
        row.setUserNote(request.userNote());
        row.setReviewed(request.reviewed() != null && request.reviewed());
        row.setCreatedAt(LocalDateTime.now());
        row.setIdentifyLatencySec(request.identifyLatencySec());
        errorAnalysisMapper.insert(row);

        boolean suggest = "OPERATE".equals(row.getErrorType())
                && ErrorCatalog.suggestSyntaxTag(row.getSpecificBehavior());
        return new ErrorDtos.CreateResponse(toView(row), suggest);
    }

    public ErrorDtos.RecordView update(Long errorId, ErrorDtos.UpdateRequest request) {
        ErrorAnalysis row = errorAnalysisMapper.selectById(errorId);
        if (row == null) {
            throw new ApiException(404, "归因记录不存在");
        }
        if (request != null) {
            if (request.reviewed() != null) {
                row.setReviewed(request.reviewed());
            }
            if (request.remedyStatus() != null) {
                if (!ErrorCatalog.isValidRemedyStatus(request.remedyStatus())) {
                    throw new ApiException(400, "remedy_status 只能是 ['待补', '已补']");
                }
                row.setRemedyStatus(request.remedyStatus());
            }
            if (request.remedyAction() != null) {
                row.setRemedyAction(request.remedyAction());
            }
            if (request.userNote() != null) {
                row.setUserNote(request.userNote());
            }
        }
        errorAnalysisMapper.updateById(row);
        return toView(row);
    }

    public Map<String, Object> delete(Long errorId) {
        ErrorAnalysis row = errorAnalysisMapper.selectById(errorId);
        if (row == null) {
            throw new ApiException(404, "归因记录不存在");
        }
        errorAnalysisMapper.deleteById(errorId);
        return Map.of("message", "删除成功");
    }

    private Validated validateCreate(ErrorDtos.CreateRequest request) {
        if (request == null) {
            throw new ApiException(400, "请求体不能为空");
        }
        if (request.problemId() == null) {
            throw new ApiException(400, "problem_id 不能为空");
        }
        if (request.problemTitle() == null) {
            throw new ApiException(400, "problem_title 不能为空");
        }
        if (request.problemTitle().length() > 200) {
            throw new ApiException(400, "problem_title 不能超过 200 字");
        }
        if (!ErrorCatalog.isValidErrorType(request.errorType())) {
            throw new ApiException(400, "error_type 只能是 "
                    + "['READ', 'IDENTIFY', 'DECOMPOSE', 'OPERATE', 'BOUNDARY', 'EFFICIENCY']");
        }

        String tag = request.tag();
        if (tag != null && !tag.isBlank()) {
            if (!ErrorCatalog.TAG_SYNTAX.equals(tag)) {
                throw new ApiException(400, "tag 只能是 SYNTAX");
            }
            if (!"OPERATE".equals(request.errorType())) {
                throw new ApiException(400, "tag 仅在 error_type=OPERATE 时可填");
            }
        } else {
            tag = null;
        }

        if (request.specificBehavior() == null) {
            throw new ApiException(400, "specific_behavior 不能为空");
        }
        if (request.specificBehavior().length() > 50) {
            throw new ApiException(400, "specific_behavior 不能超过 50 字");
        }

        String firstBreakPoint = request.firstBreakPoint() == null || request.firstBreakPoint().isBlank()
                ? request.errorType()
                : request.firstBreakPoint();
        if (!ErrorCatalog.isValidErrorType(firstBreakPoint)) {
            throw new ApiException(400, "first_break_point 不合法");
        }

        String sentence = request.decompositionSentence();
        if ("DECOMPOSE".equals(request.errorType())) {
            if (sentence == null || sentence.isEmpty()) {
                throw new ApiException(400, "DECOMPOSE 类必须填写 decomposition_sentence");
            }
            StringBuilder missing = new StringBuilder();
            for (String keyword : DECOMPOSE_KEYWORDS) {
                if (!sentence.contains(keyword)) {
                    missing.append(keyword);
                }
            }
            if (!missing.isEmpty()) {
                throw new ApiException(400,
                        "拆解句必须同时含「=」「母题」「改」三关键词，缺少：" + missing);
            }
        } else if (sentence != null && !sentence.isEmpty()) {
            throw new ApiException(400, "仅 DECOMPOSE 类可填写 decomposition_sentence");
        }

        String remedyStatus = request.remedyStatus() == null || request.remedyStatus().isBlank()
                ? ErrorCatalog.REMEDY_PENDING
                : request.remedyStatus();
        if (!ErrorCatalog.isValidRemedyStatus(remedyStatus)) {
            throw new ApiException(400, "remedy_status 只能是 ['待补', '已补']");
        }

        if (request.identifyLatencySec() != null && request.identifyLatencySec() < 0) {
            throw new ApiException(400, "identify_latency_sec 不能小于 0");
        }

        return new Validated(request.errorType(), tag, firstBreakPoint, remedyStatus);
    }

    private ErrorDtos.RecordView toView(ErrorAnalysis row) {
        return new ErrorDtos.RecordView(
                row.getId(),
                row.getProblemId(),
                row.getProblemTitle(),
                row.getTopic(),
                row.getMotherProblem(),
                row.getErrorType(),
                ErrorCatalog.errorTypeName(row.getErrorType()),
                row.getTag(),
                row.getSpecificBehavior(),
                row.getFirstBreakPoint(),
                row.getDecompositionSentence(),
                row.getRemedyStatus(),
                row.getRemedyAction(),
                row.getUserNote(),
                row.getReviewed(),
                row.getCreatedAt(),
                row.getIdentifyLatencySec());
    }

    private static double round1(double value) {
        return Math.round(value * 10.0) / 10.0;
    }

    private static double round4(double value) {
        return Math.round(value * 10000.0) / 10000.0;
    }

    private record Validated(String errorType, String tag, String firstBreakPoint, String remedyStatus) {
    }
}
