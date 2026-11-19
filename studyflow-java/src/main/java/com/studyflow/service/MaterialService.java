package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.studyflow.ai.AiClient;
import com.studyflow.ai.AiDtos;
import com.studyflow.common.ApiException;
import com.studyflow.dto.MaterialDtos;
import com.studyflow.entity.Material;
import com.studyflow.entity.MaterialChunk;
import com.studyflow.entity.Subject;
import com.studyflow.mapper.MaterialChunkMapper;
import com.studyflow.mapper.MaterialMapper;
import com.studyflow.mapper.SubjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
public class MaterialService {

    private static final Logger log = LoggerFactory.getLogger(MaterialService.class);

    private static final Set<String> ALLOWED_EXTS = Set.of("pdf", "txt", "md", "markdown");
    private static final long MAX_SIZE = 500L * 1024 * 1024;
    private static final String SCANNED_WARNING =
            "这份 PDF 几乎没有文字层（疑似扫描版），暂时无法检索，需要 OCR 后再导入";

    private final AiClient aiClient;
    private final MaterialPersistenceService materialPersistenceService;
    private final MaterialMapper materialMapper;
    private final MaterialChunkMapper materialChunkMapper;
    private final SubjectMapper subjectMapper;
    private final Path materialsDir;

    public MaterialService(AiClient aiClient,
                           MaterialPersistenceService materialPersistenceService,
                           MaterialMapper materialMapper,
                           MaterialChunkMapper materialChunkMapper,
                           SubjectMapper subjectMapper,
                           @Value("${studyflow.uploads-dir:uploads}") String uploadsDir) {
        this.aiClient = aiClient;
        this.materialPersistenceService = materialPersistenceService;
        this.materialMapper = materialMapper;
        this.materialChunkMapper = materialChunkMapper;
        this.subjectMapper = subjectMapper;
        this.materialsDir = Paths.get(uploadsDir).toAbsolutePath().normalize().resolve("materials");
    }

    public MaterialDtos.MaterialUploadView upload(MultipartFile file, String title, String subjectId) {
        if (file == null || file.isEmpty()) {
            throw new ApiException(400, "文件内容为空");
        }
        if (file.getSize() > MAX_SIZE) {
            throw new ApiException(413, "文件超过 500MB 上限");
        }

        String originalName = safeFileName(file.getOriginalFilename());
        if (originalName.isEmpty()) {
            throw new ApiException(400, "文件名为空");
        }
        String ext = extensionOf(originalName);
        if (!ALLOWED_EXTS.contains(ext)) {
            throw new ApiException(400, "不支持的格式：" + ext + "，仅允许 [md, markdown, pdf, txt]");
        }

        if (subjectId != null && !subjectId.isBlank()) {
            Subject subject = subjectMapper.selectById(subjectId);
            if (subject == null) {
                throw new ApiException(404, "科目不存在");
            }
        }

        Path target = null;
        try {
            Files.createDirectories(materialsDir);
            String safeName = shortUuid() + "_" + originalName;
            target = materialsDir.resolve(safeName).normalize();
            if (!target.startsWith(materialsDir)) {
                throw new ApiException(400, "文件名不合法");
            }
            Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);

            byte[] bytes = Files.readAllBytes(target);
            AiDtos.ParseData data = aiClient.parseMaterial(new AiDtos.ParseRequest(
                    originalName,
                    Base64.getEncoder().encodeToString(bytes),
                    null,
                    title == null ? "" : title));

            Material material = new Material();
            material.setId(UUID.randomUUID().toString());
            material.setTitle(truncate(resolveTitle(data, originalName), 200));
            material.setSubjectId(subjectId == null || subjectId.isBlank() ? null : subjectId);
            material.setFileName(truncate(originalName, 255));
            material.setFileType(resolveFileType(data, ext));
            material.setFilePath("/uploads/materials/" + safeName);
            material.setPageCount(data.pageCount() == null ? 0 : data.pageCount());
            material.setCharCount(data.charCount() == null ? 0 : data.charCount());
            material.setQuality(data.quality() == null ? "ok" : data.quality());
            material.setCreatedAt(LocalDateTime.now());

            MaterialDtos.MaterialView view = materialPersistenceService.saveParsed(material, data);
            String warning = "scanned".equals(material.getQuality()) ? SCANNED_WARNING : "";
            log.info("教材解析完成：{}（{} 页，{} 字符，{} 个分块）",
                    material.getTitle(), material.getPageCount(), material.getCharCount(),
                    data.chunks() == null ? 0 : data.chunks().size());

            return new MaterialDtos.MaterialUploadView(
                    view.id(), view.title(), view.subjectId(), view.fileName(), view.fileType(),
                    view.pageCount(), view.charCount(), view.quality(), view.createdAt(), warning);
        } catch (IOException ex) {
            deleteQuietly(target);
            throw new ApiException(500, "文件保存失败：" + ex.getMessage());
        } catch (RuntimeException ex) {
            deleteQuietly(target);
            throw ex;
        }
    }

    public List<MaterialDtos.MaterialView> list() {
        List<Material> materials = materialMapper.selectList(
                new LambdaQueryWrapper<Material>().orderByDesc(Material::getCreatedAt));
        List<MaterialDtos.MaterialView> views = new ArrayList<>(materials.size());
        for (Material material : materials) {
            views.add(materialPersistenceService.toView(material));
        }
        return views;
    }

    public MaterialDtos.OutlineResponse outline(String materialId) {
        Material material = requireMaterial(materialId);
        MaterialDtos.OutlineDraft draft = materialPersistenceService.findOutlineDraft(materialId);

        List<MaterialDtos.OutlineChapterView> chapters = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        if (draft == null) {
            warnings.add("该教材没有解析大纲，请重新上传教材生成大纲");
        } else {
            if (draft.chapters() != null) {
                for (AiDtos.OutlineItem item : draft.chapters()) {
                    chapters.add(new MaterialDtos.OutlineChapterView(
                            item.name(),
                            item.startPage(),
                            item.endPage(),
                            item.pageCount(),
                            item.chunkCount()));
                }
            }
            if (draft.warnings() != null) {
                warnings.addAll(draft.warnings());
            }
        }
        return new MaterialDtos.OutlineResponse(
                materialPersistenceService.toView(material), chapters, warnings);
    }

    public MaterialDtos.ConfirmResponse confirmOutline(String materialId,
                                                       MaterialDtos.OutlineConfirmRequest request) {
        Material material = requireMaterial(materialId);
        return materialPersistenceService.confirm(material, request);
    }

    public MaterialDtos.ChunksResponse chunks(String materialId,
                                              Integer pageFrom,
                                              Integer pageTo,
                                              Integer limit) {
        Material material = requireMaterial(materialId);
        int effectiveLimit = limit == null ? 30 : Math.max(1, Math.min(limit, 100));

        LambdaQueryWrapper<MaterialChunk> query = new LambdaQueryWrapper<MaterialChunk>()
                .eq(MaterialChunk::getMaterialId, materialId);
        if (pageFrom != null) {
            query.ge(MaterialChunk::getPageNo, pageFrom);
        }
        if (pageTo != null) {
            query.le(MaterialChunk::getPageNo, pageTo);
        }
        query.orderByAsc(MaterialChunk::getPageNo)
                .orderByAsc(MaterialChunk::getSeq)
                .last("LIMIT " + effectiveLimit);

        List<MaterialChunk> chunks = materialChunkMapper.selectList(query);
        List<MaterialDtos.ChunkView> views = new ArrayList<>(chunks.size());
        for (MaterialChunk chunk : chunks) {
            views.add(new MaterialDtos.ChunkView(
                    chunk.getPageNo(), chunk.getSeq(), chunk.getContent()));
        }
        return new MaterialDtos.ChunksResponse(
                materialPersistenceService.toView(material), views);
    }

    @Transactional
    public Map<String, Object> delete(String materialId) {
        requireMaterial(materialId);
        materialChunkMapper.delete(new LambdaQueryWrapper<MaterialChunk>()
                .eq(MaterialChunk::getMaterialId, materialId));
        materialMapper.deleteById(materialId);
        return Map.of("ok", true);
    }

    private Material requireMaterial(String materialId) {
        Material material = materialMapper.selectById(materialId);
        if (material == null) {
            throw new ApiException(404, "文档不存在");
        }
        return material;
    }

    private String resolveTitle(AiDtos.ParseData data, String fileName) {
        if (data.title() != null && !data.title().isBlank()) {
            return data.title().strip();
        }
        int dot = fileName.lastIndexOf('.');
        return dot > 0 ? fileName.substring(0, dot) : fileName;
    }

    private String resolveFileType(AiDtos.ParseData data, String ext) {
        if (data.fileType() != null && !data.fileType().isBlank()) {
            return data.fileType();
        }
        return "markdown".equals(ext) ? "md" : ext;
    }

    private String safeFileName(String filename) {
        if (filename == null) {
            return "";
        }
        String name = filename.replace('\\', '/');
        int slash = name.lastIndexOf('/');
        return slash >= 0 ? name.substring(slash + 1) : name;
    }

    private String extensionOf(String filename) {
        int dot = filename.lastIndexOf('.');
        return dot >= 0 ? filename.substring(dot + 1).toLowerCase(Locale.ROOT) : "";
    }

    private void deleteQuietly(Path path) {
        if (path == null) {
            return;
        }
        try {
            Files.deleteIfExists(path);
        } catch (IOException ex) {
            log.warn("临时文件删除失败：{}", path, ex);
        }
    }

    private static String truncate(String value, int max) {
        if (value == null) {
            return null;
        }
        return value.length() <= max ? value : value.substring(0, max);
    }

    private static String shortUuid() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 12);
    }
}
