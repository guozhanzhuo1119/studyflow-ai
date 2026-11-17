"""按一句话需求，让 AI 设计章节结构（知识点 + 母题）并落库。

与 organizer.py 的区别：organizer 只归类已有母题；本模块是从零建章节、知识点、母题。
"""

import uuid
from datetime import datetime
from typing import Dict, List

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.problem import Chapter, KnowledgePoint, Problem, Subject
from app.services.llm import get_llm


class ProblemPlan(BaseModel):
    title: str = Field(description='题目名称，带题号，例如「20. 有效的括号」')
    source: str = Field(default='', description='来源，例如「LeetCode 20」「王道 3.1」')
    tags: str = Field(default='', description='标签，逗号分隔，例如「栈,括号匹配」')


class KnowledgePointPlan(BaseModel):
    name: str = Field(description='知识点名称，不超过 20 字，体现解题套路')
    problems: List[ProblemPlan] = Field(description='该知识点下的母题')


class ChapterBuildPlan(BaseModel):
    knowledge_points: List[KnowledgePointPlan] = Field(description='2~6 个互斥知识点')
    note: str = Field(default='', description='一句话说明划分依据')


PARSER = PydanticOutputParser(pydantic_object=ChapterBuildPlan)


def _strip_fences(text: str) -> str:
    text = (text or '').strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else text
        if text.endswith('```'):
            text = text[:-3]
    return text.strip()


def _resolve_subject(db: Session, subject_name: str) -> Subject | None:
    return (
        db.query(Subject).filter(Subject.name == subject_name).first()
        or db.query(Subject).filter(Subject.name.like(f'%{subject_name}%')).first()
    )


def _ask_plan(subject_name: str, chapter_name: str, problem_count: int) -> ChapterBuildPlan:
    prompt = f"""你是算法题库的结构设计助手。请为「{subject_name}」科目设计一个「{chapter_name}」章节。

要求：
1. 先按解题套路划分 2~6 个知识点，知识点之间互斥，名称能一眼看出用什么方法。
2. 每个知识点下给出经典母题，全部知识点合计约 {problem_count} 道。
3. 母题必须是真实存在的经典题，标题带题号（LeetCode 写题号，教材题写章节号）。
4. 不要编造不存在的题目；不确定就不要写。
5. source 写清出来源，tags 用逗号分隔。

""" + PARSER.get_format_instructions()

    raw = get_llm(temperature=0.3).invoke(prompt).content
    return PARSER.parse(_strip_fences(raw))


def build_chapter(
    db: Session,
    subject_name: str,
    chapter_name: str,
    problem_count: int = 8,
    dry_run: bool = True,
) -> Dict:
    """生成章节结构方案；dry_run=False 时真正建章节、知识点和母题"""
    subject = _resolve_subject(db, subject_name)
    if not subject:
        return {'ok': False, 'message': f'没有找到科目「{subject_name}」。可以先用关键词，例如「力扣」。'}

    try:
        plan = _ask_plan(subject.name, chapter_name, problem_count)
    except Exception as error:
        return {'ok': False, 'message': f'模型未能给出可用结构：{type(error).__name__}: {error}'}

    # 去掉空名知识点和空标题题目，避免落库脏数据
    rows = []
    for knowledge_point in plan.knowledge_points:
        problems = [
            item for item in knowledge_point.problems if (item.title or '').strip()
        ]
        if knowledge_point.name.strip() and problems:
            rows.append({
                'name': knowledge_point.name.strip(),
                'problems': [
                    {
                        'title': item.title.strip(),
                        'source': (item.source or '').strip(),
                        'tags': (item.tags or '').strip(),
                    }
                    for item in problems
                ],
            })

    if not rows:
        return {'ok': False, 'message': '模型给的结构是空的，请换个说法重试。'}

    chapter = (
        db.query(Chapter)
        .filter(Chapter.subject_id == subject.id, Chapter.name == chapter_name)
        .first()
        or db.query(Chapter)
        .filter(Chapter.subject_id == subject.id, Chapter.name.like(f'%{chapter_name}%'))
        .first()
    )
    existing_titles = {
        title for (title,) in db.query(Problem.title).filter(Problem.title.in_([
            item['title'] for row in rows for item in row['problems']
        ])).all()
    }

    result = {
        'ok': True,
        'dry_run': dry_run,
        'subject': subject.name,
        'chapter': chapter_name,
        'chapter_exists': chapter is not None,
        'knowledge_points': [
            {
                'name': row['name'],
                'problems': [item['title'] for item in row['problems']],
                'duplicated': [item['title'] for item in row['problems'] if item['title'] in existing_titles],
            }
            for row in rows
        ],
        'note': plan.note,
        'created_chapter': False,
        'created_knowledge_points': [],
        'created_problems': 0,
        'skipped_problems': 0,
    }

    if dry_run:
        return result

    if not chapter:
        max_order = (
            db.query(Chapter.order_num)
            .filter(Chapter.subject_id == subject.id)
            .order_by(Chapter.order_num.desc())
            .first()
        )
        chapter = Chapter(
            id=str(uuid.uuid4()),
            subject_id=subject.id,
            name=chapter_name,
            order_num=(max_order[0] or 0) + 1 if max_order else 1,
            created_at=datetime.now(),
        )
        db.add(chapter)
        db.flush()
        result['created_chapter'] = True

    existing_kps = {
        kp.name: kp
        for kp in db.query(KnowledgePoint).filter(KnowledgePoint.chapter_id == chapter.id).all()
    }
    for row in rows:
        target = existing_kps.get(row['name'])
        if not target:
            target = KnowledgePoint(
                id=str(uuid.uuid4()),
                chapter_id=chapter.id,
                name=row['name'],
                created_at=datetime.now(),
            )
            db.add(target)
            db.flush()
            existing_kps[row['name']] = target
            result['created_knowledge_points'].append(row['name'])

        for item in row['problems']:
            if item['title'] in existing_titles:
                result['skipped_problems'] += 1
                continue
            db.add(Problem(
                id=str(uuid.uuid4()),
                title=item['title'],
                content=None,
                source=item['source'] or None,
                tags=item['tags'] or None,
                status='todo',
                knowledge_point_id=target.id,
                created_at=datetime.now(),
            ))
            existing_titles.add(item['title'])
            result['created_problems'] += 1

    db.commit()
    return result
