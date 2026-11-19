package com.studyflow.controller;

import com.studyflow.dto.ErrorDtos;
import com.studyflow.service.ErrorService;
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
@RequestMapping("/api/errors")
public class ErrorController {

    private final ErrorService errorService;

    public ErrorController(ErrorService errorService) {
        this.errorService = errorService;
    }

    @GetMapping("/meta")
    public Map<String, Object> meta(@RequestParam(value = "topic", required = false) String topic) {
        return errorService.meta(topic);
    }

    @PostMapping("/decide")
    public ErrorDtos.DecideResponse decide(@RequestBody ErrorDtos.DecideRequest request) {
        return errorService.decide(request);
    }

    @GetMapping("/statistics")
    public Map<String, Object> statistics(
            @RequestParam(value = "practice_mode", required = false, defaultValue = "true")
            boolean practiceMode) {
        return errorService.statistics(practiceMode);
    }

    @GetMapping
    public List<ErrorDtos.RecordView> list(
            @RequestParam(value = "problem_id", required = false) String problemId,
            @RequestParam(value = "error_type", required = false) String errorType,
            @RequestParam(value = "reviewed", required = false) Boolean reviewed) {
        return errorService.list(problemId, errorType, reviewed);
    }

    @PostMapping
    public ErrorDtos.CreateResponse create(@RequestBody ErrorDtos.CreateRequest request) {
        return errorService.create(request);
    }

    @PutMapping("/{errorId}")
    public ErrorDtos.RecordView update(@PathVariable Long errorId,
                                       @RequestBody ErrorDtos.UpdateRequest request) {
        return errorService.update(errorId, request);
    }

    @DeleteMapping("/{errorId}")
    public Map<String, Object> delete(@PathVariable Long errorId) {
        return errorService.delete(errorId);
    }
}
