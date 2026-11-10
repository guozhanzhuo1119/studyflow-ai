from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import get_db
from app.models.problem import Chapter, Subject
from app.services.hierarchy import delete_chapter

router = APIRouter(prefix='/api/chapters', tags=['章节'])


class ChapterCreate(BaseModel):
    subject_id: str
    name: str
    order_num: int = 0


def _serialize(chapter: Chapter) -> dict:
    return {
        'id': chapter.id,
        'subject_id': chapter.subject_id,
        'subject_name': chapter.subject.name if chapter.subject else None,
        'name': chapter.name,
        'order_num': chapter.order_num,
        'knowledge_point_count': len(chapter.knowledge_points),
        'created_at': chapter.created_at,
    }


@router.get('')
def get_chapters(subject_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Chapter)
    if subject_id:
        query = query.filter(Chapter.subject_id == subject_id)
    return [_serialize(chapter) for chapter in query.order_by(Chapter.order_num, Chapter.created_at).all()]


@router.get('/{chapter_id}')
def get_chapter(chapter_id: str, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(404, '章节不存在')
    return _serialize(chapter)


@router.post('')
def create_chapter(data: ChapterCreate, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
    if not subject:
        raise HTTPException(404, '科目不存在')
    chapter = Chapter(
        id=f'chap-{uuid.uuid4().hex[:8]}',
        subject_id=data.subject_id,
        name=data.name,
        order_num=data.order_num,
        created_at=datetime.now()
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return _serialize(chapter)


@router.put('/{chapter_id}')
def update_chapter(chapter_id: str, data: ChapterCreate, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(404, '章节不存在')
    chapter.subject_id = data.subject_id
    chapter.name = data.name
    chapter.order_num = data.order_num
    db.commit()
    db.refresh(chapter)
    return _serialize(chapter)


@router.delete('/{chapter_id}')
def delete_chapter_route(chapter_id: str, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(404, '章节不存在')
    stats = delete_chapter(db, chapter)
    return {'message': '删除成功', **stats}
