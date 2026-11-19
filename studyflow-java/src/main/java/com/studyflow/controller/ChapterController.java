package com.studyflow.controller;

import com.studyflow.dto.ChapterView;
import com.studyflow.dto.JobDtos;
import com.studyflow.dto.WriteDtos;
import com.studyflow.service.AiJobService;
import com.studyflow.service.CascadeDeleteService;
import com.studyflow.service.ChapterService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/chapters")
public class ChapterController {

    private final ChapterService chapterService;
    private final AiJobService aiJobService;
    private final CascadeDeleteService cascadeDeleteService;

    public ChapterController(ChapterService chapterService,
                             AiJobService aiJobService,
                             CascadeDeleteService cascadeDeleteService) {
        this.chapterService = chapterService;
        this.aiJobService = aiJobService;
        this.cascadeDeleteService = cascadeDeleteService;
    }

    @GetMapping
    public List<ChapterView> list(@RequestParam(value = "subject_id", required = false) String subjectId) {
        return chapterService.list(subjectId);
    }

    @GetMapping("/{chapterId}")
    public ChapterView get(@PathVariable String chapterId) {
        return chapterService.get(chapterId);
    }

    @PostMapping
    public ChapterView create(@RequestBody WriteDtos.ChapterRequest request) {
        return chapterService.create(request);
    }

    @PutMapping("/{chapterId}")
    public ChapterView update(@PathVariable String chapterId,
                              @RequestBody WriteDtos.ChapterRequest request) {
        return chapterService.update(chapterId, request);
    }

    @DeleteMapping("/{chapterId}")
    public WriteDtos.DeleteResponse delete(@PathVariable String chapterId) {
        long deletedProblems = cascadeDeleteService.deleteChapter(chapterId);
        return new WriteDtos.DeleteResponse("删除成功", deletedProblems);
    }

    /**
     * P4：出题改为异步任务，立即返回 job_id，前端轮询 GET /api/ai-jobs/{id}。
     */
    @PostMapping("/{chapterId}/generate")
    public JobDtos.GenerateJobResponse generate(
            @PathVariable String chapterId,
            @RequestBody(required = false) JobDtos.GenerateRequest request) {
        return aiJobService.createGenerateJob(chapterId, request);
    }
}
