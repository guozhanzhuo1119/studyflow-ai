from datetime import datetime
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import get_db
from app.models.problem import Problem, Variant

router = APIRouter(prefix='/api/variants', tags=['变题'])


class VariantCreate(BaseModel):
    problem_id: str
    title: str
    difficulty: str | None = None
    link: str | None = None
    reason: str | None = None


class VariantItem(BaseModel):
    title: str
    difficulty: str | None = None
    link: str | None = None
    reason: str | None = None


class SaveFromRecommendation(BaseModel):
    problem_id: str
    recommendations: List[VariantItem]


def _serialize(variant: Variant) -> dict:
    return {
        'id': variant.id,
        'problem_id': variant.problem_id,
        'problem_title': variant.problem.title if variant.problem else None,
        'title': variant.title,
        'difficulty': variant.difficulty,
        'link': variant.link,
        'reason': variant.reason,
        'origin': variant.origin,
        'created_at': variant.created_at,
    }


def _require_problem(db: Session, problem_id: str) -> Problem:
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(404, '母题不存在')
    return problem


@router.get('')
def get_variants(problem_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Variant)
    if problem_id:
        query = query.filter(Variant.problem_id == problem_id)
    return [_serialize(variant) for variant in query.all()]


@router.get('/{variant_id}')
def get_variant(variant_id: str, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(404, '变题不存在')
    return _serialize(variant)


@router.post('')
def create_variant(data: VariantCreate, db: Session = Depends(get_db)):
    _require_problem(db, data.problem_id)
    variant = Variant(
        id=f'var-{uuid.uuid4().hex[:8]}',
        problem_id=data.problem_id,
        title=data.title,
        difficulty=data.difficulty,
        link=data.link,
        reason=data.reason,
        origin='manual',
        created_at=datetime.now()
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return _serialize(variant)


@router.post('/from-recommendation')
def save_from_recommendation(data: SaveFromRecommendation, db: Session = Depends(get_db)):
    """把 AI 推荐结果批量保存成变题，来源标记为 ai"""
    _require_problem(db, data.problem_id)
    if not data.recommendations:
        raise HTTPException(400, '推荐列表为空')

    variants = []
    for item in data.recommendations:
        variant = Variant(
            id=f'var-{uuid.uuid4().hex[:8]}',
            problem_id=data.problem_id,
            title=item.title,
            difficulty=item.difficulty,
            link=item.link,
            reason=item.reason,
            origin='ai',
            created_at=datetime.now()
        )
        db.add(variant)
        variants.append(variant)
    db.commit()
    for variant in variants:
        db.refresh(variant)
    return {'saved': len(variants), 'variants': [_serialize(v) for v in variants]}


@router.put('/{variant_id}')
def update_variant(variant_id: str, data: VariantCreate, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(404, '变题不存在')
    _require_problem(db, data.problem_id)
    variant.problem_id = data.problem_id
    variant.title = data.title
    variant.difficulty = data.difficulty
    variant.link = data.link
    variant.reason = data.reason
    db.commit()
    db.refresh(variant)
    return _serialize(variant)


@router.delete('/{variant_id}')
def delete_variant(variant_id: str, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(404, '变题不存在')
    db.delete(variant)
    db.commit()
    return {'message': '删除成功'}
