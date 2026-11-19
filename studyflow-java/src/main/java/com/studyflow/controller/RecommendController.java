package com.studyflow.controller;

import com.studyflow.dto.VariantDtos;
import com.studyflow.service.VariantService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/recommend")
public class RecommendController {

    private final VariantService variantService;

    public RecommendController(VariantService variantService) {
        this.variantService = variantService;
    }

    @PostMapping
    public VariantDtos.RecommendResponse recommend(
            @RequestBody VariantDtos.RecommendRequest request) {
        return variantService.recommend(request);
    }
}
