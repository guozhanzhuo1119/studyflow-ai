"""层级删除：删掉科目/章节/知识点时，把后代母题从 FAISS 里一并清掉"""

import logging
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.problem import Chapter, KnowledgePoint, Problem
from app.rag.vector_store import vector_store

logger = logging.getLogger(__name__)


def collect_problem_ids_by_subject(db: Session, subject_id: str) -> List[str]:
    rows = (
        db.query(Problem.id)
        .join(KnowledgePoint, Problem.knowledge_point_id == KnowledgePoint.id)
        .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
        .filter(Chapter.subject_id == subject_id)
        .all()
    )
    return [row[0] for row in rows]


def collect_problem_ids_by_chapter(db: Session, chapter_id: str) -> List[str]:
    rows = (
        db.query(Problem.id)
        .join(KnowledgePoint, Problem.knowledge_point_id == KnowledgePoint.id)
        .filter(KnowledgePoint.chapter_id == chapter_id)
        .all()
    )
    return [row[0] for row in rows]


def collect_problem_ids_by_kp(db: Session, knowledge_point_id: str) -> List[str]:
    rows = db.query(Problem.id).filter(Problem.knowledge_point_id == knowledge_point_id).all()
    return [row[0] for row in rows]


def delete_subject(db: Session, subject) -> Dict[str, int]:
    problem_ids = collect_problem_ids_by_subject(db, subject.id)
    db.delete(subject)
    db.commit()
    _drop_vectors(problem_ids)
    return {'deletedProblems': len(problem_ids)}


def delete_chapter(db: Session, chapter) -> Dict[str, int]:
    problem_ids = collect_problem_ids_by_chapter(db, chapter.id)
    db.delete(chapter)
    db.commit()
    _drop_vectors(problem_ids)
    return {'deletedProblems': len(problem_ids)}


def delete_knowledge_point(db: Session, knowledge_point) -> Dict[str, int]:
    problem_ids = collect_problem_ids_by_kp(db, knowledge_point.id)
    db.delete(knowledge_point)
    db.commit()
    _drop_vectors(problem_ids)
    return {'deletedProblems': len(problem_ids)}


def _drop_vectors(problem_ids: List[str]) -> None:
    if not problem_ids:
        return
    try:
        vector_store.remove(problem_ids)
    except Exception as exc:  # 数据库已删，向量清理失败只记日志
        logger.warning('删除向量失败 %s: %s', problem_ids, exc)
