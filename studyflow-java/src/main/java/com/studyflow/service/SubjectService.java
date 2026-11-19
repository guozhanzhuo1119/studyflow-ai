package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.studyflow.common.ApiException;
import com.studyflow.dto.SubjectView;
import com.studyflow.dto.WriteDtos;
import com.studyflow.entity.Chapter;
import com.studyflow.entity.Subject;
import com.studyflow.mapper.ChapterMapper;
import com.studyflow.mapper.SubjectMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Service
public class SubjectService {

    private final SubjectMapper subjectMapper;
    private final ChapterMapper chapterMapper;

    public SubjectService(SubjectMapper subjectMapper, ChapterMapper chapterMapper) {
        this.subjectMapper = subjectMapper;
        this.chapterMapper = chapterMapper;
    }

    public List<SubjectView> list() {
        List<Subject> subjects = subjectMapper.selectList(null);
        List<SubjectView> views = new ArrayList<>(subjects.size());
        for (Subject subject : subjects) {
            views.add(toView(subject));
        }
        return views;
    }

    public SubjectView get(String subjectId) {
        Subject subject = subjectMapper.selectById(subjectId);
        if (subject == null) {
            throw new ApiException(404, "科目不存在");
        }
        return toView(subject);
    }

    public SubjectView create(WriteDtos.SubjectRequest request) {
        Subject subject = new Subject();
        subject.setId("sub-" + shortId());
        subject.setName(request.name());
        subject.setDescription(request.description());
        subject.setCreatedAt(LocalDateTime.now());
        subjectMapper.insert(subject);
        return toView(subject);
    }

    public SubjectView update(String subjectId, WriteDtos.SubjectRequest request) {
        Subject subject = subjectMapper.selectById(subjectId);
        if (subject == null) {
            throw new ApiException(404, "科目不存在");
        }
        subject.setName(request.name());
        subject.setDescription(request.description());
        subjectMapper.updateById(subject);
        return toView(subject);
    }

    private SubjectView toView(Subject subject) {
        Long chapterCount = chapterMapper.selectCount(
                new LambdaQueryWrapper<Chapter>().eq(Chapter::getSubjectId, subject.getId()));
        return new SubjectView(
                subject.getId(),
                subject.getName(),
                subject.getDescription(),
                chapterCount == null ? 0L : chapterCount,
                subject.getCreatedAt());
    }

    private static String shortId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 8);
    }
}
