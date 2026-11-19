"""章节正文 -> AI 单项选择题（纯函数，不接 db、不落库）。

迁移自 代码/app/services/question_generator.py：
- 保留 prompt、两次重试、逐题校验（4 选项 / answer 合法 / 题干去重）
- 去掉 Chapter / KnowledgePoint / Problem 等 ORM 依赖与写库逻辑
- 入参改为章节文本，返回 questions + dropped + drop_reasons
"""

import logging
import re
from typing import Dict, List, Tuple

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.core.errors import ServiceError
from app.llm.client import get_llm

logger = logging.getLogger(__name__)

MAX_TEXT = 6000        # 单次喂给模型的章节正文上限，避免超出上下文
MIN_TITLE = 8          # 题干最少字数
MIN_EXPLANATION = 20   # 解析最少字数


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

def _message_text(message) -> str:
    """兼容 content 为字符串或分段列表两种返回格式。"""
    content = getattr(message, 'content', message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get('type') == 'text':
                parts.append(block.get('text', ''))
        return ''.join(parts)
    return str(content)


def _strip_fences(text: str) -> str:
    text = (text or '').strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else text
        if text.endswith('```'):
            text = text[:-3]
    return text.strip()


def _ask_questions(
    chapter_title: str,
    context: str,
    count: int,
    difficulty: int,
) -> QuestionPlan:
    prompt = f"""你是一位出题老师，请只根据下面给出的章节正文出 {count} 道单项选择题。

章节：{chapter_title}
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
            raw = _message_text(llm.invoke(prompt))
            return PARSER.parse(_strip_fences(raw))
        except Exception as error:  # 模型偶发输出不合法 JSON，重试一次
            last_error = error
            logger.warning('出题解析失败（第 %s 次）：%s', attempt + 1, error)
            if 'timeout' in type(error).__name__.lower() or 'timeout' in str(error).lower():
                raise ServiceError(
                    'llm_timeout', '模型调用超时，请稍后重试', status_code=504
                ) from error
    raise ServiceError(
        'generation_failed',
        f'模型未返回可用的题目：{type(last_error).__name__}: {last_error}',
        status_code=502,
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
    if answer not in ('A', 'B', 'C', 'D'):
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


def _validate_difficulty(value: int) -> int:
    """problems.difficulty 是整数 1~5；出题接口不做 easy/medium/hard 映射。"""
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise ServiceError('invalid_difficulty', 'difficulty 必须是 1~5 的整数')
    return value


def generate_questions_payload(
    chapter_title: str,
    chapter_content: str,
    count: int = 5,
    difficulty: int = 3,
    existing_titles: List[str] | None = None,
) -> Dict:
    """纯函数：生成 -> 校验 -> 返回数组，不写库。"""
    chapter_title = (chapter_title or '').strip()
    chapter_content = (chapter_content or '').strip()
    if not chapter_title:
        raise ServiceError('invalid_request', 'chapter_title 不能为空')
    if not chapter_content:
        raise ServiceError('invalid_request', 'chapter_content 不能为空')
    if not 1 <= count <= 10:
        raise ServiceError('invalid_count', 'count 必须在 1~10 之间')

    difficulty = _validate_difficulty(difficulty)
    context = chapter_content[:MAX_TEXT]
    plan = _ask_questions(chapter_title, context, count, difficulty)

    if not plan.questions:
        raise ServiceError('empty_generation', '模型没有返回任何题目', status_code=502)

    existing = {
        key
        for key in (_normalize_title(title) for title in (existing_titles or []))
        if key
    }

    questions: List[Dict] = []
    drop_reasons: List[str] = []
    for index, item in enumerate(plan.questions, 1):
        data, reason = _validate(item)
        if not data:
            drop_reasons.append(f'第 {index} 题：{reason}')
            continue

        key = _normalize_title(data['title'])
        if not key or key in existing:
            drop_reasons.append(f'第 {index} 题：同章节重复')
            continue

        existing.add(key)
        # data 已经是旧库格式：title / options(A-D 数组) / answer(A-D) /
        # explanation / knowledge_point。difficulty、type、source、tags 由 Java 写。
        questions.append(data)

    return {
        'questions': questions,
        'dropped': len(drop_reasons),
        'drop_reasons': drop_reasons,
    }
