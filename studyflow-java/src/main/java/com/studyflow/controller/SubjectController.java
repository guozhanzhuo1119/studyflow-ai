package com.studyflow.controller;

import com.studyflow.dto.SubjectView;
import com.studyflow.service.SubjectService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/subjects")
public class SubjectController {

    private final SubjectService subjectService;

    public SubjectController(SubjectService subjectService) {
        this.subjectService = subjectService;
    }

    @GetMapping
    public List<SubjectView> list() {
        return subjectService.list();
    }

    @GetMapping("/{subjectId}")
    public SubjectView get(@PathVariable String subjectId) {
        return subjectService.get(subjectId);
    }
}
