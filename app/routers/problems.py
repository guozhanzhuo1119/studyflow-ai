from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import get_db
from app.models.problem import KnowledgePoint, Problem
from app.rag.retriever import index_problem, remove_problem, semantic_search
from pydantic import BaseModel
from typing import List
from datetime import datetime
import logging
import uuid

router = APIRouter(prefix='/api/problems', tags=['题目'])
logger = logging.getLogger(__name__)


class ProblemCreate(BaseModel):
    title: str
    source: str | None = None
    tags: str | None = None
    knowledge_point_id: str


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class ProblemImportItem(BaseModel):
    title: str
    source: str | None = None
    tags: str | None = None


class ProblemImportRequest(BaseModel):
    knowledge_point_id: str
    items: List[ProblemImportItem]


def _serialize(problem: Problem) -> dict:
    kp = problem.knowledge_point
    chapter = kp.chapter if kp else None
    subject = chapter.subject if chapter else None
    return {
        'id': problem.id,
        'title': problem.title,
        'source': problem.source,
        'tags': problem.tags,
        'status': problem.status,
        'knowledge_point_id': problem.knowledge_point_id,
        'knowledge_point_name': kp.name if kp else None,
        'chapter_id': chapter.id if chapter else None,
        'chapter_name': chapter.name if chapter else None,
        'subject_id': subject.id if subject else None,
        'subject_name': subject.name if subject else None,
        'created_at': problem.created_at,
    }


@router.get('')
def get_problems(knowledge_point_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Problem)
    if knowledge_point_id:
        query = query.filter(Problem.knowledge_point_id == knowledge_point_id)
    return [_serialize(problem) for problem in query.all()]


@router.get('/{problem_id}')
def get_problem(problem_id: str, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(404, '题目不存在')
    return _serialize(problem)


@router.post('/search')
def search_problems(data: SemanticSearchRequest):
    """语义搜索：用向量相似度找题目，而不是关键词匹配"""
    results = semantic_search(data.query, top_k=data.top_k)
    return {'query': data.query, 'total': len(results), 'results': results}


@router.post('/import')
def import_problems(data: ProblemImportRequest, db: Session = Depends(get_db)):
    """批量导入母题：跳过空标题和同一知识点下已存在的同名题目"""
    knowledge_point = (
        db.query(KnowledgePoint).filter(KnowledgePoint.id == data.knowledge_point_id).first()
    )
    if not knowledge_point:
        raise HTTPException(404, '知识点不存在')

    existing_titles = {
        title.strip().lower()
        for (title,) in db.query(Problem.title).filter(
            Problem.knowledge_point_id == data.knowledge_point_id
        ).all()
    }

    created = []
    skipped = []
    for item in data.items:
        title = (item.title or '').strip()
        if not title:
            continue
        key = title.lower()
        if key in existing_titles:
            skipped.append(title)
            continue
        existing_titles.add(key)
        problem = Problem(
            id=f'prob-{uuid.uuid4().hex[:8]}',
            title=title,
            source=(item.source or '').strip() or None,
            tags=(item.tags or '').strip() or None,
            knowledge_point_id=data.knowledge_point_id,
            status='todo',
            created_at=datetime.now()
        )
        db.add(problem)
        created.append(problem)

    if not created:
        return {'created': 0, 'skipped': skipped, 'problems': []}

    db.commit()
    for problem in created:
        db.refresh(problem)
        # 导入的题目同样要进向量库，否则语义搜索搜不到
        try:
            index_problem(db, problem)
        except Exception as e:
            logger.error('题目 %s 向量化失败：%s', problem.id, e)

    return {
        'created': len(created),
        'skipped': skipped,
        'problems': [_serialize(problem) for problem in created],
    }


@router.post('')
def create_problem(data: ProblemCreate, db: Session = Depends(get_db)):
    problem = Problem(
        id=f'prob-{uuid.uuid4().hex[:8]}',
        title=data.title,
        source=data.source,
        tags=data.tags,
        knowledge_point_id=data.knowledge_point_id,
        status='todo',
        created_at=datetime.now()
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)

    # 入库即 embedding，写入 FAISS
    try:
        index_problem(db, problem)
    except Exception as e:
        logger.error('题目 %s 向量化失败：%s', problem.id, e)

    return _serialize(problem)


@router.put('/{problem_id}')
def update_problem(problem_id: str, data: ProblemCreate, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(404, '题目不存在')

    problem.title = data.title
    problem.source = data.source
    problem.tags = data.tags
    problem.knowledge_point_id = data.knowledge_point_id

    db.commit()
    db.refresh(problem)

    # 内容变了要重新 embedding，否则语义检索会命中旧内容
    try:
        index_problem(db, problem)
    except Exception as e:
        logger.error('题目 %s 向量更新失败：%s', problem.id, e)

    return _serialize(problem)


@router.delete('/{problem_id}')
def delete_problem(problem_id: str, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(404, '题目不存在')

    db.delete(problem)
    db.commit()

    try:
        remove_problem(problem_id)
    except Exception as e:
        logger.error('题目 %s 向量删除失败：%s', problem_id, e)

    return {'message': '删除成功'}
