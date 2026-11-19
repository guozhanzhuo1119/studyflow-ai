package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.studyflow.common.ApiException;
import com.studyflow.dto.AttemptDtos;
import com.studyflow.entity.Attempt;
import com.studyflow.entity.Problem;
import com.studyflow.entity.Variant;
import com.studyflow.error.ErrorCatalog;
import com.studyflow.mapper.AttemptMapper;
import com.studyflow.mapper.ProblemMapper;
import com.studyflow.mapper.VariantMapper;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

@Service
public class AttemptService {

    private static final Set<String> TARGET_TYPES = Set.of("problem", "variant");
    private static final Set<String> RESULT_VALUES = Set.of("correct", "wrong");

    private final AttemptMapper attemptMapper;
    private final ProblemMapper problemMapper;
    private final VariantMapper variantMapper;
    private final AttemptPersistenceService attemptPersistenceService;

    public AttemptService(AttemptMapper attemptMapper,
                          ProblemMapper problemMapper,
                          VariantMapper variantMapper,
                          AttemptPersistenceService attemptPersistenceService) {
        this.attemptMapper = attemptMapper;
        this.problemMapper = problemMapper;
        this.variantMapper = variantMapper;
        this.attemptPersistenceService = attemptPersistenceService;
    }

    public Map<String, Object> create(AttemptDtos.CreateRequest request) {
        if (!TARGET_TYPES.contains(request.targetType())) {
            throw new ApiException(400, "target_type 只能是 ['problem', 'variant']");
        }
        if (request.targetId() == null || request.targetId().isBlank()) {
            throw new ApiException(404, "题目不存在");
        }

        String clientToken = request.clientToken() == null ? null : request.clientToken().strip();
        if (clientToken != null && clientToken.isEmpty()) {
            clientToken = null;
        }
        if (clientToken != null && clientToken.length() > 64) {
            throw new ApiException(400, "client_token 长度不能超过 64");
        }

        // 先查：同一 client_token 直接返回上次结果，不重复计分
        if (clientToken != null) {
            Attempt existing = findByClientToken(clientToken);
            if (existing != null) {
                return buildIdempotentResponse(existing, request);
            }
        }

        TargetInfo target = requireTarget(request.targetType(), request.targetId());
        boolean graded = false;
        String result = request.result();

        if (request.userAnswers() != null) {
            if (!"problem".equals(request.targetType())) {
                throw new ApiException(400, "变题没有标准答案，无法自动判分");
            }
            String correctAnswer = target.answer() == null ? "" : target.answer().strip().toUpperCase(Locale.ROOT);
            if (correctAnswer.isEmpty()) {
                throw new ApiException(400, "该题无答案");
            }
            Set<String> userSet = normalizeAnswers(request.userAnswers());
            if (userSet.isEmpty()) {
                throw new ApiException(400, "user_answers 不能为空");
            }
            Set<String> correctSet = new LinkedHashSet<>();
            for (char ch : correctAnswer.toCharArray()) {
                if (ch >= 'A' && ch <= 'D') {
                    correctSet.add(String.valueOf(ch));
                }
            }
            result = userSet.equals(correctSet) ? "correct" : "wrong";
            graded = true;
        }

        if (!RESULT_VALUES.contains(result)) {
            throw new ApiException(400, "result 只能是 ['correct', 'wrong']");
        }

        String errorType = request.errorType() == null ? null : request.errorType().strip();
        if (errorType != null && errorType.isEmpty()) {
            errorType = null;
        }
        if (errorType != null && !"wrong".equals(result)) {
            throw new ApiException(400, "只有做错时才能填 error_type");
        }
        if (errorType != null && !ErrorCatalog.isValidErrorType(errorType)) {
            throw new ApiException(400, "error_type 只能是 "
                    + "['READ', 'IDENTIFY', 'DECOMPOSE', 'OPERATE', 'BOUNDARY', 'EFFICIENCY']");
        }

        LocalDateTime now = LocalDateTime.now();
        Attempt attempt = new Attempt();
        attempt.setTargetType(request.targetType());
        attempt.setTargetId(request.targetId());
        attempt.setResult(result);
        attempt.setDurationSec(request.durationSec());
        String errorReason = request.errorReason() == null ? null : request.errorReason().strip();
        attempt.setErrorReason(errorReason == null || errorReason.isEmpty() ? null : errorReason);
        attempt.setSource(request.source() == null || request.source().isBlank()
                ? "manual" : request.source());
        attempt.setClientToken(clientToken);
        attempt.setCreatedAt(now);

        Long errorId;
        try {
            errorId = attemptPersistenceService.insert(
                    attempt, target.title(), errorType, attempt.getErrorReason(), now);
        } catch (DuplicateKeyException ex) {
            // 并发下唯一键兜底：回滚后查回上次结果，不重复计分
            if (clientToken != null) {
                Attempt existing = findByClientToken(clientToken);
                if (existing != null) {
                    return buildIdempotentResponse(existing, request);
                }
            }
            throw new ApiException(409, "重复提交，本次作答未保存");
        }

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("id", attempt.getId());
        payload.put("error_id", errorId);
        payload.put("result", attempt.getResult());
        payload.put("stats", statsFor(request.targetType(), request.targetId()));
        if (graded && target.answer() != null) {
            payload.put("correct_answer", target.answer());
            payload.put("explanation", target.explanation());
        }
        return payload;
    }

    public AttemptDtos.OverviewResponse overview(String knowledgePointId, String problemId) {
        LambdaQueryWrapper<Attempt> wrapper = new LambdaQueryWrapper<>();

        if (problemId != null && !problemId.isBlank()) {
            List<String> variantIds = variantMapper.selectList(
                            new LambdaQueryWrapper<Variant>().eq(Variant::getProblemId, problemId))
                    .stream().map(Variant::getId).toList();
            wrapper.and(inner -> {
                inner.eq(Attempt::getTargetType, "problem").eq(Attempt::getTargetId, problemId);
                if (!variantIds.isEmpty()) {
                    inner.or(nested -> nested.eq(Attempt::getTargetType, "variant")
                            .in(Attempt::getTargetId, variantIds));
                }
            });
        } else if (knowledgePointId != null && !knowledgePointId.isBlank()) {
            List<String> problemIds = problemMapper.selectList(
                            new LambdaQueryWrapper<Problem>()
                                    .eq(Problem::getKnowledgePointId, knowledgePointId))
                    .stream().map(Problem::getId).toList();
            List<String> variantIds = problemIds.isEmpty()
                    ? List.of()
                    : variantMapper.selectList(new LambdaQueryWrapper<Variant>()
                            .in(Variant::getProblemId, problemIds))
                    .stream().map(Variant::getId).toList();

            if (problemIds.isEmpty() && variantIds.isEmpty()) {
                wrapper.apply("1 = 0");
            } else {
                List<String> pids = problemIds;
                List<String> vids = variantIds;
                wrapper.and(inner -> {
                    if (!pids.isEmpty()) {
                        inner.in(Attempt::getTargetId, pids);
                    }
                    if (!vids.isEmpty()) {
                        if (!pids.isEmpty()) {
                            inner.or();
                        }
                        inner.in(Attempt::getTargetId, vids);
                    }
                });
            }
        }

        // targetId -> [total, correct, wrong]
        Map<String, int[]> counters = new LinkedHashMap<>();
        for (Attempt row : attemptMapper.selectList(wrapper)) {
            int[] counter = counters.computeIfAbsent(row.getTargetId(), key -> new int[3]);
            counter[0]++;
            if ("correct".equals(row.getResult())) {
                counter[1]++;
            } else if ("wrong".equals(row.getResult())) {
                counter[2]++;
            }
        }

        Map<String, AttemptDtos.Stats> result = new LinkedHashMap<>();
        for (Map.Entry<String, int[]> entry : counters.entrySet()) {
            int[] counter = entry.getValue();
            int giveup = counter[0] - counter[1] - counter[2];
            double accuracy = counter[0] == 0 ? 0.0 : round4((double) counter[1] / counter[0]);
            result.put(entry.getKey(), new AttemptDtos.Stats(
                    counter[0], counter[1], counter[2], giveup, accuracy));
        }
        return new AttemptDtos.OverviewResponse(result);
    }

    public AttemptDtos.HistoryResponse history(String targetType, String targetId) {
        if (!TARGET_TYPES.contains(targetType)) {
            throw new ApiException(400, "target_type 只能是 ['problem', 'variant']");
        }
        List<Attempt> rows = attemptMapper.selectList(new LambdaQueryWrapper<Attempt>()
                .eq(Attempt::getTargetType, targetType)
                .eq(Attempt::getTargetId, targetId)
                .orderByDesc(Attempt::getId));

        List<AttemptDtos.AttemptHistoryItem> items = new ArrayList<>(rows.size());
        for (Attempt row : rows) {
            items.add(new AttemptDtos.AttemptHistoryItem(
                    row.getId(),
                    row.getResult(),
                    row.getDurationSec(),
                    row.getErrorReason(),
                    row.getSource(),
                    row.getCreatedAt()));
        }
        return new AttemptDtos.HistoryResponse(statsOf(rows), items);
    }

    private Map<String, Object> buildIdempotentResponse(Attempt existing,
                                                        AttemptDtos.CreateRequest request) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("id", existing.getId());
        payload.put("error_id", null);
        payload.put("result", existing.getResult());
        payload.put("stats", statsFor(existing.getTargetType(), existing.getTargetId()));
        if (request.userAnswers() != null && "problem".equals(existing.getTargetType())) {
            Problem problem = problemMapper.selectById(existing.getTargetId());
            if (problem != null && problem.getAnswer() != null) {
                payload.put("correct_answer", problem.getAnswer());
                payload.put("explanation", problem.getExplanation());
            }
        }
        return payload;
    }

    private Attempt findByClientToken(String clientToken) {
        return attemptMapper.selectOne(new LambdaQueryWrapper<Attempt>()
                .eq(Attempt::getClientToken, clientToken));
    }

    private TargetInfo requireTarget(String targetType, String targetId) {
        if ("problem".equals(targetType)) {
            Problem problem = problemMapper.selectById(targetId);
            if (problem == null) {
                throw new ApiException(404, "题目不存在");
            }
            return new TargetInfo(problem.getTitle(), problem.getAnswer(), problem.getExplanation());
        }
        Variant variant = variantMapper.selectById(targetId);
        if (variant == null) {
            throw new ApiException(404, "题目不存在");
        }
        return new TargetInfo(variant.getTitle(), null, null);
    }

    private AttemptDtos.Stats statsFor(String targetType, String targetId) {
        List<Attempt> rows = attemptMapper.selectList(new LambdaQueryWrapper<Attempt>()
                .eq(Attempt::getTargetType, targetType)
                .eq(Attempt::getTargetId, targetId));
        return statsOf(rows);
    }

    private AttemptDtos.Stats statsOf(List<Attempt> rows) {
        int total = rows.size();
        int correct = 0;
        int wrong = 0;
        for (Attempt row : rows) {
            if ("correct".equals(row.getResult())) {
                correct++;
            } else if ("wrong".equals(row.getResult())) {
                wrong++;
            }
        }
        int giveup = total - correct - wrong;
        double accuracy = total == 0 ? 0.0 : round4((double) correct / total);
        return new AttemptDtos.Stats(total, correct, wrong, giveup, accuracy);
    }

    private Set<String> normalizeAnswers(List<String> values) {
        Set<String> normalized = new LinkedHashSet<>();
        for (String value : values) {
            String text = value == null ? "" : value.strip();
            if (text.isEmpty()) {
                continue;
            }
            char first = Character.toUpperCase(text.charAt(0));
            if (first >= 'A' && first <= 'D') {
                normalized.add(String.valueOf(first));
            } else {
                normalized.add(text.toUpperCase(Locale.ROOT));
            }
        }
        return normalized;
    }

    private static double round4(double value) {
        return Math.round(value * 10000.0) / 10000.0;
    }

    private record TargetInfo(String title, String answer, String explanation) {
    }
}
