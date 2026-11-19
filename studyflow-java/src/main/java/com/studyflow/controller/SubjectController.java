package com.studyflow.controller;

import com.studyflow.dto.SubjectView;
import com.studyflow.dto.WriteDtos;
import com.studyflow.service.CascadeDeleteService;
import com.studyflow.service.SubjectService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/subjects")
public class SubjectController {

    private final SubjectService subjectService;
    private final CascadeDeleteService cascadeDeleteService;

    public SubjectController(SubjectService subjectService,
                             CascadeDeleteService cascadeDeleteService) {
        this.subjectService = subjectService;
        this.cascadeDeleteService = cascadeDeleteService;
    }

    @GetMapping
    public List<SubjectView> list() {
        return subjectService.list();
    }

    @GetMapping("/{subjectId}")
    public SubjectView get(@PathVariable String subjectId) {
        return subjectService.get(subjectId);
    }

    @PostMapping
    public SubjectView create(@RequestBody WriteDtos.SubjectRequest request) {
        return subjectService.create(request);
    }

    @PutMapping("/{subjectId}")
    public SubjectView update(@PathVariable String subjectId,
                              @RequestBody WriteDtos.SubjectRequest request) {
        return subjectService.update(subjectId, request);
    }

    @DeleteMapping("/{subjectId}")
    public WriteDtos.SubjectDeleteResponse delete(@PathVariable String subjectId) {
        long deletedProblems = cascadeDeleteService.deleteSubject(subjectId);
        return new WriteDtos.SubjectDeleteResponse(0, "删除成功", deletedProblems);
    }
}
