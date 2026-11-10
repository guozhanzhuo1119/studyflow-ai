from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

#这个数据库类代表科目，是最顶层，比如“高数”、“408”、“Java八股”
class Subject(Base):
    __tablename__ = 'subjects'

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)# 科目名
    description = Column(String(200))# 科目描述，可空
    created_at = Column(DateTime, nullable=False)

    chapters = relationship('Chapter', back_populates='subject', cascade='all, delete-orphan')

#这个数据库类代表章节/模块，挂在科目下面
class Chapter(Base):
    __tablename__ = 'chapters'

    id = Column(String(36), primary_key=True)
    subject_id = Column(String(36), ForeignKey('subjects.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False)# 章节名，比如“极限”、“链表”
    order_num = Column(Integer, default=0)# 章节排序号，越小越靠前
    created_at = Column(DateTime, nullable=False)

    subject = relationship('Subject', back_populates='chapters')
    knowledge_points = relationship('KnowledgePoint', back_populates='chapter', cascade='all, delete-orphan')

#这个数据库类代表知识点，挂在章节下面，是题目的直接归类
class KnowledgePoint(Base):
    __tablename__ = 'knowledge_points'

    id = Column(String(36), primary_key=True)
    chapter_id = Column(String(36), ForeignKey('chapters.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False)# 知识点名，比如“洛必达法则”
    created_at = Column(DateTime, nullable=False)

    chapter = relationship('Chapter', back_populates='knowledge_points')
    problems = relationship('Problem', back_populates='knowledge_point', cascade='all, delete-orphan')

#这个数据库类代表错题本中的题目
class Problem(Base):
    __tablename__ = 'problems'

    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)# 题目标题
    source = Column(String(100))# 题目来源
    tags = Column(String(200))# 题目标签
    status = Column(String(20), default='todo')# 题目状态，比如“todo”、“doing”、“done”
    knowledge_point_id = Column(String(36), ForeignKey('knowledge_points.id'), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)

    knowledge_point = relationship('KnowledgePoint', back_populates='problems')
    variants = relationship('Variant', back_populates='problem', cascade='all, delete-orphan')

#这个数据库类代表变题，是母题派生出来的相似题，AI 推荐后手动保存或手动录入
class Variant(Base):
    __tablename__ = 'variants'

    id = Column(String(36), primary_key=True)
    problem_id = Column(String(36), ForeignKey('problems.id'), nullable=False, index=True)
    title = Column(String(200), nullable=False)# 变题标题
    difficulty = Column(String(20))# 难度：easy / medium / hard
    link = Column(String(300))# 题目链接，可空
    reason = Column(Text)# 推荐理由或补充说明
    origin = Column(String(20), default='manual')# 来源：ai（AI 推荐保存）/ manual（手动录入）
    created_at = Column(DateTime, nullable=False)

    problem = relationship('Problem', back_populates='variants')
