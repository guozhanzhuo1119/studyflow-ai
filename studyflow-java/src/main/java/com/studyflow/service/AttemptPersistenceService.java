package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.studyflow.entity.Attempt;
import com.studyflow.entity.ErrorAnalysis;
import com.studyflow.entity.WrongBook;
import com.studyflow.error.ErrorCatalog;
import com.studyflow.mapper.AttemptMapper;
import com.studyflow.mapper.ErrorAnalysisMapper;
import com.studyflow.mapper.WrongBookMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

/**
 * 一次作答的落库事务：attempts + 可选 error_analyses + wrong_book 同事务。
 * 任一失败（包括 client_token 唯一冲突）全部回滚，不会重复计分。
 */
@Service
public class AttemptPersistenceService {

    private final AttemptMapper attemptMapper;
    private final WrongBookMapper wrongBookMapper;
    private final ErrorAnalysisMapper errorAnalysisMapper;

    public AttemptPersistenceService(AttemptMapper attemptMapper,
                                     WrongBookMapper wrongBookMapper,
                                     ErrorAnalysisMapper errorAnalysisMapper) {
        this.attemptMapper = attemptMapper;
        this.wrongBookMapper = wrongBookMapper;
        this.errorAnalysisMapper = errorAnalysisMapper;
    }

    @Transactional
    public Long insert(Attempt attempt,
                       String targetTitle,
                       String errorType,
                       String errorReason,
                       LocalDateTime now) {
        attemptMapper.insert(attempt);

        Long errorId = null;
        if (errorType != null) {
            ErrorAnalysis error = new ErrorAnalysis();
            error.setProblemId(attempt.getTargetId());
            error.setProblemTitle(targetTitle);
            error.setTopic(null);
            error.setMotherProblem(null);
            error.setErrorType(errorType);
            error.setTag(null);
            String behavior = errorReason == null || errorReason.isBlank()
                    ? ErrorCatalog.specificBehaviorFallback(errorType)
                    : errorReason;
            error.setSpecificBehavior(behavior);
            error.setFirstBreakPoint(errorType);
            error.setDecompositionSentence(null);
            error.setRemedyStatus(ErrorCatalog.REMEDY_PENDING);
            error.setRemedyAction(null);
            error.setUserNote(null);
            error.setReviewed(false);
            error.setCreatedAt(now);
            error.setIdentifyLatencySec(null);
            errorAnalysisMapper.insert(error);
            errorId = error.getId();
        }

        syncWrongBook(attempt.getTargetType(), attempt.getTargetId(), targetTitle,
                attempt.getResult(), now);
        return errorId;
    }

    private void syncWrongBook(String targetType,
                               String targetId,
                               String targetTitle,
                               String result,
                               LocalDateTime now) {
        if (!"wrong".equals(result) && !"correct".equals(result)) {
            return;
        }
        WrongBook row = wrongBookMapper.selectOne(new LambdaQueryWrapper<WrongBook>()
                .eq(WrongBook::getTargetType, targetType)
                .eq(WrongBook::getTargetId, targetId));

        if ("wrong".equals(result)) {
            if (row != null) {
                row.setWrongCount((row.getWrongCount() == null ? 0 : row.getWrongCount()) + 1);
                row.setMastered(false);
                row.setMasteredAt(null);
                row.setLastWrongAt(now);
                row.setTitle(targetTitle);
                row.setUpdatedAt(now);
                wrongBookMapper.updateById(row);
            } else {
                WrongBook created = new WrongBook();
                created.setTargetType(targetType);
                created.setTargetId(targetId);
                created.setTitle(targetTitle);
                created.setWrongCount(1);
                created.setMastered(false);
                created.setLastWrongAt(now);
                created.setCreatedAt(now);
                created.setUpdatedAt(now);
                wrongBookMapper.insert(created);
            }
            return;
        }

        if (row != null && !Boolean.TRUE.equals(row.getMastered())) {
            row.setMastered(true);
            row.setMasteredAt(now);
            row.setUpdatedAt(now);
            wrongBookMapper.updateById(row);
        }
    }
}
