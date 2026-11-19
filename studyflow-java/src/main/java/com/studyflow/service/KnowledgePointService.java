package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.studyflow.common.ApiException;
import com.studyflow.dto.KnowledgePointView;
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
import java.util.List;

@Service
public class KnowledgePointService {

    private final KnowledgePointMapper knowledgePointMapper;
    private final ChapterMapper chapterMapper;
    private final SubjectMapper subjectMapper;
    private final ProblemMapper problemMapper;

    public KnowledgePointService(KnowledgePointMapper knowledgePointMapper,
                                 ChapterMapper chapterMapper,
                                 SubjectMapper subjectMapper,
                                 ProblemMapper problemMapper) {
        this.knowledgePointMapper = knowledgePointMapper;
        this.chapterMapper = chapterMapper;
        this.subjectMapper = subjectMapper;
        this.problemMapper = problemMapper;
    }

    public List<KnowledgePointView> list(String chapterId) {
        LambdaQueryWrapper<KnowledgePoint> query = new LambdaQueryWrapper<>();
        if (chapterId != null && !chapterId.isEmpty()) {
            query.eq(KnowledgePoint::getChapterId, chapterId);
        }

        List<KnowledgePoint> knowledgePoints = knowledgePointMapper.selectList(query);
        List<KnowledgePointView> views = new ArrayList<>(knowledgePoints.size());
        for (KnowledgePoint knowledgePoint : knowledgePoints) {
            views.add(toView(knowledgePoint));
        }
        return views;
    }

    public KnowledgePointView get(String knowledgePointId) {
        KnowledgePoint knowledgePoint = knowledgePointMapper.selectById(knowledgePointId);
        if (knowledgePoint == null) {
            throw new ApiException(404, "知识点不存在");
        }
        return toView(knowledgePoint);
    }

    private KnowledgePointView toView(KnowledgePoint knowledgePoint) {
        Chapter chapter = knowledgePoint.getChapterId() == null
                ? null
                : chapterMapper.selectById(knowledgePoint.getChapterId());
        Subject subject = chapter == null || chapter.getSubjectId() == null
                ? null
                : subjectMapper.selectById(chapter.getSubjectId());
        Long problemCount = problemMapper.selectCount(
                new LambdaQueryWrapper<Problem>().eq(Problem::getKnowledgePointId, knowledgePoint.getId()));
        return new KnowledgePointView(
                knowledgePoint.getId(),
                knowledgePoint.getChapterId(),
                chapter == null ? null : chapter.getName(),
                subject == null ? null : subject.getId(),
                subject == null ? null : subject.getName(),
                knowledgePoint.getName(),
                problemCount == null ? 0L : problemCount,
                knowledgePoint.getCreatedAt());
    }
}
