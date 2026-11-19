"""心月狐陪练：system prompt + 题目上下文 + 最近历史 + 用户消息 -> 一段回复。

不含 function calling、不查库、不写库、不存会话。
"""

import logging
from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.chat.prompts import build_system_prompt
from app.core.errors import ServiceError
from app.llm.client import get_llm

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20  # 与旧版 DBMessageHistory 的 limit=20 保持一致


def _format_options(options) -> str:
    """options 是旧库的 A/B/C/D 顺序数组，索引 0 即 A。"""
    if not isinstance(options, list) or not options:
        return ''
    return '；'.join(
        f'{chr(65 + index)}. {text}'
        for index, text in enumerate(options[:4])
    )


def format_question_context(question) -> str:
    """把当前题目拼成上下文；旧版 routers/chat.py 的格式，去掉 DB 查询。"""
    if question is None:
        return ''

    lines = ['【当前题目】']
    title = (getattr(question, 'title', '') or '').strip()
    if title:
        lines.append(f'题干：{title}')

    options_text = _format_options(getattr(question, 'options', None))
    if options_text:
        lines.append(f'选项：{options_text}')

    correct_answer = (getattr(question, 'correct_answer', '') or '').strip()
    if correct_answer:
        lines.append(f'正确答案：{correct_answer}')

    explanation = (getattr(question, 'explanation', '') or '').strip()
    if explanation:
        lines.append(f'解析：{explanation}')

    user_answer = (getattr(question, 'user_answer', '') or '').strip()
    if user_answer:
        lines.append(f'用户作答：{user_answer}')

    return '\n'.join(lines) if len(lines) > 1 else ''


def _to_message(item) -> BaseMessage:
    role = getattr(item, 'role', 'user')
    content = getattr(item, 'content', '')
    if role == 'assistant':
        return AIMessage(content=content)
    if role == 'system':
        return SystemMessage(content=content)
    return HumanMessage(content=content)


def _extract_text(message) -> str:
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


def chat_reply(persona: str, question, history: List, message: str) -> str:
    if persona and persona != 'xinyuehu':
        logger.warning('未知 persona=%s，回退到心月狐人设', persona)

    question_context = format_question_context(question)
    history_messages = [_to_message(item) for item in (history or [])][-MAX_HISTORY_MESSAGES:]

    messages = [
        SystemMessage(content=build_system_prompt(question_context)),
        *history_messages,
        HumanMessage(content=message),
    ]

    try:
        result = get_llm(temperature=0.3).invoke(messages)
    except ServiceError:
        raise
    except Exception as error:
        logger.exception('聊天模型调用失败')
        raise ServiceError(
            'chat_failed',
            f'模型调用失败：{type(error).__name__}: {error}',
            status_code=502,
        ) from error

    reply = _extract_text(result).strip()
    if not reply:
        raise ServiceError('empty_reply', '模型没有返回内容', status_code=502)
    return reply
