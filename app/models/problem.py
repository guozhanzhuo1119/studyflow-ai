from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()
#用来操作数据库的文件

class Category(Base):
    __tablename__ = 'categories'

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    source = Column(String(100))
    created_at = Column(DateTime, nullable=False)

    problems = relationship('Problem', back_populates='category')


class Problem(Base):
    __tablename__ = 'problems'

    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    source = Column(String(100))
    difficulty = Column(String(20))
    tags = Column(String(200))
    status = Column(String(20), default='todo')
    category_id = Column(String(36), ForeignKey('categories.id'))
    created_at = Column(DateTime, nullable=False)

    category = relationship('Category', back_populates='problems')