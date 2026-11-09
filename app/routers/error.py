"""错因分类 API：元数据、决策树归因、CRUD、统计。

路由顺序注意：/meta、/decide、/statistics 必须声明在 /{error_id} 之前，
否则 "meta" 会被当成 error_id 去解析成 int 而报 422。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import get_db
from app.models.error import (
    ERROR_TYPES_FOR_API,
    ErrorAnalysis,
    ErrorAnalysisCreate,
    ErrorAnalysisOut,
    ErrorAnalysisUpdate,
    ErrorTag,
    RemedyStatus,
)
from app.services.error import (
    DECISION_STEPS_FOR_API,
    apply_decision_tree,
    build_statistics,
    get_presets,
    suggest_syntax_tag,
    to_out,
)

router = APIRouter(prefix='/api/errors', tags=['错因分类'])
logger = logging.getLogger(__name__)


class DecideRequest(BaseModel):
    """决策树回答：answers[i] 是第 i+1 步回答（true=是，false=否）"""
    answers: List[bool] = Field(..., min_length=1)
    specific_behavior: Optional[str] = None


@router.get('/meta')
def get_meta(topic: Optional[str] = None):
    """前端初始化用：六类错因、子标签、决策树、预置映射"""
    return {
        'error_types': ERROR_TYPES_FOR_API,
        'tags': [{'code': ErrorTag.SYNTAX.value, 'name': '语法/语言坑', 'attach_to': 'OPERATE'}],
        'remedy_status': [RemedyStatus.PENDING.value, RemedyStatus.DONE.value],
        'decision_tree': DECISION_STEPS_FOR_API,
        'presets': get_presets(topic),
    }


@router.post('/decide')
def decide(data: DecideRequest):
    """按决策树推导错因，不让用户直接选下拉框（规格 5.1）"""
    result = apply_decision_tree(data.answers)
    return {
        'error_type': result.value,
        'suggest_syntax_tag': result.value == 'OPERATE' and suggest_syntax_tag(data.specific_behavior or ''),
    }


@router.get('/statistics')
def statistics(practice_mode: bool = True, db: Session = Depends(get_db)):
    """练习模式只返回四指标；practice_mode=false 才带上模拟阶段指标"""
    return build_statistics(db, practice_mode=practice_mode)


@router.get('', response_model=List[ErrorAnalysisOut])
def list_errors(
    problem_id: Optional[str] = None,
    error_type: Optional[str] = None,
    reviewed: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ErrorAnalysis)
    if problem_id:
        query = query.filter(ErrorAnalysis.problem_id == problem_id)
    if error_type:
        query = query.filter(ErrorAnalysis.error_type == error_type)
    if reviewed is not None:
        query = query.filter(ErrorAnalysis.reviewed == reviewed)
    rows = query.order_by(ErrorAnalysis.created_at.desc(), ErrorAnalysis.id.desc()).all()
    return [to_out(r) for r in rows]


@router.post('')
def create_error(data: ErrorAnalysisCreate, db: Session = Depends(get_db)):
    row = ErrorAnalysis(
        problem_id=data.problem_id,
        problem_title=data.problem_title,
        topic=data.topic,
        mother_problem=data.mother_problem,
        error_type=data.error_type.value,
        tag=data.tag.value if data.tag else None,
        specific_behavior=data.specific_behavior,
        first_break_point=data.first_break_point.value,
        decomposition_sentence=data.decomposition_sentence,
        remedy_status=data.remedy_status.value,
        remedy_action=data.remedy_action,
        user_note=data.user_note,
        reviewed=data.reviewed,
        identify_latency_sec=data.identify_latency_sec,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # 语言坑自动建议：不改用户数据，只在前端提示一下可以补打 SYNTAX 标签
    return {
        'record': to_out(row),
        'suggest_syntax_tag': row.error_type == 'OPERATE' and suggest_syntax_tag(row.specific_behavior or ''),
    }


@router.put('/{error_id}', response_model=ErrorAnalysisOut)
def update_error(error_id: int, data: ErrorAnalysisUpdate, db: Session = Depends(get_db)):
    """复盘相关字段的部分更新：reviewed / remedy_status / remedy_action / user_note"""
    row = db.query(ErrorAnalysis).filter(ErrorAnalysis.id == error_id).first()
    if not row:
        raise HTTPException(404, '归因记录不存在')

    payload = data.model_dump(exclude_unset=True)
    if 'remedy_status' in payload and payload['remedy_status'] is not None:
        payload['remedy_status'] = payload['remedy_status'].value
    for key, value in payload.items():
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    return to_out(row)


@router.delete('/{error_id}')
def delete_error(error_id: int, db: Session = Depends(get_db)):
    row = db.query(ErrorAnalysis).filter(ErrorAnalysis.id == error_id).first()
    if not row:
        raise HTTPException(404, '归因记录不存在')
    db.delete(row)
    db.commit()
    return {'message': '删除成功'}
