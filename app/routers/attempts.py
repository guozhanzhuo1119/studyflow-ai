"""作答记录：每做一次题写一条，为错因分析、掌握度和复习排期提供数据"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import false, or_
from sqlalchemy.orm import Session

from app import get_db
from app.models.attempt import Attempt
from app.models.error import ERROR_TYPE_META, ErrorAnalysis, ErrorType
from app.models.problem import Problem, Variant

router = APIRouter(prefix='/api/attempts', tags=['作答记录'])

RESULT_VALUES = {'correct', 'wrong', 'giveup'}
TARGET_VALUES = {'problem', 'variant'}


class AttemptCreate(BaseModel):
    target_type: str
    target_id: str
    result: str
    duration_sec: int | None = None
    error_reason: str | None = None
    error_type: str | None = None          # 六类错因之一，result=wrong 时可带，会同步写归因记录
    source: str = 'manual'


def _stats(rows: list[Attempt]) -> dict:
    total = len(rows)
    correct = sum(1 for row in rows if row.result == 'correct')
    wrong = sum(1 for row in rows if row.result == 'wrong')
    return {
        'total': total,
        'correct': correct,
        'wrong': wrong,
        'giveup': total - correct - wrong,
        'accuracy': round(correct / total, 4) if total else 0.0,
    }


@router.post('')
def create_attempt(data: AttemptCreate, db: Session = Depends(get_db)):
    """记录一次作答；result=wrong 且带 error_type 时，同步写一条错因归因记录"""
    if data.result not in RESULT_VALUES:
        raise HTTPException(400, f'result 只能是 {sorted(RESULT_VALUES)}')
    if data.target_type not in TARGET_VALUES:
        raise HTTPException(400, f'target_type 只能是 {sorted(TARGET_VALUES)}')

    model = Problem if data.target_type == 'problem' else Variant
    target = db.query(model).filter(model.id == data.target_id).first()
    if not target:
        raise HTTPException(404, '题目不存在')

    if data.error_type and data.result != 'wrong':
        raise HTTPException(400, '只有做错时才能填 error_type')
    if data.error_type and data.error_type not in {et.value for et in ErrorType}:
        raise HTTPException(400, f'error_type 只能是 {[et.value for et in ErrorType]}')

    attempt = Attempt(
        target_type=data.target_type,
        target_id=data.target_id,
        result=data.result,
        duration_sec=data.duration_sec,
        error_reason=(data.error_reason or '').strip() or None,
        source=data.source,
        created_at=datetime.now(),
    )
    db.add(attempt)

    error_id = None
    if data.error_type:
        error_row = ErrorAnalysis(
            problem_id=data.target_id,
            problem_title=target.title,
            topic=None,
            mother_problem=None,
            error_type=data.error_type,
            tag=None,
            specific_behavior=(data.error_reason or '').strip()
            or ERROR_TYPE_META[ErrorType(data.error_type)]['name'],
            first_break_point=data.error_type,
            remedy_status='待补',
            reviewed=False,
            created_at=datetime.now(),
        )
        db.add(error_row)
        db.flush()
        error_id = error_row.id

    db.commit()
    db.refresh(attempt)

    rows = db.query(Attempt).filter(
        Attempt.target_type == data.target_type,
        Attempt.target_id == data.target_id,
    ).all()
    return {'id': attempt.id, 'error_id': error_id, 'stats': _stats(rows)}


@router.get('/overview')
def attempt_overview(
    knowledge_point_id: str | None = Query(default=None),
    problem_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """按题目聚合作答次数，供列表页显示「已做 N 次 / 正确率」"""
    query = db.query(Attempt)
    if problem_id:
        # 母题本身 + 它名下的变题，合起来算
        variant_ids = [
            row.id for row in db.query(Variant.id).filter(Variant.problem_id == problem_id).all()
        ]
        conditions = [(Attempt.target_type == 'problem') & (Attempt.target_id == problem_id)]
        if variant_ids:
            conditions.append((Attempt.target_type == 'variant') & (Attempt.target_id.in_(variant_ids)))
        query = query.filter(or_(*conditions))
    elif knowledge_point_id:
        problem_ids = [
            row.id
            for row in db.query(Problem.id).filter(Problem.knowledge_point_id == knowledge_point_id).all()
        ]
        variant_ids = [
            row.id
            for row in db.query(Variant.id).filter(Variant.problem_id.in_(problem_ids)).all()
        ] if problem_ids else []
        conditions = []
        if problem_ids:
            conditions.append(Attempt.target_id.in_(problem_ids))
        if variant_ids:
            conditions.append(Attempt.target_id.in_(variant_ids))
        query = query.filter(or_(*conditions)) if conditions else query.filter(false())

    result: dict[str, dict] = {}
    for row in query.all():
        bucket = result.setdefault(row.target_id, {
            'total': 0, 'correct': 0, 'wrong': 0, 'giveup': 0,
        })
        bucket['total'] += 1
        bucket[row.result] = bucket.get(row.result, 0) + 1

    for bucket in result.values():
        bucket['accuracy'] = round(bucket['correct'] / bucket['total'], 4) if bucket['total'] else 0.0
    return {'stats': result}


@router.get('/{target_type}/{target_id}')
def list_attempts(target_type: str, target_id: str, db: Session = Depends(get_db)):
    """某道题的全部作答历史"""
    if target_type not in TARGET_VALUES:
        raise HTTPException(400, f'target_type 只能是 {sorted(TARGET_VALUES)}')
    rows = (
        db.query(Attempt)
        .filter(Attempt.target_type == target_type, Attempt.target_id == target_id)
        .order_by(Attempt.id.desc())
        .all()
    )
    return {
        'stats': _stats(rows),
        'attempts': [
            {
                'id': row.id,
                'result': row.result,
                'duration_sec': row.duration_sec,
                'error_reason': row.error_reason,
                'source': row.source,
                'created_at': row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }
