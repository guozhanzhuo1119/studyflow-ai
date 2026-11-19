package com.studyflow.controller;

import com.studyflow.dto.ChapterView;
import com.studyflow.service.ChapterService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/chapters")
public class ChapterController {

    private final ChapterService chapterService;

    public ChapterController(ChapterService chapterService) {
        this.chapterService = chapterService;
    }

    @GetMapping
    public List<ChapterView> list(@RequestParam(value = "subject_id", required = false) String subjectId) {
        return chapterService.list(subjectId);
    }

    @GetMapping("/{chapterId}")
    public ChapterView get(@PathVariable String chapterId) {
        return chapterService.get(chapterId);
    }
}
