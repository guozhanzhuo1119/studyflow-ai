package com.studyflow.controller;

import com.studyflow.dto.KnowledgePointView;
import com.studyflow.service.KnowledgePointService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/knowledge-points")
public class KnowledgePointController {

    private final KnowledgePointService knowledgePointService;

    public KnowledgePointController(KnowledgePointService knowledgePointService) {
        this.knowledgePointService = knowledgePointService;
    }

    @GetMapping
    public List<KnowledgePointView> list(@RequestParam(value = "chapter_id", required = false) String chapterId) {
        return knowledgePointService.list(chapterId);
    }

    @GetMapping("/{knowledgePointId}")
    public KnowledgePointView get(@PathVariable String knowledgePointId) {
        return knowledgePointService.get(knowledgePointId);
    }
}
