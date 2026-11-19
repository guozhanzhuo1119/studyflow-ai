package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.studyflow.common.ApiException;
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

import java.util.List;

/**
 * 手写级联删除（DDL 没有 ON DELETE CASCADE）：
 * Subject -> Chapter -> KnowledgePoint -> Problem -> Variant。
 * attempts / wrong_book / error_analyses 不随题目删除，与旧版一致。
 */
@Service
public class CascadeDeleteService {

    private final SubjectMapper subjectMapper;
    private final ChapterMapper chapterMapper;
    private final KnowledgePointMapper knowledgePointMapper;
    private final ProblemMapper problemMapper;
    private final VariantMapper variantMapper;

    public CascadeDeleteService(SubjectMapper subjectMapper,
                                ChapterMapper chapterMapper,
                                KnowledgePointMapper knowledgePointMapper,
                                ProblemMapper problemMapper,
                                VariantMapper variantMapper) {
        this.subjectMapper = subjectMapper;
        this.chapterMapper = chapterMapper;
        this.knowledgePointMapper = knowledgePointMapper;
        this.problemMapper = problemMapper;
        this.variantMapper = variantMapper;
    }

    @Transactional
    public long deleteSubject(String subjectId) {
        Subject subject = subjectMapper.selectById(subjectId);
        if (subject == null) {
            throw new ApiException(404, "科目不存在");
        }

        List<String> chapterIds = chapterMapper.selectList(
                        new LambdaQueryWrapper<Chapter>().eq(Chapter::getSubjectId, subjectId))
                .stream().map(Chapter::getId).toList();
        List<String> knowledgePointIds = knowledgePointIdsByChapters(chapterIds);
        List<String> problemIds = problemIdsByKnowledgePoints(knowledgePointIds);

        deleteVariants(problemIds);
        deleteProblems(problemIds);
        deleteKnowledgePoints(knowledgePointIds);
        if (!chapterIds.isEmpty()) {
            chapterMapper.delete(new LambdaQueryWrapper<Chapter>().in(Chapter::getId, chapterIds));
        }
        subjectMapper.deleteById(subjectId);
        return problemIds.size();
    }

    @Transactional
    public long deleteChapter(String chapterId) {
        Chapter chapter = chapterMapper.selectById(chapterId);
        if (chapter == null) {
            throw new ApiException(404, "章节不存在");
        }

        List<String> knowledgePointIds = knowledgePointIdsByChapter(chapterId);
        List<String> problemIds = problemIdsByKnowledgePoints(knowledgePointIds);

        deleteVariants(problemIds);
        deleteProblems(problemIds);
        deleteKnowledgePoints(knowledgePointIds);
        chapterMapper.deleteById(chapterId);
        return problemIds.size();
    }

    @Transactional
    public long deleteKnowledgePoint(String knowledgePointId) {
        KnowledgePoint knowledgePoint = knowledgePointMapper.selectById(knowledgePointId);
        if (knowledgePoint == null) {
            throw new ApiException(404, "知识点不存在");
        }

        List<String> problemIds = problemIdsByKnowledgePoint(knowledgePointId);
        deleteVariants(problemIds);
        deleteProblems(problemIds);
        knowledgePointMapper.deleteById(knowledgePointId);
        return problemIds.size();
    }

    @Transactional
    public void deleteProblem(String problemId) {
        Problem problem = problemMapper.selectById(problemId);
        if (problem == null) {
            throw new ApiException(404, "题目不存在");
        }
        variantMapper.delete(new LambdaQueryWrapper<Variant>().eq(Variant::getProblemId, problemId));
        problemMapper.deleteById(problemId);
    }

    private List<String> knowledgePointIdsByChapters(List<String> chapterIds) {
        if (chapterIds.isEmpty()) {
            return List.of();
        }
        return knowledgePointMapper.selectList(new LambdaQueryWrapper<KnowledgePoint>()
                        .in(KnowledgePoint::getChapterId, chapterIds))
                .stream().map(KnowledgePoint::getId).toList();
    }

    private List<String> knowledgePointIdsByChapter(String chapterId) {
        return knowledgePointMapper.selectList(new LambdaQueryWrapper<KnowledgePoint>()
                        .eq(KnowledgePoint::getChapterId, chapterId))
                .stream().map(KnowledgePoint::getId).toList();
    }

    private List<String> problemIdsByKnowledgePoints(List<String> knowledgePointIds) {
        if (knowledgePointIds.isEmpty()) {
            return List.of();
        }
        return problemMapper.selectList(new LambdaQueryWrapper<Problem>()
                        .in(Problem::getKnowledgePointId, knowledgePointIds))
                .stream().map(Problem::getId).toList();
    }

    private List<String> problemIdsByKnowledgePoint(String knowledgePointId) {
        return problemMapper.selectList(new LambdaQueryWrapper<Problem>()
                        .eq(Problem::getKnowledgePointId, knowledgePointId))
                .stream().map(Problem::getId).toList();
    }

    private void deleteVariants(List<String> problemIds) {
        if (!problemIds.isEmpty()) {
            variantMapper.delete(new LambdaQueryWrapper<Variant>()
                    .in(Variant::getProblemId, problemIds));
        }
    }

    private void deleteProblems(List<String> problemIds) {
        if (!problemIds.isEmpty()) {
            problemMapper.delete(new LambdaQueryWrapper<Problem>()
                    .in(Problem::getId, problemIds));
        }
    }

    private void deleteKnowledgePoints(List<String> knowledgePointIds) {
        if (!knowledgePointIds.isEmpty()) {
            knowledgePointMapper.delete(new LambdaQueryWrapper<KnowledgePoint>()
                    .in(KnowledgePoint::getId, knowledgePointIds));
        }
    }
}
