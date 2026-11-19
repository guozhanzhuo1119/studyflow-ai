package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.studyflow.ai.AiDtos;
import com.studyflow.dto.MaterialDtos;
import com.studyflow.entity.AiJob;
import com.studyflow.entity.Chapter;
import com.studyflow.entity.Material;
import com.studyflow.entity.MaterialChunk;
import com.studyflow.entity.Subject;
import com.studyflow.mapper.AiJobMapper;
import com.studyflow.mapper.ChapterMapper;
import com.studyflow.mapper.MaterialChunkMapper;
import com.studyflow.mapper.MaterialMapper;
import com.studyflow.mapper.SubjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * 教材落库：materials + material_chunks + ai_jobs(解析大纲) 同事务写入。
 */
@Service
public class MaterialPersistenceService {

    private static final Logger log = LoggerFactory.getLogger(MaterialPersistenceService.class);
    private static final int MAX_CHAPTERS_PER_CONFIRM = 200;

    private final MaterialMapper materialMapper;
    private final MaterialChunkMapper materialChunkMapper;
    private final AiJobMapper aiJobMapper;
    private final SubjectMapper subjectMapper;
    private final ChapterMapper chapterMapper;
    private final ObjectMapper objectMapper;

    public MaterialPersistenceService(MaterialMapper materialMapper,
                                      MaterialChunkMapper materialChunkMapper,
                                      AiJobMapper aiJobMapper,
                                      SubjectMapper subjectMapper,
                                      ChapterMapper chapterMapper,
                                      ObjectMapper objectMapper) {
        this.materialMapper = materialMapper;
        this.materialChunkMapper = materialChunkMapper;
        this.aiJobMapper = aiJobMapper;
        this.subjectMapper = subjectMapper;
        this.chapterMapper = chapterMapper;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public MaterialDtos.MaterialView saveParsed(Material material, AiDtos.ParseData data) {
        materialMapper.insert(material);

        List<AiDtos.Chunk> chunks = data.chunks() == null ? List.of() : data.chunks();
        for (AiDtos.Chunk source : chunks) {
            MaterialChunk chunk = new MaterialChunk();
            chunk.setId(UUID.randomUUID().toString());
            chunk.setMaterialId(material.getId());
            chunk.setPageNo(source.pageNo());
            chunk.setSeq(source.seq());
            chunk.setContent(source.content() == null ? "" : source.content());
            chunk.setCharCount(source.charCount());
            materialChunkMapper.insert(chunk);
        }

        LocalDateTime now = LocalDateTime.now();
        AiJob job = new AiJob();
        // job- + 32 位 hex = 36 字符，与 materials.id 一一对应，GET outline 可直接按 id 读
        job.setId("job-" + material.getId().replace("-", ""));
        job.setType("parse-material");
        job.setStatus("success");
        job.setRequestJson(writeJson(Map.of("material_id", material.getId())));
        job.setResultJson(writeJson(new MaterialDtos.OutlineDraft(
                data.outline() == null ? List.of() : data.outline(),
                data.warnings() == null ? List.of() : data.warnings())));
        job.setCreatedAt(now);
        job.setFinishedAt(now);
        aiJobMapper.insert(job);

        return toView(material);
    }

    public MaterialDtos.OutlineDraft findOutlineDraft(String materialId) {
        AiJob job = aiJobMapper.selectById("job-" + materialId.replace("-", ""));
        if (job == null || job.getResultJson() == null || job.getResultJson().isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(job.getResultJson(), MaterialDtos.OutlineDraft.class);
        } catch (Exception ex) {
            log.warn("教材 {} 的大纲草案解析失败：{}", materialId, ex.getMessage());
            return null;
        }
    }

    @Transactional
    public MaterialDtos.ConfirmResponse confirm(Material material,
                                                MaterialDtos.OutlineConfirmRequest request) {
        if (request == null || request.chapters() == null) {
            throw new com.studyflow.common.ApiException(400, "没有可导入的章节（章节名不能为空）");
        }

        List<ChapterInput> items = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();
        for (MaterialDtos.OutlineConfirmChapter chapter : request.chapters()) {
            if (chapter == null) {
                continue;
            }
            String name = truncate(chapter.name() == null ? "" : chapter.name().strip(), 100);
            if (name.isEmpty() || !seen.add(name)) {
                continue;
            }
            items.add(new ChapterInput(
                    name,
                    chapter.startPage() == null ? 0 : chapter.startPage(),
                    chapter.endPage() == null ? 0 : chapter.endPage()));
        }
        if (items.isEmpty()) {
            throw new com.studyflow.common.ApiException(400, "没有可导入的章节（章节名不能为空）");
        }
        if (items.size() > MAX_CHAPTERS_PER_CONFIRM) {
            throw new com.studyflow.common.ApiException(400, "单次最多导入 200 个章节");
        }

        Subject subject;
        boolean subjectCreated = false;
        if (request.subjectId() != null && !request.subjectId().isBlank()) {
            subject = subjectMapper.selectById(request.subjectId());
            if (subject == null) {
                throw new com.studyflow.common.ApiException(404, "科目不存在");
            }
        } else {
            String subjectName = request.subjectName() == null ? "" : request.subjectName().strip();
            if (subjectName.isEmpty()) {
                subjectName = material.getTitle();
            }
            subject = new Subject();
            // 旧实现这里误用了 subj- 前缀；按 CLAUDE.md 统一为 sub-
            subject.setId("sub-" + shortId());
            subject.setName(truncate(subjectName, 100));
            subject.setDescription(truncate("由教材《" + material.getTitle() + "》解析生成", 200));
            subject.setCreatedAt(LocalDateTime.now());
            subjectMapper.insert(subject);
            subjectCreated = true;
        }

        List<Chapter> existingChapters = chapterMapper.selectList(
                new LambdaQueryWrapper<Chapter>().eq(Chapter::getSubjectId, subject.getId()));
        Set<String> existingNames = new LinkedHashSet<>();
        int maxOrder = 0;
        for (Chapter chapter : existingChapters) {
            existingNames.add(chapter.getName());
            if (chapter.getOrderNum() != null && chapter.getOrderNum() > maxOrder) {
                maxOrder = chapter.getOrderNum();
            }
        }

        List<MaterialDtos.CreatedChapterView> created = new ArrayList<>();
        List<MaterialDtos.SkippedChapterView> skipped = new ArrayList<>();
        LocalDateTime now = LocalDateTime.now();
        int order = maxOrder;
        for (ChapterInput item : items) {
            if (existingNames.contains(item.name())) {
                skipped.add(new MaterialDtos.SkippedChapterView(item.name(), "同名章节已存在"));
                continue;
            }
            order += 1;
            Chapter chapter = new Chapter();
            chapter.setId("chap-" + shortId());
            chapter.setSubjectId(subject.getId());
            chapter.setName(item.name());
            chapter.setOrderNum(order);
            chapter.setCreatedAt(now);
            chapterMapper.insert(chapter);
            existingNames.add(item.name());
            created.add(new MaterialDtos.CreatedChapterView(
                    chapter.getId(),
                    chapter.getName(),
                    subject.getId(),
                    chapter.getOrderNum(),
                    item.startPage(),
                    item.endPage()));
        }

        if (material.getSubjectId() == null) {
            material.setSubjectId(subject.getId());
            materialMapper.updateById(material);
        }

        return new MaterialDtos.ConfirmResponse(
                subject.getId(),
                subject.getName(),
                subjectCreated,
                created,
                skipped);
    }

    public MaterialDtos.MaterialView toView(Material material) {
        return new MaterialDtos.MaterialView(
                material.getId(),
                material.getTitle(),
                material.getSubjectId(),
                material.getFileName(),
                material.getFileType(),
                material.getPageCount(),
                material.getCharCount(),
                material.getQuality(),
                material.getCreatedAt());
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ex) {
            throw new IllegalStateException("教材解析结果序列化失败", ex);
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

    private record ChapterInput(String name, int startPage, int endPage) {
    }
}
