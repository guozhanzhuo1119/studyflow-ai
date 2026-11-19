package com.studyflow.controller;

import com.studyflow.dto.MaterialDtos;
import com.studyflow.service.MaterialService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/materials")
public class MaterialController {

    private final MaterialService materialService;

    public MaterialController(MaterialService materialService) {
        this.materialService = materialService;
    }

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public MaterialDtos.MaterialUploadView upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "title", required = false, defaultValue = "") String title,
            @RequestParam(value = "subject_id", required = false, defaultValue = "") String subjectId) {
        return materialService.upload(file, title, subjectId);
    }

    @GetMapping
    public List<MaterialDtos.MaterialView> list() {
        return materialService.list();
    }

    @GetMapping("/{materialId}/outline")
    public MaterialDtos.OutlineResponse outline(@PathVariable String materialId) {
        return materialService.outline(materialId);
    }

    @PostMapping("/{materialId}/outline/confirm")
    public MaterialDtos.ConfirmResponse confirm(
            @PathVariable String materialId,
            @RequestBody MaterialDtos.OutlineConfirmRequest request) {
        return materialService.confirmOutline(materialId, request);
    }

    @GetMapping("/{materialId}/chunks")
    public MaterialDtos.ChunksResponse chunks(
            @PathVariable String materialId,
            @RequestParam(value = "page_from", required = false) Integer pageFrom,
            @RequestParam(value = "page_to", required = false) Integer pageTo,
            @RequestParam(value = "limit", required = false) Integer limit) {
        return materialService.chunks(materialId, pageFrom, pageTo, limit);
    }

    @DeleteMapping("/{materialId}")
    public Map<String, Object> delete(@PathVariable String materialId) {
        return materialService.delete(materialId);
    }
}
