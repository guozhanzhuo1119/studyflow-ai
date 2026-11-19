package com.studyflow.controller;

import com.studyflow.dto.ProblemSearchRequest;
import com.studyflow.dto.ProblemSearchResponse;
import com.studyflow.dto.ProblemView;
import com.studyflow.dto.WriteDtos;
import com.studyflow.service.CascadeDeleteService;
import com.studyflow.service.ProblemService;
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
import java.util.Map;

@RestController
@RequestMapping("/api/problems")
public class ProblemController {

    private final ProblemService problemService;
    private final CascadeDeleteService cascadeDeleteService;

    public ProblemController(ProblemService problemService,
                             CascadeDeleteService cascadeDeleteService) {
        this.problemService = problemService;
        this.cascadeDeleteService = cascadeDeleteService;
    }

    @GetMapping
    public List<ProblemView> list(
            @RequestParam(value = "knowledge_point_id", required = false) String knowledgePointId) {
        return problemService.list(knowledgePointId);
    }

    @GetMapping("/{problemId}")
    public ProblemView get(@PathVariable String problemId) {
        return problemService.get(problemId);
    }

    @PostMapping
    public ProblemView create(@RequestBody WriteDtos.ProblemRequest request) {
        return problemService.create(request);
    }

    @PutMapping("/{problemId}")
    public ProblemView update(@PathVariable String problemId,
                              @RequestBody WriteDtos.ProblemRequest request) {
        return problemService.update(problemId, request);
    }

    @DeleteMapping("/{problemId}")
    public Map<String, Object> delete(@PathVariable String problemId) {
        cascadeDeleteService.deleteProblem(problemId);
        return Map.of("message", "删除成功");
    }

    /**
     * 旧版与旧前端使用的是 POST /api/problems/search；
     * 同时保留 GET 查询参数形式，方便直接按契约文档联调。
     */
    @PostMapping("/search")
    public ProblemSearchResponse search(@RequestBody ProblemSearchRequest request) {
        return problemService.search(request);
    }

    @GetMapping("/search")
    public ProblemSearchResponse searchByQuery(
            @RequestParam("query") String query,
            @RequestParam(value = "top_k", required = false) Integer topK) {
        return problemService.search(new ProblemSearchRequest(query, topK));
    }
}
