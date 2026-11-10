from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

#这个数据库类代表错题本目录，用来装题目的文件夹
class Category(Base):
    __tablename__ = 'categories'

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)# 分类名，比如“高数”、“408”、“Java八股”
    source = Column(String(100))# 来源，比如“考研”、“工作”、“面试”
    created_at = Column(DateTime, nullable=False)

    problems = relationship('Problem', back_populates='category')

#这个数据库类代表错题本中的题目
class Problem(Base):
    __tablename__ = 'problems'

    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)# 题目标题
    source = Column(String(100))# 题目来源
    tags = Column(String(200))# 题目标签
    status = Column(String(20), default='todo')# 题目状态，比如“todo”、“doing”、“done”
    category_id = Column(String(36), ForeignKey('categories.id'))
    created_at = Column(DateTime, nullable=False)

    category = relationship('Category', back_populates='problems')