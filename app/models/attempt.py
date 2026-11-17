from sqlalchemy import Column, String, Integer, Text, DateTime, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Attempt(Base):
    """一次作答记录，是错因分析、掌握度和复习排期的数据来源"""

    __tablename__ = 'attempts'
    __table_args__ = (Index('ix_attempts_target', 'target_type', 'target_id'),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_type = Column(String(20), nullable=False)  # problem / variant
    target_id = Column(String(36), nullable=False)    # 对应母题或变题的 id
    result = Column(String(20), nullable=False)       # correct / wrong / giveup
    duration_sec = Column(Integer)                    # 本次耗时，可空
    error_reason = Column(Text)                       # 错因，自由文本，可空
    source = Column(String(20), default='manual')     # manual / ai / duplicate
    created_at = Column(DateTime, nullable=False)
