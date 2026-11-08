from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ChatSession(Base):
    """对话会话，重启后依然存在"""

    __tablename__ = 'chat_sessions'

    id = Column(String(36), primary_key=True)
    title = Column(String(200))
    user_id = Column(String(36), index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ChatMessage(Base):
    """会话中的一条消息"""

    __tablename__ = 'chat_messages'
    __table_args__ = (Index('ix_chat_messages_session_id_id', 'session_id', 'id'),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('chat_sessions.id'), nullable=False)
    role = Column(String(20), nullable=False)      # user / assistant / system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
