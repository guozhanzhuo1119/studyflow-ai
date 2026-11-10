"""题目 <-> 向量库的同步与检索封装"""

import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.problem import Chapter, KnowledgePoint, Problem, Subject
from app.rag.vector_store import vector_store

logger = logging.getLogger(__name__)

_SEARCH_FIELDS = ('id', 'title', 'source', 'tags', 'knowledge_point_id', 'status')


def problem_to_dict(
    problem: Problem,
    knowledge_point_name: Optional[str] = None,
    chapter_name: Optional[str] = None,
    subject_name: Optional[str] = None,
) -> Dict:
    data = {field: getattr(problem, field, None) for field in _SEARCH_FIELDS}
    # 科目/章节/知识点名称一并入库，让「线性代数」「洛必达法则」这类查询也能命中
    data['knowledge_point_name'] = knowledge_point_name
    data['chapter_name'] = chapter_name
    data['subject_name'] = subject_name
    return data


def _hierarchy_names(db: Session, problem: Problem) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """沿 知识点 -> 章节 -> 科目 取名称"""
    kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == problem.knowledge_point_id).first()
    if not kp:
        return None, None, None
    chapter = db.query(Chapter).filter(Chapter.id == kp.chapter_id).first()
    subject = None
    if chapter:
        subject = db.query(Subject).filter(Subject.id == chapter.subject_id).first()
    return kp.name, (chapter.name if chapter else None), (subject.name if subject else None)


def index_problem(db: Session, problem: Problem) -> None:
    """题目新增/修改后写入向量库"""
    kp_name, chapter_name, subject_name = _hierarchy_names(db, problem)
    vector_store.update(problem_to_dict(problem, kp_name, chapter_name, subject_name))


def remove_problem(problem_id: str) -> None:
    vector_store.remove([problem_id])


def sync_all_problems(db: Session) -> Dict[str, int]:
    """启动时把数据库里的题目与索引对齐"""
    rows = (
        db.query(Problem, KnowledgePoint.name, Chapter.name, Subject.name)
        .join(KnowledgePoint, Problem.knowledge_point_id == KnowledgePoint.id)
        .outerjoin(Chapter, KnowledgePoint.chapter_id == Chapter.id)
        .outerjoin(Subject, Chapter.subject_id == Subject.id)
        .all()
    )
    items = [
        problem_to_dict(problem, kp_name, chapter_name, subject_name)
        for problem, kp_name, chapter_name, subject_name in rows
    ]
    stats = vector_store.sync(items)
    logger.info('向量库同步完成：%s，当前共 %s 条', stats, len(vector_store))
    return stats


def semantic_search(query: str, top_k: int = 5, exclude_ids: Optional[List[str]] = None) -> List[Dict]:
    return vector_store.search(query, top_k=top_k, exclude_ids=exclude_ids)
