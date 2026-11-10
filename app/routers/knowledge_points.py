from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import get_db
from app.models.problem import Chapter, KnowledgePoint
from app.services.hierarchy import delete_knowledge_point

router = APIRouter(prefix='/api/knowledge-points', tags=['知识点'])


class KnowledgePointCreate(BaseModel):
    chapter_id: str
    name: str


def _serialize(kp: KnowledgePoint) -> dict:
    chapter = kp.chapter
    subject = chapter.subject if chapter else None
    return {
        'id': kp.id,
        'chapter_id': kp.chapter_id,
        'chapter_name': chapter.name if chapter else None,
        'subject_id': subject.id if subject else None,
        'subject_name': subject.name if subject else None,
        'name': kp.name,
        'problem_count': len(kp.problems),
        'created_at': kp.created_at,
    }


@router.get('')
def get_knowledge_points(chapter_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(KnowledgePoint)
    if chapter_id:
        query = query.filter(KnowledgePoint.chapter_id == chapter_id)
    return [_serialize(kp) for kp in query.all()]


@router.get('/{kp_id}')
def get_knowledge_point(kp_id: str, db: Session = Depends(get_db)):
    kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == kp_id).first()
    if not kp:
        raise HTTPException(404, '知识点不存在')
    return _serialize(kp)


@router.post('')
def create_knowledge_point(data: KnowledgePointCreate, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(Chapter.id == data.chapter_id).first()
    if not chapter:
        raise HTTPException(404, '章节不存在')
    kp = KnowledgePoint(
        id=f'kp-{uuid.uuid4().hex[:8]}',
        chapter_id=data.chapter_id,
        name=data.name,
        created_at=datetime.now()
    )
    db.add(kp)
    db.commit()
    db.refresh(kp)
    return _serialize(kp)


@router.put('/{kp_id}')
def update_knowledge_point(kp_id: str, data: KnowledgePointCreate, db: Session = Depends(get_db)):
    kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == kp_id).first()
    if not kp:
        raise HTTPException(404, '知识点不存在')
    kp.chapter_id = data.chapter_id
    kp.name = data.name
    db.commit()
    db.refresh(kp)
    return _serialize(kp)


@router.delete('/{kp_id}')
def delete_knowledge_point_route(kp_id: str, db: Session = Depends(get_db)):
    kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == kp_id).first()
    if not kp:
        raise HTTPException(404, '知识点不存在')
    stats = delete_knowledge_point(db, kp)
    return {'message': '删除成功', **stats}
