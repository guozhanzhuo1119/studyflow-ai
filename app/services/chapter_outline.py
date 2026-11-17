"""教材 -> 章节草案：基于分块文本的标题识别与章节归并。

L1 链路的中间环节，不调用大模型，纯文本启发式：
识别「第X章 / 第X节 / 1.1 / 一、」等标题行，按出现顺序把分块归入章节。
识别不到标题时退化为按页范围分组，由前端人工改名后确认写入 chapters 表。
"""

import math
import re
from typing import Dict, List, Optional, Tuple

MAX_CHAPTERS = 60          # 草案最多输出章节数，超出截断
_MAX_HEAD_LINES = 12       # 只在分块前若干行里找标题
_LOOSE_HEAD_LINES = 4      # 非强特征标题只认前几行，避免正文中的列表项误判

_CN_NUM = '零〇一二三四五六七八九十百千两'
_STRONG_RE = re.compile(rf'^第\s*[{_CN_NUM}\d]+\s*[章篇部]')
_SECTION_RE = re.compile(rf'^(第\s*[{_CN_NUM}\d]+\s*[节讲])|(^\d{{1,3}}(\.\d{{1,3}}){{1,2}}\s+\S)')
_CN_HEAD_RE = re.compile(rf'^[{_CN_NUM}]+\s*[、.．]\s*\S')
_NUMBERED_RE = re.compile(r'^\d{1,2}\s*[、.．](?!\d)\s*\S')
_EN_HEAD_RE = re.compile(r'^(chapter|unit|part)\s+\d+', re.I)


def _normalize_line(line: str) -> str:
    """去掉 Markdown 井号、压缩空白，供标题判定"""
    text = re.sub(r'^#+\s*', '', (line or '').strip())
    return re.sub(r'\s+', ' ', text).strip()


def _heading_level(line: str) -> Optional[str]:
    """返回 chapter / section / None；标题不合法就返回 None"""
    text = _normalize_line(line)
    if not (2 <= len(text) <= 50):
        return None
    if text[-1] in '。！？；，、：:;,':
        return None
    if _STRONG_RE.match(text) or _EN_HEAD_RE.match(text):
        return 'chapter'
    if _CN_HEAD_RE.match(text) or _NUMBERED_RE.match(text):
        return 'chapter'
    if _SECTION_RE.match(text):
        return 'section'
    return None


def _collect_candidates(rows) -> Tuple[List[Dict], int]:
    """把分块还原成行流，收集标题候选，并记录每条候选在流中的位置
    返回 (候选列表, 行流总行数)
    """
    stream = []
    for chunk_index, row in enumerate(rows):
        lines = [line for line in (row.content or '').split('\n') if line.strip()]
        for position, line in enumerate(lines):
            stream.append({
                'line': line,
                'position': position,
                'chunk_index': chunk_index,
                'page_no': int(row.page_no or 0),
            })

    candidates = []
    for stream_index, item in enumerate(stream):
        if item['position'] >= _MAX_HEAD_LINES:
            continue
        level = _heading_level(item['line'])
        if not level:
            continue
        strong = bool(
            _STRONG_RE.match(_normalize_line(item['line'])) or _EN_HEAD_RE.match(_normalize_line(item['line']))
        )
        if not strong and item['position'] > _LOOSE_HEAD_LINES:
            continue
        candidates.append({
            'stream_index': stream_index,
            'chunk_index': item['chunk_index'],
            'page_no': item['page_no'],
            'name': _normalize_line(item['line'])[:100],
            'level': level,
        })

    return candidates, len(stream)


def _pick_level(candidates: List[Dict]) -> List[Dict]:
    """优先用章级标题；不足两条时退到节级，保证草案有粒度"""
    for level in ('chapter', 'section'):
        subset = [item for item in candidates if item['level'] == level]
        if len(subset) >= 2:
            return subset
    return []


def _add_gaps(candidates: List[Dict], stream_length: int) -> List[Dict]:
    """gap = 与下一条同级标题之间的正文行数，目录页条目通常为 0"""
    for index, item in enumerate(candidates):
        next_index = candidates[index + 1]['stream_index'] if index + 1 < len(candidates) else stream_length
        item['gap'] = next_index - item['stream_index'] - 1
    return candidates


def _dedupe(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    """丢弃紧贴下一条标题的候选（多为目录行），同名只留第一次（多为正文首次出现）
    返回 (保留列表, 是否丢弃了开头内容)
    """
    kept, seen_names = [], set()
    for item in candidates:
        if item['gap'] <= 0:
            continue
        key = re.sub(r'\s+', '', item['name']).lower()
        if not key or key in seen_names:
            continue
        kept.append(item)
        seen_names.add(key)
    return kept, bool(kept) and kept[0]['chunk_index'] > 0


def _fallback(rows, title: str) -> List[Dict]:
    """没有标题特征时，按页范围临时分组"""
    pages = sorted({int(row.page_no or 0) for row in rows})
    if not pages:
        return []
    if len(pages) <= 1:
        return [{
            'name': (title or '全书')[:100],
            'start_page': pages[0] or 1,
            'end_page': pages[-1] or 1,
            'page_count': 1,
            'chunk_count': len(rows),
        }]

    step = max(1, math.ceil(len(pages) / 8))
    chapters = []
    for offset in range(0, len(pages), step):
        segment = pages[offset:offset + step]
        start, end = segment[0], segment[-1]
        chapters.append({
            'name': f'第 {start}–{end} 页',
            'start_page': start,
            'end_page': end,
            'page_count': end - start + 1,
            'chunk_count': sum(1 for row in rows if start <= int(row.page_no or 0) <= end),
        })
    return chapters


def extract_chapter_text(rows, chapter_name: str, limit: int = 6000) -> str:
    """在分块行流里定位与 chapter_name 匹配的标题，返回该章正文（到下一章标题为止）

    L2 出题用：章节本身不存正文，只能按同名标题回到教材分块里取。
    找不到匹配标题时返回空串，由调用方提示「先在知识库解析章节」。
    """
    target = re.sub(r'\s+', '', _normalize_line(chapter_name)).lower()
    if not target:
        return ''

    lines: List[str] = []
    for row in rows:
        lines.extend((row.content or '').split('\n'))

    def key_of(line: str) -> str:
        return re.sub(r'\s+', '', _normalize_line(line)).lower()

    start, stop = None, len(lines)
    for index, line in enumerate(lines):
        key = key_of(line)
        if not key or not _heading_level(line):
            continue
        # 先求同名，再退到包含关系（章节名常被前端改短，例如「线性表」对应「第2章 线性表」）
        if key == target or (len(key) >= 3 and (target in key or key in target)):
            start = index
            break
    if start is None:
        return ''

    for index in range(start + 1, len(lines)):
        if _heading_level(lines[index]) == 'chapter' and key_of(lines[index]) != target:
            stop = index
            break

    text = '\n'.join(lines[start:stop]).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text[:limit]


def build_outline(rows, title: str = '') -> Tuple[List[Dict], List[str]]:
    """rows 为按 page_no, seq 排好序的 MaterialChunk 列表
    返回 (章节草案, 提示信息)；草案字段：name/start_page/end_page/page_count/chunk_count
    """
    warnings: List[str] = []
    if not rows:
        return [], ['这份文档没有可用的文字分块，无法生成章节草案']

    candidates, stream_length = _collect_candidates(rows)
    picked = _add_gaps(_pick_level(candidates), stream_length)

    if not picked:
        chapters = _fallback(rows, title)
        if chapters:
            warnings.append(
                f'未识别到章节标题，已按页范围临时分组（共 {len(chapters)} 章），请人工改名后确认'
            )
        return chapters, warnings

    kept, leading_dropped = _dedupe(picked)
    if not kept:
        chapters = _fallback(rows, title)
        if chapters:
            warnings.append('识别结果全部重复，已按页范围临时分组，请人工改名后确认')
        return chapters, warnings

    if leading_dropped and kept[0]['page_no'] > 1:
        warnings.append(f'第 1–{kept[0]["page_no"] - 1} 页（目录/前言）未纳入草案')

    if len(kept) > MAX_CHAPTERS:
        warnings.append(f'识别到 {len(kept)} 个标题，已截断为前 {MAX_CHAPTERS} 章')
        kept = kept[:MAX_CHAPTERS]

    chapters = []
    for position, item in enumerate(kept):
        start_chunk = item['chunk_index']
        if position + 1 < len(kept):
            end_chunk = kept[position + 1]['chunk_index'] - 1
        else:
            end_chunk = len(rows) - 1
        if end_chunk < start_chunk:
            end_chunk = start_chunk
        start_page = int(rows[start_chunk].page_no or 0)
        end_page = int(rows[end_chunk].page_no or 0) or start_page
        chapters.append({
            'name': item['name'],
            'start_page': start_page,
            'end_page': end_page,
            'page_count': max(1, end_page - start_page + 1),
            'chunk_count': end_chunk - start_chunk + 1,
        })

    warnings.append(
        f'共识别到 {len(chapters)} 章；页码取标题所在分块的页，可按实际情况微调'
    )
    return chapters, warnings
