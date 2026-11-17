"""知识库接口：上传教材 / 文档，抽取文本并分块"""

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import get_db
from app.models.material import Material, MaterialChunk
from app.models.problem import Chapter, Subject
from app.services.chapter_outline import build_outline
from app.services.materials import extract_pages, ingest, search_chunks

router = APIRouter(prefix='/api/materials', tags=['知识库'])

ALLOWED_EXTS = {'pdf', 'txt', 'md', 'markdown'}
MAX_SIZE = 500 * 1024 * 1024
MAX_TEXT = 2_000_000
MATERIALS_DIR = Path(__file__).resolve().parent.parent.parent / 'uploads' / 'materials'
MATERIALS_DIR.mkdir(parents=True, exist_ok=True)


class OutlineChapter(BaseModel):
    name: str
    start_page: int = 0
    end_page: int = 0


class OutlineConfirm(BaseModel):
    subject_id: str | None = None
    subject_name: str | None = None
    chapters: list[OutlineChapter]


class TextImport(BaseModel):
    title: str
    content: str
    subject_id: str | None = None


def _get_material(db: Session, material_id: str) -> Material:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(404, '文档不存在')
    return material


def _serialize(material: Material) -> dict:
    return {
        'id': material.id,
        'title': material.title,
        'subject_id': material.subject_id,
        'file_name': material.file_name,
        'file_type': material.file_type,
        'page_count': material.page_count,
        'char_count': material.char_count,
        'quality': material.quality,
        'created_at': material.created_at.isoformat() if material.created_at else None,
    }


@router.post('/upload')
async def upload_material(
    file: UploadFile = File(...),
    title: str = Form(default=''),
    subject_id: str = Form(default=''),
    db: Session = Depends(get_db),
):
    """上传 PDF / TXT / Markdown，抽取文本并分块入库"""
    if not file.filename:
        raise HTTPException(400, '文件名为空')

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f'不支持的格式：{ext}，仅允许 {sorted(ALLOWED_EXTS)}')

    safe_name = f'{uuid.uuid4().hex[:12]}_{file.filename}'
    target = MATERIALS_DIR / safe_name

    # 分块落盘，避免把整本书读进内存
    size = 0
    try:
        with target.open('wb') as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_SIZE:
                    raise HTTPException(413, f'文件超过 {MAX_SIZE // (1024 * 1024)}MB 上限')
                output.write(chunk)
    except HTTPException:
        target.unlink(missing_ok=True)
        raise

    if not size:
        target.unlink(missing_ok=True)
        raise HTTPException(400, '文件内容为空')

    material = Material(
        id=str(uuid.uuid4()),
        title=(title or '').strip() or Path(file.filename).stem,
        subject_id=subject_id or None,
        file_name=file.filename,
        file_type='md' if ext == 'markdown' else ext,
        file_path=f'/uploads/materials/{safe_name}',
        page_count=0,
        char_count=0,
        quality='ok',
        created_at=datetime.now(),
    )
    db.add(material)

    try:
        pages = extract_pages(target, material.file_type)
    except Exception as error:
        db.rollback()
        target.unlink(missing_ok=True)
        raise HTTPException(400, f'解析失败：{error}')

    ingest(db, material, pages)
    db.commit()
    db.refresh(material)

    payload = _serialize(material)
    payload['warning'] = (
        '这份 PDF 几乎没有文字层（疑似扫描版），暂时无法检索，需要 OCR 后再导入'
        if material.quality == 'scanned' else ''
    )
    return payload


@router.get('')
def list_materials(db: Session = Depends(get_db)):
    """列出知识库里的全部文档"""
    rows = db.query(Material).order_by(Material.created_at.desc()).all()
    return [_serialize(row) for row in rows]


@router.get('/search')
def search_material_content(
    q: str,
    material_id: str | None = None,
    top_k: int = 3,
    db: Session = Depends(get_db),
):
    """按关键词检索文档片段，返回书名 + 页码 + 原文"""
    if not q.strip():
        raise HTTPException(400, '检索词不能为空')
    return search_chunks(db, q.strip(), material_id=material_id, top_k=min(max(top_k, 1), 10))


@router.post('/text')
def import_material_text(data: TextImport, db: Session = Depends(get_db)):
    """粘贴纯文本入库：扫描版 PDF 没有文字层时的人工替代方案"""
    title = (data.title or '').strip()
    content = (data.content or '').strip()
    if not title:
        raise HTTPException(400, '标题不能为空')
    if len(content) < 50:
        raise HTTPException(400, '正文过短（至少 50 字）')
    if len(content) > MAX_TEXT:
        raise HTTPException(413, f'正文超过 {MAX_TEXT} 字符，请拆分后导入')

    if data.subject_id:
        subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
        if not subject:
            raise HTTPException(404, '科目不存在')

    material = Material(
        id=str(uuid.uuid4()),
        title=title[:200],
        subject_id=data.subject_id or None,
        file_name=f'{title[:200]}.txt',
        file_type='txt',
        file_path='',
        page_count=0,
        char_count=0,
        quality='ok',
        created_at=datetime.now(),
    )
    db.add(material)
    ingest(db, material, [(1, content)])
    db.commit()
    db.refresh(material)
    return _serialize(material)


@router.get('/{material_id}/outline')
def get_material_outline(material_id: str, db: Session = Depends(get_db)):
    """基于已抽取的分块生成章节草案，供前端改名/勾选后确认"""
    material = _get_material(db, material_id)
    rows = db.query(MaterialChunk).filter(
        MaterialChunk.material_id == material_id
    ).order_by(MaterialChunk.page_no, MaterialChunk.seq).all()

    chapters, warnings = build_outline(rows, material.title)
    if material.quality == 'scanned':
        warnings.insert(0, '这份文档疑似扫描版，几乎没有文字层；可改用「粘贴文字导入」后再解析章节')
    if not chapters:
        warnings.append('没有生成任何章节，请先检查文档是否成功抽取')

    return {
        'material': _serialize(material),
        'chapters': chapters,
        'warnings': warnings,
    }


@router.post('/{material_id}/outline/confirm')
def confirm_material_outline(
    material_id: str,
    data: OutlineConfirm,
    db: Session = Depends(get_db),
):
    """把前端确认后的章节一次性写入 chapters 表；同名章节跳过"""
    material = _get_material(db, material_id)

    items, seen = [], set()
    for chapter in data.chapters:
        name = (chapter.name or '').strip()[:100]
        if not name or name in seen:
            continue
        seen.add(name)
        items.append((name, int(chapter.start_page or 0), int(chapter.end_page or 0)))
    if not items:
        raise HTTPException(400, '没有可导入的章节（章节名不能为空）')
    if len(items) > 200:
        raise HTTPException(400, '单次最多导入 200 个章节')

    subject_created = False
    if data.subject_id:
        subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
        if not subject:
            raise HTTPException(404, '科目不存在')
    else:
        subject = Subject(
            id=f'subj-{uuid.uuid4().hex[:8]}',
            name=(data.subject_name or '').strip()[:100] or material.title[:100],
            description=f'由教材《{material.title}》解析生成',
            created_at=datetime.now(),
        )
        db.add(subject)
        subject_created = True

    existing_names = {
        row[0] for row in db.query(Chapter.name).filter(Chapter.subject_id == subject.id).all()
    }
    max_order = db.query(func.max(Chapter.order_num)).filter(
        Chapter.subject_id == subject.id
    ).scalar() or 0

    created, skipped = [], []
    order = max_order
    for name, start_page, end_page in items:
        if name in existing_names:
            skipped.append({'name': name, 'reason': '同名章节已存在'})
            continue
        order += 1
        chapter = Chapter(
            id=f'chap-{uuid.uuid4().hex[:8]}',
            subject_id=subject.id,
            name=name,
            order_num=order,
            created_at=datetime.now(),
        )
        db.add(chapter)
        existing_names.add(name)
        created.append({
            'id': chapter.id,
            'name': name,
            'subject_id': subject.id,
            'order_num': order,
            'start_page': start_page,
            'end_page': end_page,
        })

    if not material.subject_id:
        material.subject_id = subject.id

    try:
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(400, f'写入章节失败：{error}')

    return {
        'subject_id': subject.id,
        'subject_name': subject.name,
        'subject_created': subject_created,
        'created': created,
        'skipped': skipped,
    }


@router.get('/{material_id}/chunks')
def list_chunks(
    material_id: str,
    page_from: int | None = None,
    page_to: int | None = None,
    limit: int = 30,
    db: Session = Depends(get_db),
):
    """按页读取文档原文，供预览或人工核对"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(404, '文档不存在')

    query = db.query(MaterialChunk).filter(MaterialChunk.material_id == material_id)
    if page_from:
        query = query.filter(MaterialChunk.page_no >= page_from)
    if page_to:
        query = query.filter(MaterialChunk.page_no <= page_to)

    rows = query.order_by(MaterialChunk.page_no, MaterialChunk.seq).limit(min(max(limit, 1), 100)).all()
    return {
        'material': _serialize(material),
        'chunks': [
            {'page_no': row.page_no, 'seq': row.seq, 'content': row.content}
            for row in rows
        ],
    }


@router.delete('/{material_id}')
def delete_material(material_id: str, db: Session = Depends(get_db)):
    """删除文档及其分块（磁盘文件保留，避免误删原书）"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(404, '文档不存在')
    db.delete(material)
    db.commit()
    return {'ok': True}
