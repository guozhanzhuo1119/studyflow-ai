package com.studyflow.controller;

import com.studyflow.dto.VariantDtos;
import com.studyflow.service.VariantService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

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

    @PostMapping
    public VariantDtos.VariantView create(@RequestBody VariantDtos.VariantCreateRequest request) {
        return variantService.create(request);
    }

    /** 只保存前端传来的推荐结果，不调用 AI。 */
    @PostMapping("/from-recommendation")
    public VariantDtos.SaveVariantsResponse saveFromRecommendation(
            @RequestBody VariantDtos.SaveFromRecommendationRequest request) {
        return variantService.saveFromRecommendation(request);
    }
}
