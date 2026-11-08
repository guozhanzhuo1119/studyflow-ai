from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import get_db
from app.models.problem import Category
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter(prefix='/api/categories', tags=['知识点'])


class CategoryCreate(BaseModel):
    name: str
    source: str | None = None


@router.get('')
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()


@router.post('')
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    cat = Category(
        id=f'cat-{uuid.uuid4().hex[:8]}',
        name=data.name,
        source=data.source,
        created_at=datetime.now()
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat