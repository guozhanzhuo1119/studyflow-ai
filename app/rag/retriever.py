"""题目 <-> 向量库的同步与检索封装"""

import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.problem import Problem, Category
from app.rag.vector_store import vector_store

logger = logging.getLogger(__name__)

_SEARCH_FIELDS = ('id', 'title', 'source', 'tags', 'category_id', 'status')


def problem_to_dict(problem: Problem, category_name: Optional[str] = None) -> Dict:
    data = {field: getattr(problem, field, None) for field in _SEARCH_FIELDS}
    # 知识点名称一并入库，让「线性代数」这类查询也能命中
    data['category_name'] = category_name
    return data


def index_problem(db: Session, problem: Problem) -> None:
    """题目新增/修改后写入向量库"""
    category = None
    if problem.category_id:
        category = db.query(Category).filter(Category.id == problem.category_id).first()
    vector_store.update(problem_to_dict(problem, category.name if category else None))


def remove_problem(problem_id: str) -> None:
    vector_store.remove([problem_id])


def sync_all_problems(db: Session) -> Dict[str, int]:
    """启动时把数据库里的题目与索引对齐"""
    rows = (
        db.query(Problem, Category.name)
        .outerjoin(Category, Problem.category_id == Category.id)
        .all()
    )
    items = [problem_to_dict(problem, category_name) for problem, category_name in rows]
    stats = vector_store.sync(items)
    logger.info('向量库同步完成：%s，当前共 %s 条', stats, len(vector_store))
    return stats


def semantic_search(query: str, top_k: int = 5, exclude_ids: Optional[List[str]] = None) -> List[Dict]:
    return vector_store.search(query, top_k=top_k, exclude_ids=exclude_ids)
