import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import get_db
from app.agent.analyzer import run_agent
from app.models.attempt import Attempt
from app.models.chat import ChatMessage, ChatSession
from app.models.problem import Problem, Subject
from app.services.memory import DBMessageHistory, get_or_create_session

router = APIRouter(prefix='/api/chat', tags=['AI 对话'])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    subject_id: str | None = None  # 当前科目，用于把检索和统计限定在该科目
    question_id: str | None = None  # 当前题目，用于把题干/选项/答案/解析/最近作答注入上下文


class ChatResponse(BaseModel):
    reply: str
    session_id: str


def _build_question_context(db: Session, question_id: str) -> str:
    """把当前题目与最近一次作答拼成上下文，只注入给模型，不下发给前端"""
    problem = db.query(Problem).filter(Problem.id == question_id).first()
    if not problem:
        raise HTTPException(404, '题目不存在')

    options = []
    try:
        parsed = json.loads(problem.options or '[]')
        if isinstance(parsed, list):
            options = parsed
    except (TypeError, ValueError):
        options = []

    lines = ['【当前题目】', f'题干：{problem.title}']
    if options:
        lines.append('选项：' + '；'.join(f'{chr(65 + index)}. {text}' for index, text in enumerate(options[:4])))
    lines.append(f'正确答案：{problem.answer or "无"}')
    if problem.explanation:
        lines.append(f'解析：{problem.explanation}')

    last = (
        db.query(Attempt)
        .filter(Attempt.target_type == 'problem', Attempt.target_id == question_id)
        .order_by(Attempt.id.desc())
        .first()
    )
    if last:
        result_text = {'correct': '答对', 'wrong': '答错', 'giveup': '放弃'}.get(last.result, last.result)
        when = last.created_at.strftime('%Y-%m-%d %H:%M') if last.created_at else ''
        lines.append(f'用户最近作答：{result_text}（{when}）')
    else:
        lines.append('用户最近作答：尚未作答')
    return '\n'.join(lines)


@router.post('', response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """多轮对话：历史记录存 MySQL，Agent 按需调用工具，支持指代追问"""
    # 先校验题目，避免非法 question_id 留下空会话
    question_context = _build_question_context(db, request.question_id) if request.question_id else ''
    session_id = request.session_id or f'session-{uuid.uuid4().hex[:8]}'
    session = get_or_create_session(db, session_id, title=request.message[:40])

    subject_name = ''
    if request.subject_id:
        subject = db.query(Subject).filter(Subject.id == request.subject_id).first()
        subject_name = subject.name if subject else ''

    history = DBMessageHistory(session_id)
    # 给模型明确的科目范围和当前题目上下文，它会把 subject_name 传给检索和统计工具
    parts = []
    if subject_name:
        parts.append(f'【当前科目：{subject_name}】')
    if question_context:
        parts.append(question_context)
    parts.append(request.message)
    scoped = '\n'.join(parts)

    reply = run_agent(scoped, history.messages)

    # 用户消息与最终回答一起落库（存原文，不带范围/题目前缀）
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
