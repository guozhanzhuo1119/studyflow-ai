"""心月狐陪练：system prompt + 题目上下文 + 最近历史 + 用户消息 -> 一段回复。

不含 function calling、不查库、不写库、不存会话。
"""

import logging
from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from app.chat.prompts import build_system_prompt
from app.chat.tools import TOOLS, TOOLS_BY_NAME
from app.core.errors import ServiceError
from app.llm.client import get_llm

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20  # 与旧版 DBMessageHistory 的 limit=20 保持一致
MAX_TOOL_ROUNDS = 3       # 工具循环上限：3 轮后强制生成最终回复，避免死循环


def _run_tool(tool_call) -> ToolMessage:
    """执行单个工具调用；未在白名单内的工具一律拒绝。"""
    name = tool_call.get('name') or ''
    args = tool_call.get('args') or {}
    call_id = tool_call.get('id') or ''

    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        logger.warning('拒绝白名单外的工具：%s', name)
        content = f'工具 {name} 不在白名单内，无法执行。'
    else:
        logger.info('调用工具 %s 参数=%s', name, args)
        try:
            content = tool.invoke(args)
        except Exception as error:  # 工具失败也要回传给模型，不能中断对话
            logger.warning('工具 %s 执行失败：%s', name, error)
            content = f'工具执行失败：{error}'
        else:
            logger.info('工具 %s 返回：%s', name, content[:200])

    return ToolMessage(content=content, tool_call_id=call_id, name=name)


def _invoke_with_tools(model, messages: list) -> BaseMessage:
    """模型决定调工具 -> 代码执行 -> 结果回传，最多 MAX_TOOL_ROUNDS 轮。"""
    tool_model = model.bind_tools(TOOLS)
    for round_no in range(1, MAX_TOOL_ROUNDS + 1):
        result = tool_model.invoke(messages)
        tool_calls = getattr(result, 'tool_calls', None) or []
        if not tool_calls:
            return result

        logger.info(
            '第 %s/%s 轮工具调用：%s',
            round_no,
            MAX_TOOL_ROUNDS,
            [(call.get('name'), call.get('args')) for call in tool_calls],
        )
        messages.append(result)
        for call in tool_calls:
            messages.append(_run_tool(call))

    logger.warning('工具调用达到 %s 轮上限，强制生成最终回复', MAX_TOOL_ROUNDS)
    return model.invoke(messages)


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


def chat_reply(persona: str, question, history: List, message: str, use_tools: bool = True) -> str:
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
        model = get_llm(temperature=0.3)
        if use_tools:
            result = _invoke_with_tools(model, messages)
        else:
            # 完全走旧路径：不 bind_tools，单次调用
            result = model.invoke(messages)
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
