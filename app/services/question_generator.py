"""章节正文 -> AI 单项选择题。

流程：定位章节正文 -> 让 DeepSeek 按 Pydantic 结构输出 -> 逐题校验（选项/答案/题干/解析/去重）
-> 合格题单事务批量入库 problems，知识点按章内同名复用或新建。
失败一律抛 GenerationError，调用方返回错误且不落库。
"""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Dict, List, Tuple

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.material import Material, MaterialChunk
from app.models.problem import Chapter, KnowledgePoint, Problem
from app.services.chapter_outline import extract_chapter_text
from app.services.llm import get_llm

logger = logging.getLogger(__name__)

MAX_TEXT = 6000        # 单次喂给模型的章节正文上限，避免超出上下文
MIN_TITLE = 8          # 题干最少字数
MIN_EXPLANATION = 20   # 解析最少字数


class GenerationError(Exception):
    """出题失败：message 直接返回给前端，status_code 决定 HTTP 状态码"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GeneratedQuestion(BaseModel):
    title: str = Field(description='题干，不含选项内容，不少于 8 个字')
    option_a: str = Field(description='A 选项的完整文字')
    option_b: str = Field(description='B 选项的完整文字')
    option_c: str = Field(description='C 选项的完整文字')
    option_d: str = Field(description='D 选项的完整文字')
    answer: str = Field(description='正确答案，只能是 A/B/C/D 之一')
    explanation: str = Field(description='解析，不少于 20 字，说明正确项为什么对、其余项为什么错')
    knowledge_point: str = Field(description='这道题考查的知识点，不超过 20 字')


class QuestionPlan(BaseModel):
    questions: List[GeneratedQuestion] = Field(description='生成的单项选择题')


PARSER = PydanticOutputParser(pydantic_object=QuestionPlan)


def _strip_fences(text: str) -> str:
    text = (text or '').strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else text
        if text.endswith('```'):
            text = text[:-3]
    return text.strip()


def _ask_questions(
    subject_name: str,
    chapter_name: str,
    context: str,
    count: int,
    difficulty: int,
) -> QuestionPlan:
    prompt = f"""你是「{subject_name}」科目的出题老师，请只根据下面给出的章节正文出 {count} 道单项选择题。

章节：{chapter_name}
难度：{difficulty}（1 最简单，5 最难）

硬性要求：
1. 每题必须有 A/B/C/D 四个选项，且只有一个正确答案，answer 只写 A、B、C、D 中的一个字母。
2. 题干不少于 8 个字，必须能独立作答，不能出现「以上都错」这类依赖选项的表述。
3. 解析不少于 20 个字，说清正确项为什么对、其余选项错在哪。
4. 全部题目必须来自给定正文，不要编造正文里没有的知识；可以换问法，但不能超纲。
5. 知识点名称不超过 20 字，尽量沿用正文里的说法，同章题目能复用的就复用。
6. 只输出 JSON，不要输出多余解释。

章节正文：
{context}

""" + PARSER.get_format_instructions()

    llm = get_llm(temperature=0.3)
    last_error = None
    for attempt in range(2):
        try:
            raw = llm.invoke(prompt).content
            return PARSER.parse(_strip_fences(raw))
        except Exception as error:  # 模型偶发输出不合法 JSON，重试一次
            last_error = error
            logger.warning('出题解析失败（第 %s 次）：%s', attempt + 1, error)
            if 'timeout' in type(error).__name__.lower() or 'timeout' in str(error).lower():
                raise GenerationError('模型调用超时，请稍后重试', status_code=504) from error
    raise GenerationError(f'模型未返回可用的题目：{type(last_error).__name__}: {last_error}')


def _fetch_chapter_text(db: Session, chapter: Chapter) -> str:
    """按科目找教材，在分块行流里定位章节标题后的正文"""
    materials = (
        db.query(Material)
        .filter(Material.subject_id == chapter.subject_id)
        .order_by(Material.created_at.desc())
        .all()
    )
    for material in materials:
        rows = (
            db.query(MaterialChunk)
            .filter(MaterialChunk.material_id == material.id)
            .order_by(MaterialChunk.page_no, MaterialChunk.seq)
            .all()
        )
        text = extract_chapter_text(rows, chapter.name, limit=MAX_TEXT)
        if text:
            logger.info('章节「%s」正文取自教材《%s》，%s 字', chapter.name, material.title, len(text))
            return text

    raise GenerationError(
        f'没有找到「{chapter.name}」的正文：请先在知识库对该科目下的教材执行「解析章节」，'
        '或确认章节名与教材标题一致',
        status_code=400,
    )


def _normalize_title(value: str) -> str:
    """去重用的标题归一化：去掉选项字母、空白、大小写差异"""
    text = re.sub(r'^[A-Da-d]\s*[.、．)）]\s*', '', (value or '').strip())
    return re.sub(r'\s+', '', text).lower()


def _validate(item: GeneratedQuestion) -> Tuple[Dict | None, str]:
    """返回 (合格题数据, 丢弃原因)；不合格时数据为 None"""
    title = (item.title or '').strip()
    options = [
        (item.option_a or '').strip(),
        (item.option_b or '').strip(),
        (item.option_c or '').strip(),
        (item.option_d or '').strip(),
    ]
    answer_text = (item.answer or '').strip().upper()
    answer = answer_text[0] if answer_text and answer_text[0] in 'ABCD' else ''
    explanation = (item.explanation or '').strip()
    knowledge_point = re.sub(r'\s+', '', item.knowledge_point or '').strip()

    if not all(options):
        return None, '选项不全'
    if answer not in 'ABCD':
        return None, '答案不合法'
    if len(re.sub(r'\s+', '', title)) < MIN_TITLE:
        return None, '题干不足 8 字'
    if len(explanation) < MIN_EXPLANATION:
        return None, '解析不足 20 字'
    if not knowledge_point:
        return None, '缺少知识点'

    return {
        'title': title[:200],
        'options': options,
        'answer': answer,
        'explanation': explanation,
        'knowledge_point': knowledge_point[:100],
    }, ''


def _existing_titles(db: Session, chapter_id: str) -> Dict[str, str]:
    """本章已有题目的归一化标题集合，用于跨批次去重"""
    rows = (
        db.query(Problem.title)
        .join(KnowledgePoint, Problem.knowledge_point_id == KnowledgePoint.id)
        .filter(KnowledgePoint.chapter_id == chapter_id)
        .all()
    )
    return {_normalize_title(title): title for (title,) in rows}


def generate_questions(
    db: Session,
    chapter: Chapter,
    count: int,
    difficulty: int,
) -> Dict:
    """生成并入库；任一步失败抛 GenerationError，不写库"""
    context = _fetch_chapter_text(db, chapter)
    subject_name = chapter.subject.name if chapter.subject else '未知科目'

    plan = _ask_questions(subject_name, chapter.name, context, count, difficulty)

    existing = _existing_titles(db, chapter.id)
    valid: List[Dict] = []
    dropped = 0
    for item in plan.questions:
        data, reason = _validate(item)
        if not data:
            dropped += 1
            logger.info('丢弃题目：%s（%s）', (item.title or '')[:30], reason)
            continue
        key = _normalize_title(data['title'])
        if not key or key in existing:
            dropped += 1
            logger.info('丢弃题目：%s（同章节重复）', data['title'][:30])
            continue
        existing[key] = data['title']
        valid.append(data)

    if not valid:
        raise GenerationError(f'生成的 {len(plan.questions)} 道题全部不合格，已丢弃，未写入题库')

    # 知识点按章内同名复用，没有就新建；全部写入只提交一次
    knowledge_points = {
        re.sub(r'\s+', '', kp.name): kp
        for kp in db.query(KnowledgePoint).filter(KnowledgePoint.chapter_id == chapter.id).all()
    }
    try:
        for data in valid:
            kp_key = data['knowledge_point']
            target = knowledge_points.get(kp_key)
            if not target:
                target = KnowledgePoint(
                    id=f'kp-{uuid.uuid4().hex[:8]}',
                    chapter_id=chapter.id,
                    name=kp_key,
                    created_at=datetime.now(),
                )
                db.add(target)
                db.flush()
                knowledge_points[kp_key] = target

            db.add(Problem(
                id=f'prob-{uuid.uuid4().hex[:8]}',
                title=data['title'],
                content=None,
                source='AI 生成',
                tags=f'{chapter.name},AI出题',
                type='single',
                options=json.dumps(data['options'], ensure_ascii=False),
                answer=data['answer'],
                explanation=data['explanation'],
                difficulty=difficulty,
                status='todo',
                knowledge_point_id=target.id,
                created_at=datetime.now(),
            ))
        db.commit()
    except Exception as error:
        db.rollback()
        raise GenerationError(f'入库失败，本次生成未保存：{error}') from error

    total = (
        db.query(Problem)
        .join(KnowledgePoint, Problem.knowledge_point_id == KnowledgePoint.id)
        .filter(KnowledgePoint.chapter_id == chapter.id)
        .count()
    )
    return {
        'generated': len(valid),
        'dropped': dropped,
        'total_in_chapter': total,
    }
