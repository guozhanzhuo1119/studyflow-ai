from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import get_db
from app.models.problem import Subject
from app.services.hierarchy import delete_subject

router = APIRouter(prefix='/api/subjects', tags=['科目'])


class SubjectCreate(BaseModel):
    name: str
    description: str | None = None


def _serialize(subject: Subject) -> dict:
    return {
        'id': subject.id,
        'name': subject.name,
        'description': subject.description,
        'chapter_count': len(subject.chapters),
        'created_at': subject.created_at,
    }


@router.get('')
def get_subjects(db: Session = Depends(get_db)):
    return [_serialize(subject) for subject in db.query(Subject).all()]


@router.get('/{subject_id}')
def get_subject(subject_id: str, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(404, '科目不存在')
    return _serialize(subject)


@router.post('')
def create_subject(data: SubjectCreate, db: Session = Depends(get_db)):
    subject = Subject(
        id=f'sub-{uuid.uuid4().hex[:8]}',
        name=data.name,
        description=data.description,
        created_at=datetime.now()
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return _serialize(subject)


@router.put('/{subject_id}')
def update_subject(subject_id: str, data: SubjectCreate, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(404, '科目不存在')
    subject.name = data.name
    subject.description = data.description
    db.commit()
    db.refresh(subject)
    return _serialize(subject)


@router.delete('/{subject_id}')
def delete_subject_route(subject_id: str, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(404, '科目不存在')
    stats = delete_subject(db, subject)
    return {'message': '删除成功', **stats}
