from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import get_db
from app.agent.analyzer import run_agent
from app.models.chat import ChatMessage, ChatSession
from app.services.memory import DBMessageHistory, get_or_create_session
import uuid

router = APIRouter(prefix='/api/chat', tags=['AI 对话'])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@router.post('', response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """多轮对话：历史记录存 MySQL，Agent 按需调用工具，支持指代追问"""
    session_id = request.session_id or f'session-{uuid.uuid4().hex[:8]}'
    session = get_or_create_session(db, session_id, title=request.message[:40])

    history = DBMessageHistory(session_id)
    reply = run_agent(request.message, history.messages)

    # 用户消息与最终回答一起落库
    history.add_messages([HumanMessage(content=request.message), AIMessage(content=reply)])

    session.updated_at = datetime.now()
    db.commit()

    return {'reply': reply, 'session_id': session_id}


@router.get('/sessions')
def list_sessions(db: Session = Depends(get_db)):
    """列出所有会话（来自数据库，重启不丢）"""
    sessions = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
    result = []
    for s in sessions:
        count = db.query(ChatMessage).filter(ChatMessage.session_id == s.id).count()
        result.append({
            'session_id': s.id,
            'title': s.title,
            'message_count': count,
            'updated_at': s.updated_at.isoformat() if s.updated_at else None,
        })
    return {'sessions': result}


@router.get('/sessions/{session_id}/messages')
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    """回放某次会话的历史消息，前端可用来恢复聊天记录"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(404, '会话不存在')
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id)
        .all()
    )
    return {
        'session_id': session_id,
        'messages': [{'role': m.role, 'content': m.content} for m in messages],
    }


@router.delete('/sessions/{session_id}')
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """删除会话及其消息"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(404, '会话不存在')
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {'message': '会话已删除'}
