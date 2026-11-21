"""AI 变体题推荐（纯函数）。
这个文件是只负责出变式题的，不处理数据库
"""

import logging
from dataclasses import dataclass
from typing import Dict, List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from app.llm.client import get_llm

logger = logging.getLogger(__name__)

# 这个类就是给 API 层规定的输入结构
@dataclass
class ProblemInput:
    """母题的最小字段集合；由 API 层从请求体构造。"""

    title: str
    content: str = ''
    source: str = ''
    tags: str = ''

# 这个类也是规定输出结果的结构
class Recommendation(BaseModel):
    """单条变体题推荐"""

    title: str = Field(description='题目名称或清晰的题目描述')
    difficulty: str = Field(description='难度，只能是 easy / medium / hard 之一')
    link: str = Field(default='', description='题目的完整 URL，必须以 http:// 或 https:// 开头；不知道具体链接就留空字符串，不要填写平台名或题目出处')
    reason: str = Field(description='为什么适合作为变体，考查了什么相同的知识点或方法')

    @field_validator('difficulty')
    @classmethod
    def normalize_difficulty(cls, value: str) -> str:
        """模型偶尔会输出中文难度，统一归一化，保证前端渲染稳定"""
        mapping = {'简单': 'easy', '容易': 'easy', '中等': 'medium', '一般': 'medium',
                   '困难': 'hard', '较难': 'hard', '高': 'hard', '低': 'easy'}
        value = (value or 'medium').strip().lower()
        return mapping.get(value, value if value in {'easy', 'medium', 'hard'} else 'medium')

    @field_validator('link')
    @classmethod
    def normalize_link(cls, value: str) -> str:
        """模型常把「出处」写进 link，非 URL 会被前端当成相对路径跳转"""
        value = (value or '').strip()
        return value if value.startswith(('http://', 'https://')) else ''

# 这个类也是规定输出结果的结构
class RecommendationList(BaseModel):
    """变体题推荐结果"""

    recommendations: List[Recommendation] = Field(description='推荐出来的变体题列表')


parser = PydanticOutputParser(pydantic_object=RecommendationList)

SYSTEM_PROMPT = "你是一个刷题变体推荐助手，精通考研数学与算法竞赛题型。"

HUMAN_PROMPT = """母题信息：
- 题目：{title}
- 层级：{hierarchy}
- 来源：{source}
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
# 本期无 RAG 上下文，二期补（§14.13）；模板中的 {retrieval_context} 保留，传空字符串。
RETRIEVAL_CONTEXT = ''

#把「科目 / 章节 / 知识点」三个可能为空的字段，拼成一行人话
def _hierarchy_text(hierarchy: Dict[str, str] | None) -> str:
    """把科目 / 章节 / 知识点拼成一行可读文本"""
    if not hierarchy:
        return ''
    names = (
        hierarchy.get('subject_name'),
        hierarchy.get('chapter_name'),
        hierarchy.get('knowledge_point_name'),
    )
    return ' / '.join(name for name in names if name)

# 判断是否是考研题，是则优先推荐考研题
def _is_exam_style(problem, hierarchy) -> bool:
    source = (getattr(problem, 'source', '') or '').lower()
    hierarchy_name = _hierarchy_text(hierarchy).lower()
    keywords = ['考研', '真题', '张宇', '李永乐', '汤家凤', '数学']
    return any(k in source or k in hierarchy_name for k in keywords)

# 调用 LLM 链，用chain流水线
#chain = LangChain 用 | 运算符把「提示模板 → 大模型 → 输出解析器」三个组件拼成的一条可调用流水线。
# chain.invoke(payload) 就是把参数从流水线一头送进去、让它自动跑完所有环节、从另一头拿出结构化结果。
# 本质是**「声明式的流程编排」，替代手写的一步步命令式调用**
def _invoke_chain(payload: Dict) -> RecommendationList:
    chain = ChatPromptTemplate.from_messages([
        ('system', SYSTEM_PROMPT),
        ('human', HUMAN_PROMPT),
    ]) | get_llm(temperature=0.7) | parser
    return chain.invoke(payload)

#主入口，「把母题信息填进模板 → 用管道调模型并解析 → 重试 + 兜底」，实现变式题推荐
def recommend_variants(problem, hierarchy: Dict[str, str] | None = None, count: int = 5) -> List[Dict]:
    """根据母题推荐变体题，返回稳定的结构化列表"""
    payload = {
        'title': problem.title,
        'hierarchy': _hierarchy_text(hierarchy) or '未知',
        'source': problem.source or '未知',
        'tags': problem.tags or '无',
        'count': count,
        # 旧实现这里调用 FAISS 语义检索；本期 RAG 下线，固定为空上下文。
        'retrieval_context': RETRIEVAL_CONTEXT,
        'style_hint': EXAM_STYLE_HINT if _is_exam_style(problem, hierarchy) else DEFAULT_STYLE_HINT,
        'format_instructions': parser.get_format_instructions(),
    }

    for attempt in range(2):
        try:
            result: RecommendationList = _invoke_chain(payload)
            return [r.model_dump() for r in result.recommendations[:count]]
        except Exception as e:
            logger.warning('推荐结果解析失败（第 %s 次）：%s', attempt + 1, e)

    # 两次都失败时不再让接口 500，返回可读提示（保留旧行为）
    return [{
        'title': 'AI 生成失败，请稍后重试',
        'difficulty': 'medium',
        'link': '',
        'reason': '模型返回内容无法解析为结构化结果，可再次点击推荐。',
    }]
