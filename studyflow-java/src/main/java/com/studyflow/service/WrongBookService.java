package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.studyflow.dto.WrongBookDtos;
import com.studyflow.entity.Chapter;
import com.studyflow.entity.KnowledgePoint;
import com.studyflow.entity.Problem;
import com.studyflow.entity.Subject;
import com.studyflow.entity.WrongBook;
import com.studyflow.mapper.ChapterMapper;
import com.studyflow.mapper.KnowledgePointMapper;
import com.studyflow.mapper.ProblemMapper;
import com.studyflow.mapper.SubjectMapper;
import com.studyflow.mapper.WrongBookMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class WrongBookService {

    private final WrongBookMapper wrongBookMapper;
    private final ProblemMapper problemMapper;
    private final KnowledgePointMapper knowledgePointMapper;
    private final ChapterMapper chapterMapper;
    private final SubjectMapper subjectMapper;

    public WrongBookService(WrongBookMapper wrongBookMapper,
                            ProblemMapper problemMapper,
                            KnowledgePointMapper knowledgePointMapper,
                            ChapterMapper chapterMapper,
                            SubjectMapper subjectMapper) {
        this.wrongBookMapper = wrongBookMapper;
        this.problemMapper = problemMapper;
        this.knowledgePointMapper = knowledgePointMapper;
        this.chapterMapper = chapterMapper;
        this.subjectMapper = subjectMapper;
    }

    public WrongBookDtos.ListResponse list(Boolean mastered, String targetType) {
        LambdaQueryWrapper<WrongBook> query = new LambdaQueryWrapper<>();
        if (mastered != null) {
            query.eq(WrongBook::getMastered, mastered);
        }
        if (targetType != null && !targetType.isBlank()) {
            query.eq(WrongBook::getTargetType, targetType);
        }

        List<WrongBook> rows = wrongBookMapper.selectList(query);
        rows.sort((a, b) -> {
            int byMastered = Boolean.compare(
                    Boolean.TRUE.equals(a.getMastered()), Boolean.TRUE.equals(b.getMastered()));
            if (byMastered != 0) {
                return byMastered;
            }
            LocalDateTime left = a.getLastWrongAt() != null ? a.getLastWrongAt() : a.getCreatedAt();
            LocalDateTime right = b.getLastWrongAt() != null ? b.getLastWrongAt() : b.getCreatedAt();
            int byTime = right.compareTo(left);
            if (byTime != 0) {
                return byTime;
            }
            return Long.compare(b.getId(), a.getId());
        });

        List<WrongBookDtos.Item> items = new ArrayList<>(rows.size());
        for (WrongBook row : rows) {
            items.add(toItem(row));
        }

        Long total = wrongBookMapper.selectCount(null);
        Long unmastered = wrongBookMapper.selectCount(new LambdaQueryWrapper<WrongBook>()
                .eq(WrongBook::getMastered, false));
        return new WrongBookDtos.ListResponse(
                items,
                total == null ? 0L : total,
                unmastered == null ? 0L : unmastered);
    }

    private WrongBookDtos.Item toItem(WrongBook row) {
        String title = row.getTitle();
        String knowledgePointId = null;
        String knowledgePointName = null;
        String chapterId = null;
        String chapterName = null;
        String subjectId = null;
        String subjectName = null;

        if ("problem".equals(row.getTargetType())) {
            Problem problem = problemMapper.selectById(row.getTargetId());
            if (problem != null) {
                title = problem.getTitle() == null ? row.getTitle() : problem.getTitle();
                KnowledgePoint knowledgePoint = problem.getKnowledgePointId() == null
                        ? null
                        : knowledgePointMapper.selectById(problem.getKnowledgePointId());
                if (knowledgePoint != null) {
                    knowledgePointId = knowledgePoint.getId();
                    knowledgePointName = knowledgePoint.getName();
                    Chapter chapter = knowledgePoint.getChapterId() == null
                            ? null
                            : chapterMapper.selectById(knowledgePoint.getChapterId());
                    if (chapter != null) {
                        chapterId = chapter.getId();
                        chapterName = chapter.getName();
                        Subject subject = chapter.getSubjectId() == null
                                ? null
                                : subjectMapper.selectById(chapter.getSubjectId());
                        if (subject != null) {
                            subjectId = subject.getId();
                            subjectName = subject.getName();
                        }
                    }
                }
            }
        }

        return new WrongBookDtos.Item(
                row.getId(),
                row.getTargetType(),
                row.getTargetId(),
                title,
                row.getWrongCount(),
                row.getMastered(),
                row.getLastWrongAt(),
                row.getMasteredAt(),
                knowledgePointId,
                knowledgePointName,
                chapterId,
                chapterName,
                subjectId,
                subjectName);
    }
}
