package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.studyflow.common.ApiException;
import com.studyflow.dto.ChapterView;
import com.studyflow.dto.WriteDtos;
import com.studyflow.entity.Chapter;
import com.studyflow.entity.KnowledgePoint;
import com.studyflow.entity.Subject;
import com.studyflow.mapper.ChapterMapper;
import com.studyflow.mapper.KnowledgePointMapper;
import com.studyflow.mapper.SubjectMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Service
public class ChapterService {

    private final ChapterMapper chapterMapper;
    private final SubjectMapper subjectMapper;
    private final KnowledgePointMapper knowledgePointMapper;

    public ChapterService(ChapterMapper chapterMapper,
                          SubjectMapper subjectMapper,
                          KnowledgePointMapper knowledgePointMapper) {
        this.chapterMapper = chapterMapper;
        this.subjectMapper = subjectMapper;
        this.knowledgePointMapper = knowledgePointMapper;
    }

    public List<ChapterView> list(String subjectId) {
        LambdaQueryWrapper<Chapter> query = new LambdaQueryWrapper<>();
        // 旧版 if subject_id: 空字符串视为不筛选
        if (subjectId != null && !subjectId.isEmpty()) {
            query.eq(Chapter::getSubjectId, subjectId);
        }
        query.orderByAsc(Chapter::getOrderNum).orderByAsc(Chapter::getCreatedAt);

        List<Chapter> chapters = chapterMapper.selectList(query);
        List<ChapterView> views = new ArrayList<>(chapters.size());
        for (Chapter chapter : chapters) {
            views.add(toView(chapter));
        }
        return views;
    }

    public ChapterView get(String chapterId) {
        Chapter chapter = chapterMapper.selectById(chapterId);
        if (chapter == null) {
            throw new ApiException(404, "章节不存在");
        }
        return toView(chapter);
    }

    public ChapterView create(WriteDtos.ChapterRequest request) {
        Subject subject = request.subjectId() == null ? null : subjectMapper.selectById(request.subjectId());
        if (subject == null) {
            throw new ApiException(404, "科目不存在");
        }
        Chapter chapter = new Chapter();
        chapter.setId("chap-" + shortId());
        chapter.setSubjectId(request.subjectId());
        chapter.setName(request.name());
        chapter.setOrderNum(request.orderNum() == null ? 0 : request.orderNum());
        chapter.setCreatedAt(LocalDateTime.now());
        chapterMapper.insert(chapter);
        return toView(chapter);
    }

    public ChapterView update(String chapterId, WriteDtos.ChapterRequest request) {
        Chapter chapter = chapterMapper.selectById(chapterId);
        if (chapter == null) {
            throw new ApiException(404, "章节不存在");
        }
        chapter.setSubjectId(request.subjectId());
        chapter.setName(request.name());
        chapter.setOrderNum(request.orderNum() == null ? 0 : request.orderNum());
        chapterMapper.updateById(chapter);
        return toView(chapter);
    }

    private ChapterView toView(Chapter chapter) {
        Subject subject = chapter.getSubjectId() == null
                ? null
                : subjectMapper.selectById(chapter.getSubjectId());
        Long knowledgePointCount = knowledgePointMapper.selectCount(
                new LambdaQueryWrapper<KnowledgePoint>().eq(KnowledgePoint::getChapterId, chapter.getId()));
        return new ChapterView(
                chapter.getId(),
                chapter.getSubjectId(),
                subject == null ? null : subject.getName(),
                chapter.getName(),
                chapter.getOrderNum(),
                knowledgePointCount == null ? 0L : knowledgePointCount,
                chapter.getCreatedAt());
    }

    private static String shortId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 8);
    }
}
