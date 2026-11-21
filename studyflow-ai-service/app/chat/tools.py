"""心月狐的白名单只读工具。

Agent 初版把工具直连数据库（`with SessionLocal()` 写科目/章节/题目），等于把
数据主权交给模型；v2 的边界是：只挂白名单内的只读工具，工具本身无任何副作用，
写操作永远只属于 Java。新增工具必须同时满足「只读」「无外部副作用」。
"""

import ast
import logging
import math
import re

from langchain_core.tools import tool

from app.rag.search import search_semantic

logger = logging.getLogger(__name__)

MAX_EXPRESSION_LENGTH = 200
MAX_EXPONENT = 100
MAX_POW_BASE = 1e9
MAX_INT_BITS = 4096
_EXPRESSION_PATTERN = re.compile(r'[0-9+\-*/().\s^]+')

'''query 清洗 → 空则直接返回提示
   ↓
top_k 钳制到 1~10（防模型乱传参数）
   ↓
调 search_semantic() 做向量相似度检索（RAG）
   ↓
没结果 → 返回"当前没有已建索引的题目"
有结果 → 拼成带编号的多行字符串：
   "1. [题目id] 相似度 0.8732：题干内容..."'''
@tool
def rag_search_problems(query: str, top_k: int = 3) -> str:
    """只读检索题库：按自然语言查询返回最相关的已索引题目（id、相似度、题干）。
    仅用于查找题目，不能新增、修改或删除任何数据。"""
    query = (query or '').strip()
    if not query:
        return '查询关键词不能为空。'

    top_k = max(1, min(int(top_k), 10))
    results = search_semantic(query, top_k)
    if not results:
        return '当前没有已建索引的题目'

    return '\n'.join(
        f'{index}. [{item["id"]}] 相似度 {item["score"]:.4f}：{item["text"]}'
        for index, item in enumerate(results, start=1)
    )

#
def _eval_node(node):
    """递归求值 AST；只放行数字、四则运算、正负号与乘方。"""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('只允许数字参与运算')
        return value

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_node(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        elif isinstance(node.op, ast.Div):
            result = left / right
        elif isinstance(node.op, ast.Pow):
            if abs(right) > MAX_EXPONENT:
                raise ValueError('指数过大，拒绝计算')
            if abs(left) > MAX_POW_BASE:
                raise ValueError('底数过大，拒绝计算')
            result = left ** right
        else:
            raise ValueError('只允许 + - * / 和乘方运算')

        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError('结果超出范围')
        if isinstance(result, int) and result.bit_length() > MAX_INT_BITS:
            raise ValueError('结果过大，拒绝计算')
        return result

    raise ValueError('表达式包含不允许的语法（变量、函数或代码）')

#
@tool
def safe_math_eval(expression: str) -> str:
    """只读计算器：对纯算术表达式求值，支持数字、+ - * / ( ) 和 ^ 乘方。
    不接受变量、函数调用或任何代码；遇到算术题需要精确结果时使用。"""
    text = (expression or '').strip()
    if not text:
        return '表达式不能为空。'
    if len(text) > MAX_EXPRESSION_LENGTH:
        return '表达式过长，无法计算。'
    if not _EXPRESSION_PATTERN.fullmatch(text):
        return '表达式只允许数字和 + - * / ( ) . ^。'

    try:
        tree = ast.parse(text.replace('^', '**'), mode='eval')
        value = _eval_node(tree)
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as error:
        return f'计算失败：{error}'

    if isinstance(value, float):
        return f'{value:.12g}'
    return str(value)


TOOLS = [rag_search_problems, safe_math_eval]
TOOLS_BY_NAME = {item.name: item for item in TOOLS}
