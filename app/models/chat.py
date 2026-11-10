from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base
#导入sqlalchemy的库，用来操作关系型数据库
Base = declarative_base()
#创建模具，用来创建表

class ChatSession(Base):
    """对话会话，重启后依然存在"""

#这个数据表的表名叫chat_session，这个是代表的会话，下面的数据库是会话里面的消息，属性有会话标题以及用户id
    __tablename__ = 'chat_sessions'

    id = Column(String(36), primary_key=True)
    title = Column(String(200))
    user_id = Column(String(36), index=True)#加了索引，加快搜索速度
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ChatMessage(Base):
    """会话中的一条消息"""
#这个数据表的表名叫chat_messages，用来记录会话中的消息，属性是主键，会话的类型，角色(发起对话的人)，内容，创建时间
    __tablename__ = 'chat_messages'
    __table_args__ = (Index('ix_chat_messages_session_id_id', 'session_id', 'id'),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('chat_sessions.id'), nullable=False)
    role = Column(String(20), nullable=False)      # user / assistant / system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
