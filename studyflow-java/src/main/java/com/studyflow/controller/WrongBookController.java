package com.studyflow.controller;

import com.studyflow.dto.WrongBookDtos;
import com.studyflow.service.WrongBookService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/wrong-book")
public class WrongBookController {

    private final WrongBookService wrongBookService;

    public WrongBookController(WrongBookService wrongBookService) {
        this.wrongBookService = wrongBookService;
    }

    @GetMapping
    public WrongBookDtos.ListResponse list(
            @RequestParam(value = "mastered", required = false) Boolean mastered,
            @RequestParam(value = "target_type", required = false) String targetType) {
        return wrongBookService.list(mastered, targetType);
    }
}
