"""从知识库文档自动建题库：文档 → 章节 → 知识点 → 母题。

母题正文取自文档原文，不让模型编造；dry_run=True 时只返回方案。
"""

import uuid
from datetime import datetime
from typing import Dict, List

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.material import Material, MaterialChunk
from app.models.problem import Chapter, KnowledgePoint, Problem, Subject
from app.services.llm import get_llm

MAX_CONTEXT_CHARS = 14000#单次喂给模型的原文上限，防止超长


class ProblemSeed(BaseModel):
    title: str = Field(description='题目名称，不超过 40 字，体现考点')
    content: str = Field(description='题目正文，必须摘自原文，保留原文表述，不超过 800 字')
    source: str = Field(default='', description='来源，例如「教材 3.1 节」')
    tags: str = Field(default='', description='标签，逗号分隔')


class KnowledgePointSeed(BaseModel):
    name: str = Field(description='知识点名称，不超过 20 字')
    problems: List[ProblemSeed] = Field(description='该知识点下的母题')


class ChapterSeed(BaseModel):
    name: str = Field(description='章节名称，取自原文标题，不超过 40 字')
    knowledge_points: List[KnowledgePointSeed] = Field(description='2~6 个知识点')


class MaterialPlan(BaseModel):
    chapters: List[ChapterSeed] = Field(description='文档包含的章节，通常 1~5 个')
    note: str = Field(default='', description='一句话说明划分依据')


PARSER = PydanticOutputParser(pydantic_object=MaterialPlan)


def _strip_fences(text: str) -> str:
    text = (text or '').strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else text
        if text.endswith('```'):
            text = text[:-3]
    return text.strip()


def _resolve_material(db: Session, title: str) -> Material | None:
    return (
        db.query(Material).filter(Material.title == title).first()
        or db.query(Material).filter(Material.title.like(f'%{title}%')).first()
    )


def _resolve_subject(db: Session, subject_name: str) -> Subject | None:
    return (
        db.query(Subject).filter(Subject.name == subject_name).first()
        or db.query(Subject).filter(Subject.name.like(f'%{subject_name}%')).first()
    )


def _collect_text(db: Session, material: Material) -> str:
    chunks = (
        db.query(MaterialChunk)
        .filter(MaterialChunk.material_id == material.id)
        .order_by(MaterialChunk.page_no, MaterialChunk.seq)
        .all()
    )
    parts, total = [], 0
    for chunk in chunks:
        text = chunk.content or ''
        if not text.strip():
            continue
        if total + len(text) > MAX_CONTEXT_CHARS:
            remain = MAX_CONTEXT_CHARS - total
            if remain > 0:
                parts.append(f'[P{chunk.page_no}] ' + text[:remain])
            break
        parts.append(f'[P{chunk.page_no}] ' + text)
        total += len(text)
    return '\n\n'.join(parts)


def _ask_plan(material: Material, text: str, chapter_hint: str, max_problems: int) -> MaterialPlan:
    hint = f'\n只处理与「{chapter_hint}」相关的部分，其余内容忽略。' if chapter_hint else ''
    prompt = f"""你是题库结构设计助手，要从下面这份文档的原文中，整理出可练的题目并建立层级结构。

文档：《{material.title}》
要求：
1. 章节名取自原文标题；如果原文只有一章，就只输出一章。
2. 每章划分 2~6 个知识点，名称体现考点，不超过 20 字。
3. 全文档母题总数不超过 {max_problems} 道。
4. content 必须是原文的内容摘录（可适度删减口语化表述），不得凭空编题；原文没有的信息不要补。
5. source 写原文的节号或页码，例如「P1 3.1 节」。
6. tags 用逗号分隔，写考点关键词。{hint}

以下是原文：
---
{text}
---

""" + PARSER.get_format_instructions()

    raw = get_llm(temperature=0.2).invoke(prompt).content
    return PARSER.parse(_strip_fences(raw))


def _clean_plan(plan: MaterialPlan, max_problems: int) -> List[Dict]:
    rows, total = [], 0
    for chapter in plan.chapters:
        if not (chapter.name or '').strip():
            continue
        kps = []
        for knowledge_point in chapter.knowledge_points:
            if not (knowledge_point.name or '').strip():
                continue
            problems = []
            for item in knowledge_point.problems:
                if total >= max_problems:
                    break
                if not (item.title or '').strip() or not (item.content or '').strip():
                    continue
                problems.append({
                    'title': item.title.strip()[:200],
                    'content': item.content.strip()[:2000],
                    'source': (item.source or '').strip()[:100],
                    'tags': (item.tags or '').strip()[:200],
                })
                total += 1
            if problems:
                kps.append({'name': knowledge_point.name.strip()[:100], 'problems': problems})
        if kps:
            rows.append({'name': chapter.name.strip()[:100], 'knowledge_points': kps})
    return rows


def build_from_material(
    db: Session,
    material_title: str,
    subject_name: str,
    chapter_hint: str = '',
    max_problems: int = 15,
    dry_run: bool = True,
) -> Dict:
    material = _resolve_material(db, material_title)
    if not material:
        return {'ok': False, 'message': f'知识库里没有找到《{material_title}》，先上传该文档。'}
    if material.quality == 'scanned':
        return {'ok': False, 'message': f'《{material.title}》是扫描版，没有可检索文本，需要先 OCR。'}

    text = _collect_text(db, material)
    if len(text) < 50:
        return {'ok': False, 'message': f'《{material.title}》抽取到的文本太少，无法建题。'}

    try:
        plan = _ask_plan(material, text, chapter_hint, max_problems)
    except Exception as error:
        return {'ok': False, 'message': f'模型未能给出可用结构：{type(error).__name__}: {error}'}

    rows = _clean_plan(plan, max_problems)
    if not rows:
        return {'ok': False, 'message': '模型给的结构是空的，请换个说法或指定更具体的范围。'}

    subject = _resolve_subject(db, subject_name)
    existing_titles = {
        title for (title,) in db.query(Problem.title).all()
    }
    created_problems = []# 只给新建的题建索引，避免重复索引旧题

    result = {
        'ok': True,
        'dry_run': dry_run,
        'material': material.title,
        'subject': subject.name if subject else subject_name,
        'subject_exists': subject is not None,
        'chapters': [
            {
                'name': row['name'],
                'knowledge_points': [
                    {
                        'name': kp['name'],
                        'problems': [
                            {'title': item['title'], 'source': item['source'], 'chars': len(item['content'])}
                            for item in kp['problems']
                        ],
                    }
                    for kp in row['knowledge_points']
                ],
            }
            for row in rows
        ],
        'note': plan.note,
        'created_subject': False,
        'created_chapters': [],
        'created_knowledge_points': [],
        'created_problems': 0,
        'skipped_problems': 0,
    }

    if dry_run:
        return result

    if not subject:
        subject = Subject(
            id=str(uuid.uuid4()),
            name=subject_name,
            description=f'由文档《{material.title}》自动建立',
            created_at=datetime.now(),
        )
        db.add(subject)
        db.flush()
        result['created_subject'] = True

    existing_chapters = {
        chapter.name: chapter
        for chapter in db.query(Chapter).filter(Chapter.subject_id == subject.id).all()
    }
    max_order = (
        db.query(Chapter.order_num)
        .filter(Chapter.subject_id == subject.id)
        .order_by(Chapter.order_num.desc())
        .first()
    )
    next_order = (max_order[0] or 0) + 1 if max_order else 1

    for row in rows:
        chapter = existing_chapters.get(row['name'])
        if not chapter:
            chapter = Chapter(
                id=str(uuid.uuid4()),
                subject_id=subject.id,
                name=row['name'],
                order_num=next_order,
                created_at=datetime.now(),
            )
            db.add(chapter)
            db.flush()
            existing_chapters[row['name']] = chapter
            next_order += 1
            result['created_chapters'].append(row['name'])

        existing_kps = {
            knowledge_point.name: knowledge_point
            for knowledge_point in db.query(KnowledgePoint)
            .filter(KnowledgePoint.chapter_id == chapter.id)
            .all()
        }

        for kp_row in row['knowledge_points']:
            target_kp = existing_kps.get(kp_row['name'])
            if not target_kp:
                target_kp = KnowledgePoint(
                    id=str(uuid.uuid4()),
                    chapter_id=chapter.id,
                    name=kp_row['name'],
                    created_at=datetime.now(),
                )
                db.add(target_kp)
                db.flush()
                existing_kps[kp_row['name']] = target_kp
                result['created_knowledge_points'].append(kp_row['name'])

            for item in kp_row['problems']:
                if item['title'] in existing_titles:
                    result['skipped_problems'] += 1
                    continue
                problem = Problem(
                    id=str(uuid.uuid4()),
                    title=item['title'],
                    content=f"{item['content']}\n\n> 出自《{material.title}》{item['source'] or ''}".strip(),
                    source=item['source'] or f'《{material.title}》',
                    tags=item['tags'] or None,
                    status='todo',
                    knowledge_point_id=target_kp.id,
                    created_at=datetime.now(),
                )
                db.add(problem)
                db.flush()
                existing_titles.add(item['title'])
                created_problems.append(problem)
                result['created_problems'] += 1

    db.commit()

    # 落库后统一进向量索引，保证能被语义检索命中
    from app.rag.retriever import index_problem

    for problem in created_problems:
        try:
            index_problem(db, problem)
        except Exception:
            continue

    return result
