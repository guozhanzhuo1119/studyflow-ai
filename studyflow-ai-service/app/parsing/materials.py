"""教材解析：PDF/TXT/Markdown -> 文本分块 + 章节大纲草案。
将教材文本分块
"""

import base64
import binascii
import re
from pathlib import Path
from typing import List, Tuple

from app.core.errors import ServiceError
from app.parsing.chapter_outline import ChunkRow, build_outline

CHUNK_SIZE = 1000          # 单块目标字符数
MIN_CHUNK = 120            # 合并后小于该长度的块并入前一块
SCANNED_THRESHOLD = 20     # 平均每页字符数低于该值视为扫描版

ALLOWED_EXTS = {'pdf', 'txt', 'md', 'markdown'}
MAX_SIZE = 500 * 1024 * 1024
MAX_TEXT = 2_000_000

#extract_pages_from_bytes：PDF 用 pymupdf 逐页抽文字；TXT/MD 当一页
def extract_pages_from_bytes(data: bytes, file_type: str) -> List[Tuple[int, str]]:
    """返回 [(页码, 该页原文)]；TXT/MD 视为单页。

    与旧实现唯一区别：旧实现从磁盘路径读取，这里从内存字节读取（服务无状态）。
    """
    if file_type == 'pdf':
        try:
            import pymupdf
        except ImportError as error:
            raise RuntimeError('缺少 PyMuPDF，先执行 pip install pymupdf') from error
        pages = []
        with pymupdf.open(stream=data, filetype='pdf') as doc:
            for index, page in enumerate(doc):
                pages.append((index + 1, page.get_text() or ''))
        return pages

    text = data.decode('utf-8', errors='ignore')
    return [(1, text)]

#清洗——全角空格转半角、统一换行、压缩多余空白。
def normalize_text(text: str) -> str:
    text = (text or '').replace('　', ' ')
    text = re.sub(r'\r\n?', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

#贪心合并段落切块，目标每块约 1000 字。有两个防坑设计：
#超长段落按句号再切，不从句子中间截断；
#尾部短块并入前一块（第 82 行注释）——否则「第X章」这种标题会因为太短被单独丢掉。
def split_text(text: str, size: int = CHUNK_SIZE) -> List[str]:
    """按段落贪心合并，避免把句子从中间截断"""
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    pieces: List[str] = []
    buffer = ''
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 2 <= size:
            buffer = f'{buffer}\n\n{paragraph}' if buffer else paragraph
            continue
        if buffer:
            pieces.append(buffer)
        if len(paragraph) <= size:
            buffer = paragraph
        else:
            # 超长段落按句号再切
            sentences = re.split(r'(?<=[。！？；])', paragraph)
            buffer = ''
            for sentence in sentences:
                if len(buffer) + len(sentence) <= size:
                    buffer += sentence
                else:
                    if buffer:
                        pieces.append(buffer)
                    buffer = sentence
    if buffer:
        pieces.append(buffer)

    # 短块并入前一块，而不是直接丢弃：否则「第X章」这类标题会随短块一起消失
    merged: List[str] = []
    for piece in pieces:
        if merged and len(piece) < MIN_CHUNK:
            merged[-1] = f'{merged[-1]}\n\n{piece}'
        else:
            merged.append(piece)
    return merged or ([text] if text else [])

#把页文本切成分块；返回 (chunks, 总字符数, 质量标记)。
def build_chunks(pages: List[Tuple[int, str]]) -> Tuple[List[dict], int, str]:
    """把页文本切成分块；返回 (chunks, 总字符数, 质量标记)。"""
    chunks: List[dict] = []
    total = 0
    for page_no, raw in pages:
        text = normalize_text(raw)
        total += len(text)
        for seq, piece in enumerate(split_text(text)):
            chunks.append({
                'page_no': page_no,
                'seq': seq,
                'content': piece,
                'char_count': len(piece),
            })

    average = total / len(pages) if pages else 0
    quality = 'scanned' if pages and average < SCANNED_THRESHOLD else 'ok'
    return chunks, total, quality


def _file_type_from_name(filename: str) -> str:
    if not filename or '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[-1].lower()

#parse_material_payload（主入口，被 api/parse_material.py 调）：
# Base64 解码、格式/大小校验 → 抽页 → 分块 → 调 build_outline 生成大纲 → 汇总返回。
def parse_material_payload(
    filename: str = '',
    content_base64: str | None = None,
    text: str | None = None,
    title: str | None = None,
) -> dict:
    """解析教材并返回 chunks + 大纲草案；不落库、不生成 ID。"""
    filename = (filename or '').strip()

    if text is not None:
        if len(text) > MAX_TEXT:
            raise ServiceError(
                'text_too_large',
                f'正文超过 {MAX_TEXT} 字符，请拆分后导入',
                status_code=413,
            )
        if not text.strip():
            raise ServiceError('empty_file', '文件内容为空')
        pages = [(1, text)]
        file_type = 'txt'
        document_title = (title or '').strip() or (Path(filename).stem if filename else '未命名文档')
    else:
        if not content_base64:
            raise ServiceError('invalid_request', 'content_base64 与 text 至少提供一个')

        ext = _file_type_from_name(filename)
        if ext not in ALLOWED_EXTS:
            raise ServiceError(
                'unsupported_file_type',
                f'不支持的格式：{ext or "未知"}，仅允许 {sorted(ALLOWED_EXTS)}',
            )

        try:
            raw = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ServiceError('invalid_base64', 'content_base64 不是合法的 Base64') from error

        if not raw:
            raise ServiceError('empty_file', '文件内容为空')
        if len(raw) > MAX_SIZE:
            raise ServiceError(
                'file_too_large',
                f'文件超过 {MAX_SIZE // (1024 * 1024)}MB 上限',
                status_code=413,
            )

        file_type = 'md' if ext == 'markdown' else ext
        pages = extract_pages_from_bytes(raw, file_type)
        document_title = (title or '').strip() or (Path(filename).stem if filename else '未命名文档')

    chunks, char_count, quality = build_chunks(pages)
    outline_rows = [
        ChunkRow(content=chunk['content'], page_no=chunk['page_no'])
        for chunk in chunks
    ]
    outline, warnings = build_outline(outline_rows, document_title)

    if quality == 'scanned':
        warnings.insert(
            0,
            '这份文档疑似扫描版，几乎没有文字层；可改用「粘贴文字导入」后再解析章节',
        )
    if not outline:
        warnings.append('没有生成任何章节，请先检查文档是否成功抽取')

    return {
        'title': document_title,
        'file_type': file_type,
        'page_count': len(pages),
        'char_count': char_count,
        'quality': quality,
        'chunks': chunks,
        'outline': outline,
        'warnings': warnings,
    }
