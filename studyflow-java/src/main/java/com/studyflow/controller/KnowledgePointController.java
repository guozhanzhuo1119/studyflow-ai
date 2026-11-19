package com.studyflow.controller;

import com.studyflow.dto.KnowledgePointView;
import com.studyflow.dto.WriteDtos;
import com.studyflow.service.CascadeDeleteService;
import com.studyflow.service.KnowledgePointService;
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
@RequestMapping("/api/knowledge-points")
public class KnowledgePointController {

    private final KnowledgePointService knowledgePointService;
    private final CascadeDeleteService cascadeDeleteService;

    public KnowledgePointController(KnowledgePointService knowledgePointService,
                                    CascadeDeleteService cascadeDeleteService) {
        this.knowledgePointService = knowledgePointService;
        this.cascadeDeleteService = cascadeDeleteService;
    }

    @GetMapping
    public List<KnowledgePointView> list(@RequestParam(value = "chapter_id", required = false) String chapterId) {
        return knowledgePointService.list(chapterId);
    }

    @GetMapping("/{knowledgePointId}")
    public KnowledgePointView get(@PathVariable String knowledgePointId) {
        return knowledgePointService.get(knowledgePointId);
    }

    @PostMapping
    public KnowledgePointView create(@RequestBody WriteDtos.KnowledgePointRequest request) {
        return knowledgePointService.create(request);
    }

    @PutMapping("/{knowledgePointId}")
    public KnowledgePointView update(@PathVariable String knowledgePointId,
                                     @RequestBody WriteDtos.KnowledgePointRequest request) {
        return knowledgePointService.update(knowledgePointId, request);
    }

    @DeleteMapping("/{knowledgePointId}")
    public WriteDtos.DeleteResponse delete(@PathVariable String knowledgePointId) {
        long deletedProblems = cascadeDeleteService.deleteKnowledgePoint(knowledgePointId);
        return new WriteDtos.DeleteResponse("删除成功", deletedProblems);
    }
}
