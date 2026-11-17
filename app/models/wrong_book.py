"""错题本：每道题一行，答错累加次数，答对标记已掌握（不删记录）"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class WrongBook(Base):
    __tablename__ = 'wrong_book'
    # 唯一键：同一道题只保留一行，重复提交靠它兜底
    __table_args__ = (
        UniqueConstraint('target_type', 'target_id', name='uq_wrong_book_target'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_type = Column(String(20), nullable=False)   # problem / variant
    target_id = Column(String(36), nullable=False)     # 对应母题或变题 id
    title = Column(String(200))                        # 题目快照，题目被删后仍可展示
    wrong_count = Column(Integer, default=1, nullable=False)
    mastered = Column(Boolean, default=False, nullable=False)  # 答对后置 True
    last_wrong_at = Column(DateTime)
    mastered_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)
