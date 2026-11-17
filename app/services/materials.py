"""知识库：文本抽取、分块、检索。

支持 PDF（PyMuPDF 抽文字层）、TXT、Markdown。
扫描版 PDF 没有文字层，会被标记为 quality=scanned，提示需要 OCR。
"""

import re
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models.material import Material, MaterialChunk

CHUNK_SIZE = 1000          # 单块目标字符数
MIN_CHUNK = 120            # 合并后小于该长度的块并入前一块
SCANNED_THRESHOLD = 20     # 平均每页字符数低于该值视为扫描版


def extract_pages(path: Path, file_type: str) -> List[Tuple[int, str]]:
    """返回 [(页码, 该页原文)]；TXT/MD 视为单页"""
    if file_type == 'pdf':
        try:
            import pymupdf
        except ImportError as error:
            raise RuntimeError('缺少 PyMuPDF，先执行 pip install pymupdf') from error
        pages = []
        with pymupdf.open(str(path)) as doc:
            for index, page in enumerate(doc):
                pages.append((index + 1, page.get_text() or ''))
        return pages

    text = path.read_text(encoding='utf-8', errors='ignore')
    return [(1, text)]


def normalize_text(text: str) -> str:
    text = (text or '').replace('\u3000', ' ')
    text = re.sub(r'\r\n?', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


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


def ingest(db: Session, material: Material, pages: List[Tuple[int, str]]) -> Material:
    """把抽取结果写成分块；同时更新页数、字符数、质量标记"""
    total = 0
    for page_no, raw in pages:
        text = normalize_text(raw)
        total += len(text)
        for seq, piece in enumerate(split_text(text)):
            db.add(MaterialChunk(
                id=str(uuid.uuid4()),
                material_id=material.id,
                page_no=page_no,
                seq=seq,
                content=piece,
                char_count=len(piece),
            ))

    material.page_count = len(pages)
    material.char_count = total
    average = total / len(pages) if pages else 0
    material.quality = 'scanned' if pages and average < SCANNED_THRESHOLD else 'ok'
    return material


def _bigrams(text: str) -> List[str]:
    clean = re.sub(r'\s+', '', text)
    return [clean[i:i + 2] for i in range(len(clean) - 1)]


def search_chunks(db: Session, query: str, material_id: str | None = None, top_k: int = 3) -> List[Dict]:
    """基于字符二元组的简单相关性打分；样本量下足够，且无需额外模型"""
    terms = _bigrams(query) or ([query] if query else [])
    rows = db.query(MaterialChunk).filter(
        MaterialChunk.material_id == material_id if material_id else True
    ).all()

    scored = []
    for row in rows:
        score = sum(row.content.count(term) for term in terms)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)

    picked = []
    for score, row in scored[:top_k]:
        material = db.query(Material).filter(Material.id == row.material_id).first()
        picked.append({
            'material': material.title if material else '',
            'page_no': row.page_no,
            'score': score,
            'content': row.content,
        })
    return picked
