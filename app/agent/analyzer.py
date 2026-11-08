"""基于 LangChain create_agent 的智能学习助手：
把工具交给模型，由模型自己决定调用哪个（Function Calling），而不是在代码里写 if-else
"""

import logging
from typing import List

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage

from app.agent.tools import analyze_weak_points, recommend_variants, search_problems
from app.services.llm import get_llm

logger = logging.getLogger(__name__)

TOOLS = [search_problems, analyze_weak_points, recommend_variants]

SYSTEM_PROMPT = """你是 StudyFlow AI 的智能学习助手，服务正在备考考研数学、刷算法题的学生。

你可以调用以下工具：
- search_problems：在题库里做语义检索，找相似题目
- analyze_weak_points：分析做题数据，找出薄弱知识点
- recommend_variants：基于母题推荐同类型变体题

调用原则：
1. 用户问「我的弱项 / 该补什么 / 学习情况」时，调用 analyze_weak_points。
2. 用户问「找题 / 有没有关于某知识点的题」时，调用 search_problems。
3. 用户要「出几道类似的题 / 推荐变体题 / 多练几道」时，调用 recommend_variants。
4. 纯知识性问题（例如某个定理怎么理解）直接回答，不必调用工具。
5. 用户问「刚才那道题」这类指代时，结合对话历史理解，不要反问用户是哪道题。

回答要求：中文、条理清晰、给具体可执行的建议，不要输出 JSON 或 Markdown 表格。"""

_agent = None


def get_agent():
    """Agent 构建成本较高，进程内复用"""
    global _agent
    if _agent is None:
        _agent = create_agent(
            get_llm(temperature=0.3),
            tools=TOOLS,
            system_prompt=SYSTEM_PROMPT,
        )
    return _agent


def _extract_text(message: BaseMessage) -> str:
    """兼容 content 为字符串或分段列表两种返回格式"""
    content = message.content
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


def run_agent(message: str, history: List[BaseMessage] | None = None) -> str:
    """带上下文的对话：历史消息来自数据库，本次消息单独传入"""
    messages: List[BaseMessage] = list(history or [])
    messages.append(HumanMessage(content=message))

    try:
        result = get_agent().invoke({'messages': messages})
        return _extract_text(result['messages'][-1])
    except Exception as e:
        logger.exception('Agent 调用失败')
        return f'AI 助手暂时不可用，请稍后重试。（{type(e).__name__}: {e}）'
