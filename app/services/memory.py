"""把 LangChain 的消息历史接口落到 MySQL，服务重启后对话记录不丢失"""

from typing import Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app import SessionLocal
from app.models.chat import ChatMessage

_MESSAGE_TYPES = {
    'user': HumanMessage,
    'assistant': AIMessage,
    'system': SystemMessage,
}


class DBMessageHistory(BaseChatMessageHistory):
    """按 session_id 读写数据库中的消息"""

    def __init__(self, session_id: str, limit: int = 20, session_factory=SessionLocal):
        self.session_id = session_id
        self.limit = limit
        self._session_factory = session_factory

    @property
    def messages(self) -> list[BaseMessage]:
        with self._session_factory() as db:
            rows = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == self.session_id)
                .order_by(ChatMessage.id.desc())
                .limit(self.limit)
                .all()
            )
        # 只取最近 limit 条，避免上下文无限增长；取回后按时间正序
        return [
            _MESSAGE_TYPES.get(row.role, HumanMessage)(content=row.content)
            for row in reversed(rows)
        ]

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        from datetime import datetime

        with self._session_factory() as db:
            for message in messages:
                role = _role_of(message)
                if role is None:
                    continue
                db.add(ChatMessage(
                    session_id=self.session_id,
                    role=role,
                    content=message.content if isinstance(message.content, str) else str(message.content),
                    created_at=datetime.now(),
                ))
            db.commit()

    def clear(self) -> None:
        with self._session_factory() as db:
            db.query(ChatMessage).filter(ChatMessage.session_id == self.session_id).delete()
            db.commit()


def _role_of(message: BaseMessage) -> str | None:
    if isinstance(message, HumanMessage):
        return 'user'
    if isinstance(message, AIMessage):
        return 'assistant'
    if isinstance(message, SystemMessage):
        return 'system'
    return None


def get_or_create_session(db: Session, session_id: str, title: str | None = None, user_id: str | None = None):
    """取会话，没有就建一个"""
    from app.models.chat import ChatSession
    from datetime import datetime

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session:
        return session

    now = datetime.now()
    session = ChatSession(
        id=session_id,
        title=(title or '新对话')[:200],
        user_id=user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
