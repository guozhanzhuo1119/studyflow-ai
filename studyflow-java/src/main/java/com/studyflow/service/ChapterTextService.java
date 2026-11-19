package com.studyflow.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.studyflow.common.ApiException;
import com.studyflow.entity.Chapter;
import com.studyflow.entity.Material;
import com.studyflow.entity.MaterialChunk;
import com.studyflow.mapper.MaterialChunkMapper;
import com.studyflow.mapper.MaterialMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * 从教材分块里定位章节正文。
 * 算法照搬旧版 services/chapter_outline.py 的 extract_chapter_text，
 * 读取的是 Java 库里的 material_chunks，不回调 Python。
 */
@Service
public class ChapterTextService {

    private static final Logger log = LoggerFactory.getLogger(ChapterTextService.class);

    private static final int MAX_TEXT = 6000;
    private static final String CN_NUM = "零〇一二三四五六七八九十百千两";

    private static final int UNICODE = Pattern.UNICODE_CHARACTER_CLASS;

    private static final Pattern STRONG = Pattern.compile(
            "^第\\s*[" + CN_NUM + "\\d]+\\s*[章篇部]", UNICODE);
    private static final Pattern SECTION = Pattern.compile(
            "^(第\\s*[" + CN_NUM + "\\d]+\\s*[节讲])|(^\\d{1,3}(\\.\\d{1,3}){1,2}\\s+\\S)", UNICODE);
    private static final Pattern CN_HEAD = Pattern.compile(
            "^[" + CN_NUM + "]+\\s*[、.．]\\s*\\S", UNICODE);
    private static final Pattern NUMBERED = Pattern.compile(
            "^\\d{1,2}\\s*[、.．](?!\\d)\\s*\\S", UNICODE);
    private static final Pattern EN_HEAD = Pattern.compile(
            "^(chapter|unit|part)\\s+\\d+", UNICODE | Pattern.CASE_INSENSITIVE);
    private static final Pattern LEADING_HASHES = Pattern.compile("^#+\\s*", UNICODE);
    private static final Pattern WHITESPACE = Pattern.compile("\\s+", UNICODE);
    private static final Pattern THREE_NEWLINES = Pattern.compile("\\n{3,}");

    private final MaterialMapper materialMapper;
    private final MaterialChunkMapper materialChunkMapper;

    public ChapterTextService(MaterialMapper materialMapper, MaterialChunkMapper materialChunkMapper) {
        this.materialMapper = materialMapper;
        this.materialChunkMapper = materialChunkMapper;
    }

    public String extract(Chapter chapter) {
        if (chapter.getSubjectId() != null && !chapter.getSubjectId().isBlank()) {
            List<Material> materials = materialMapper.selectList(
                    new LambdaQueryWrapper<Material>()
                            .eq(Material::getSubjectId, chapter.getSubjectId())
                            .orderByDesc(Material::getCreatedAt));

            for (Material material : materials) {
                List<MaterialChunk> chunks = materialChunkMapper.selectList(
                        new LambdaQueryWrapper<MaterialChunk>()
                                .eq(MaterialChunk::getMaterialId, material.getId())
                                .orderByAsc(MaterialChunk::getPageNo)
                                .orderByAsc(MaterialChunk::getSeq));
                if (chunks.isEmpty()) {
                    continue;
                }

                List<String> lines = new ArrayList<>();
                for (MaterialChunk chunk : chunks) {
                    String content = chunk.getContent() == null ? "" : chunk.getContent();
                    for (String line : content.split("\n", -1)) {
                        lines.add(line);
                    }
                }

                String text = extractChapterText(lines, chapter.getName());
                if (!text.isEmpty()) {
                    log.info("章节「{}」正文取自教材《{}》，{} 字",
                            chapter.getName(), material.getTitle(), text.length());
                    return text;
                }
            }
        }

        throw new ApiException(400,
                "没有找到「" + chapter.getName() + "」的正文：请先在知识库对该科目下的教材执行「解析章节」，"
                        + "或确认章节名与教材标题一致");
    }

    private String extractChapterText(List<String> lines, String chapterName) {
        String target = keyOf(chapterName);
        if (target.isEmpty()) {
            return "";
        }

        int start = -1;
        for (int index = 0; index < lines.size(); index++) {
            String key = keyOf(lines.get(index));
            if (key.isEmpty() || headingLevel(lines.get(index)) == null) {
                continue;
            }
            if (key.equals(target)
                    || (key.length() >= 3 && (key.contains(target) || target.contains(key)))) {
                start = index;
                break;
            }
        }
        if (start < 0) {
            return "";
        }

        int stop = lines.size();
        for (int index = start + 1; index < lines.size(); index++) {
            if (headingLevel(lines.get(index)) == Heading.CHAPTER
                    && !keyOf(lines.get(index)).equals(target)) {
                stop = index;
                break;
            }
        }

        String text = String.join("\n", lines.subList(start, stop)).strip();
        text = THREE_NEWLINES.matcher(text).replaceAll("\n\n");
        return text.length() > MAX_TEXT ? text.substring(0, MAX_TEXT) : text;
    }

    private Heading headingLevel(String line) {
        String text = normalizeLine(line);
        if (text.length() < 2 || text.length() > 50) {
            return null;
        }
        char last = text.charAt(text.length() - 1);
        if ("。！？；，、：:;,".indexOf(last) >= 0) {
            return null;
        }
        if (STRONG.matcher(text).find() || EN_HEAD.matcher(text).find()) {
            return Heading.CHAPTER;
        }
        if (CN_HEAD.matcher(text).find() || NUMBERED.matcher(text).find()) {
            return Heading.CHAPTER;
        }
        if (SECTION.matcher(text).find()) {
            return Heading.SECTION;
        }
        return null;
    }

    private String normalizeLine(String line) {
        String text = line == null ? "" : line.strip();
        text = LEADING_HASHES.matcher(text).replaceAll("");
        return WHITESPACE.matcher(text).replaceAll(" ").strip();
    }

    private String keyOf(String line) {
        return WHITESPACE.matcher(normalizeLine(line)).replaceAll("")
                .toLowerCase(Locale.ROOT);
    }

    private enum Heading {
        CHAPTER,
        SECTION
    }
}
