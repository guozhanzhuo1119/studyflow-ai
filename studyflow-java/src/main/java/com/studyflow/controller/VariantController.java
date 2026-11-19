package com.studyflow.controller;

import com.studyflow.dto.VariantDtos;
import com.studyflow.service.VariantService;
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
@RequestMapping("/api/variants")
public class VariantController {

    private final VariantService variantService;

    public VariantController(VariantService variantService) {
        this.variantService = variantService;
    }

    @GetMapping
    public List<VariantDtos.VariantView> list(
            @RequestParam(value = "problem_id", required = false) String problemId) {
        return variantService.list(problemId);
    }

    @GetMapping("/{variantId}")
    public VariantDtos.VariantView get(@PathVariable String variantId) {
        return variantService.get(variantId);
    }

    @PostMapping
    public VariantDtos.VariantView create(@RequestBody VariantDtos.VariantCreateRequest request) {
        return variantService.create(request);
    }

    @PutMapping("/{variantId}")
    public VariantDtos.VariantView update(@PathVariable String variantId,
                                          @RequestBody VariantDtos.VariantCreateRequest request) {
        return variantService.update(variantId, request);
    }

    @DeleteMapping("/{variantId}")
    public Map<String, Object> delete(@PathVariable String variantId) {
        variantService.delete(variantId);
        return Map.of("message", "删除成功");
    }

    /** 只保存前端传来的推荐结果，不调用 AI。 */
    @PostMapping("/from-recommendation")
    public VariantDtos.SaveVariantsResponse saveFromRecommendation(
            @RequestBody VariantDtos.SaveFromRecommendationRequest request) {
        return variantService.saveFromRecommendation(request);
    }
}
