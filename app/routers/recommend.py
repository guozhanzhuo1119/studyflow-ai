from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import get_db
from app.models.problem import Problem
from app.services.recommend import recommend_variants
from pydantic import BaseModel

router = APIRouter(prefix='/api/recommend', tags=['AI 推荐'])


class RecommendRequest(BaseModel):
    problem_id: str
    count: int = 5


class RecommendResponse(BaseModel):
    problem_id: str
    problem_title: str
    recommendations: list


@router.post('', response_model=RecommendResponse)
def recommend(request: RecommendRequest, db: Session = Depends(get_db)):
    # 1. 查询母题
    problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
    if not problem:
        raise HTTPException(404, '题目不存在')

    # 2. 沿 知识点 -> 章节 -> 科目 取层级名称
    hierarchy = {
        'knowledge_point_name': None,
        'chapter_name': None,
        'subject_name': None,
    }
    kp = problem.knowledge_point
    if kp:
        hierarchy['knowledge_point_name'] = kp.name
        chapter = kp.chapter
        if chapter:
            hierarchy['chapter_name'] = chapter.name
            if chapter.subject:
                hierarchy['subject_name'] = chapter.subject.name

    # 3. 调用 AI 推荐
    recommendations = recommend_variants(
        problem=problem,
        hierarchy=hierarchy,
        count=request.count
    )

    return {
        'problem_id': problem.id,
        'problem_title': problem.title,
        'recommendations': recommendations
    }
