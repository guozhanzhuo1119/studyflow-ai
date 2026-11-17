"""知识库：教材 / 文档及其文本分块"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.problem import Base


class Material(Base):
    """一份上传的教材或文档（PDF / TXT / Markdown）"""

    __tablename__ = 'materials'

    id = Column(String(64), primary_key=True)
    title = Column(String(200), nullable=False)
    subject_id = Column(String(64), ForeignKey('subjects.id'), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(16), nullable=False)      # pdf / txt / md
    file_path = Column(String(500), nullable=False)
    page_count = Column(Integer, default=0)
    char_count = Column(Integer, default=0)
    quality = Column(String(16), default='ok')          # ok / scanned（疑似扫描版，无文字层）
    created_at = Column(DateTime)

    chunks = relationship('MaterialChunk', back_populates='material', cascade='all, delete-orphan')


class MaterialChunk(Base):
    """按页切出的文本块，供检索与 AI 阅读"""

    __tablename__ = 'material_chunks'

    id = Column(String(64), primary_key=True)
    material_id = Column(String(64), ForeignKey('materials.id'), nullable=False, index=True)
    page_no = Column(Integer, default=0)
    seq = Column(Integer, default=0)                   # 同页内的块序号
    content = Column(Text, nullable=False)
    char_count = Column(Integer, default=0)

    material = relationship('Material', back_populates='chunks')
