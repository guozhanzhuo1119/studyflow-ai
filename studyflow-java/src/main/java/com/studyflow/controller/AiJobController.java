package com.studyflow.controller;

import com.studyflow.dto.JobDtos;
import com.studyflow.service.AiJobService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/ai-jobs")
public class AiJobController {

    private final AiJobService aiJobService;

    public AiJobController(AiJobService aiJobService) {
        this.aiJobService = aiJobService;
    }

    @GetMapping("/{jobId}")
    public JobDtos.AiJobView get(@PathVariable String jobId) {
        return aiJobService.getJob(jobId);
    }
}
