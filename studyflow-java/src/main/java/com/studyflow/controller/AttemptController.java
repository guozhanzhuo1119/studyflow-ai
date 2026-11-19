package com.studyflow.controller;

import com.studyflow.dto.AttemptDtos;
import com.studyflow.service.AttemptService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/attempts")
public class AttemptController {

    private final AttemptService attemptService;

    public AttemptController(AttemptService attemptService) {
        this.attemptService = attemptService;
    }

    @PostMapping
    public Map<String, Object> create(@RequestBody AttemptDtos.CreateRequest request) {
        return attemptService.create(request);
    }

    @GetMapping("/overview")
    public AttemptDtos.OverviewResponse overview(
            @RequestParam(value = "knowledge_point_id", required = false) String knowledgePointId,
            @RequestParam(value = "problem_id", required = false) String problemId) {
        return attemptService.overview(knowledgePointId, problemId);
    }

    @GetMapping("/{targetType}/{targetId}")
    public AttemptDtos.HistoryResponse history(
            @PathVariable String targetType,
            @PathVariable String targetId) {
        return attemptService.history(targetType, targetId);
    }
}
