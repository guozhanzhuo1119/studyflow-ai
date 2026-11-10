"""AI 变体题推荐：
1. 先用 FAISS 语义检索找到题库中与母题相似的题（RAG 检索增强）
2. 再用 PydanticOutputParser 约束 LLM 输出结构化 JSON
"""

import logging
from typing import Dict, List, Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from app.rag.retriever import semantic_search
from app.services.llm import get_llm

logger = logging.getLogger(__name__)


class Recommendation(BaseModel):
    """单条变体题推荐"""

    title: str = Field(description='题目名称或清晰的题目描述')
    difficulty: str = Field(description='难度，只能是 easy / medium / hard 之一')
    link: str = Field(default='', description='题目出处，例如「2019 年数一真题」「LeetCode」，没有就留空字符串')
    reason: str = Field(description='为什么适合作为变体，考查了什么相同的知识点或方法')

    @field_validator('difficulty')
    @classmethod
    def normalize_difficulty(cls, value: str) -> str:
        """模型偶尔会输出中文难度，统一归一化，保证前端渲染稳定"""
        mapping = {'简单': 'easy', '容易': 'easy', '中等': 'medium', '一般': 'medium',
                   '困难': 'hard', '较难': 'hard', '高': 'hard', '低': 'easy'}
        value = (value or 'medium').strip().lower()
        return mapping.get(value, value if value in {'easy', 'medium', 'hard'} else 'medium')


class RecommendationList(BaseModel):
    """变体题推荐结果"""

    recommendations: List[Recommendation] = Field(description='推荐出来的变体题列表')


parser = PydanticOutputParser(pydantic_object=RecommendationList)

SYSTEM_PROMPT = "你是一个刷题变体推荐助手，精通考研数学与算法竞赛题型。"

HUMAN_PROMPT = """母题信息：
- 题目：{title}
- 知识点：{category}
- 来源：{source}
- 难度：{difficulty}
- 标签：{tags}

{retrieval_context}

请根据这道母题考查的知识点和方法，推荐 {count} 道同类型的变体题。

要求：
1. 变体题必须和母题考查同一类知识点或解题方法，难度等于或略高于母题。
2. {style_hint}
3. 题目名称要写清楚；如果不确定具体出处，就描述题目内容，不要编造题号。
4. {format_instructions}

只输出 JSON，不要输出任何解释性文字。"""

EXAM_STYLE_HINT = '优先推荐历年真题或知名辅导书（张宇、李永乐、汤家凤等）中的题目。'
DEFAULT_STYLE_HINT = '题目描述要清晰，说明考查什么知识点或模板。'


def _is_exam_style(problem, category) -> bool:
    source = (getattr(problem, 'source', '') or '').lower()
    category_name = (category.name if category else '').lower()
    keywords = ['考研', '真题', '张宇', '李永乐', '汤家凤', '数学']
    return any(k in source or k in category_name for k in keywords)


def _build_retrieval_context(problem, category) -> str:
    """RAG：从题库里检索相似题，作为推荐时的上下文"""
    query_parts = [problem.title or '', getattr(problem, 'tags', '') or '']
    if category:
        query_parts.append(category.name)
    similar = semantic_search(' '.join(p for p in query_parts if p), top_k=3, exclude_ids=[problem.id])
    if not similar:
        return '题库中暂无相似题目。'

    lines = ['题库中与母题语义相近的题目（可作为风格参考）：']
    for i, item in enumerate(similar, 1):
        lines.append(
            f"{i}. {item.get('title')}（来源：{item.get('source') or '未知'}，"
            f"相似度：{item.get('score')}）"
        )
    return '\n'.join(lines)


def _invoke_chain(payload: Dict) -> RecommendationList:
    chain = ChatPromptTemplate.from_messages([
        ('system', SYSTEM_PROMPT),
        ('human', HUMAN_PROMPT),
    ]) | get_llm(temperature=0.7) | parser
    return chain.invoke(payload)


def recommend_variants(problem, category, count: int = 5) -> List[Dict]:
    """根据母题推荐变体题，返回稳定的结构化列表"""
    payload = {
        'title': problem.title,
        'category': category.name if category else '未知',
        'source': problem.source or '未知',
        'tags': problem.tags or '无',
        'count': count,
        'retrieval_context': _build_retrieval_context(problem, category),
        'style_hint': EXAM_STYLE_HINT if _is_exam_style(problem, category) else DEFAULT_STYLE_HINT,
        'format_instructions': parser.get_format_instructions(),
    }

    for attempt in range(2):
        try:
            result: RecommendationList = _invoke_chain(payload)
            return [r.model_dump() for r in result.recommendations[:count]]
        except Exception as e:
            logger.warning('推荐结果解析失败（第 %s 次）：%s', attempt + 1, e)

    # 两次都失败时不再让接口 500，返回可读提示
    return [{
        'title': 'AI 生成失败，请稍后重试',
        'difficulty': 'medium',
        'link': '',
        'reason': '模型返回内容无法解析为结构化结果，可再次点击推荐。',
    }]
