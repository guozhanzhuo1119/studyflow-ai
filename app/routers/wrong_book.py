"""错题本查询接口"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import get_db
from app.models.problem import Problem
from app.models.wrong_book import WrongBook

router = APIRouter(prefix='/api/wrong-book', tags=['错题本'])


def _serialize(db: Session, row: WrongBook) -> dict:
    payload = {
        'id': row.id,
        'target_type': row.target_type,
        'target_id': row.target_id,
        'title': row.title,
        'wrong_count': row.wrong_count,
        'mastered': row.mastered,
        'last_wrong_at': row.last_wrong_at,
        'mastered_at': row.mastered_at,
        'knowledge_point_id': None,
        'knowledge_point_name': None,
        'chapter_id': None,
        'chapter_name': None,
        'subject_id': None,
        'subject_name': None,
    }
    if row.target_type == 'problem':
        problem = db.query(Problem).filter(Problem.id == row.target_id).first()
        knowledge_point = problem.knowledge_point if problem else None
        if problem:
            payload['title'] = problem.title or row.title
        if knowledge_point:
            chapter = knowledge_point.chapter
            subject = chapter.subject if chapter else None
            payload.update({
                'knowledge_point_id': knowledge_point.id,
                'knowledge_point_name': knowledge_point.name,
                'chapter_id': chapter.id if chapter else None,
                'chapter_name': chapter.name if chapter else None,
                'subject_id': subject.id if subject else None,
                'subject_name': subject.name if subject else None,
            })
    return payload


@router.get('')
def list_wrong_book(
    mastered: Optional[bool] = Query(None, description='true 只看已掌握，false 只看未掌握，不传看全部'),
    target_type: Optional[str] = Query(None, description='problem / variant'),
    db: Session = Depends(get_db),
):
    query = db.query(WrongBook)
    if mastered is not None:
        query = query.filter(WrongBook.mastered == mastered)
    if target_type:
        query = query.filter(WrongBook.target_type == target_type)

    rows = query.order_by(
        WrongBook.mastered.asc(),
        func.coalesce(WrongBook.last_wrong_at, WrongBook.created_at).desc(),
        WrongBook.id.desc(),
    ).all()

    total = db.query(WrongBook).count()
    unmastered = db.query(WrongBook).filter(WrongBook.mastered == False).count()  # noqa: E712
    return {
        'items': [_serialize(db, row) for row in rows],
        'total': total,
        'unmastered': unmastered,
    }
