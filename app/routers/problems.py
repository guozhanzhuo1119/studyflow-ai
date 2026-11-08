from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import get_db
from app.models.problem import Problem
from app.rag.retriever import index_problem, remove_problem, semantic_search
from pydantic import BaseModel
from datetime import datetime
import logging
import uuid

router = APIRouter(prefix='/api/problems', tags=['题目'])
logger = logging.getLogger(__name__)


class ProblemCreate(BaseModel):
    title: str
    content: str | None = None
    source: str | None = None
    difficulty: str | None = None
    tags: str | None = None
    category_id: str


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.get('')
def get_problems(category_id: str | None = None, db: Session = Depends(get_db)):
    if category_id:
        return db.query(Problem).filter(Problem.category_id == category_id).all()
    return db.query(Problem).all()


@router.post('/search')
def search_problems(data: SemanticSearchRequest):
    """语义搜索：用向量相似度找题目，而不是关键词匹配"""
    results = semantic_search(data.query, top_k=data.top_k)
    return {'query': data.query, 'total': len(results), 'results': results}


@router.post('')
def create_problem(data: ProblemCreate, db: Session = Depends(get_db)):
    problem = Problem(
        id=f'prob-{uuid.uuid4().hex[:8]}',
        title=data.title,
        content=data.content,
        source=data.source,
        difficulty=data.difficulty,
        tags=data.tags,
        category_id=data.category_id,
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

    return problem


@router.put('/{problem_id}')
def update_problem(problem_id: str, data: ProblemCreate, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(404, '题目不存在')

    problem.title = data.title
    problem.content = data.content
    problem.source = data.source
    problem.difficulty = data.difficulty
    problem.tags = data.tags
    problem.category_id = data.category_id

    db.commit()
    db.refresh(problem)

    # 内容变了要重新 embedding，否则语义检索会命中旧内容
    try:
        index_problem(db, problem)
    except Exception as e:
        logger.error('题目 %s 向量更新失败：%s', problem.id, e)

    return problem


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
