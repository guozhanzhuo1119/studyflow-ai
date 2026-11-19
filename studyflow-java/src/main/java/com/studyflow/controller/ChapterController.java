package com.studyflow.controller;

import com.studyflow.dto.ChapterView;
import com.studyflow.dto.JobDtos;
import com.studyflow.service.AiJobService;
import com.studyflow.service.ChapterService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
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

    public ChapterController(ChapterService chapterService, AiJobService aiJobService) {
        this.chapterService = chapterService;
        this.aiJobService = aiJobService;
    }

    @GetMapping
    public List<ChapterView> list(@RequestParam(value = "subject_id", required = false) String subjectId) {
        return chapterService.list(subjectId);
    }

    @GetMapping("/{chapterId}")
    public ChapterView get(@PathVariable String chapterId) {
        return chapterService.get(chapterId);
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
