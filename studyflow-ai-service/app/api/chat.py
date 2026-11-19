"""POST /ai/chat：心月狐陪练，只做 prompt + 上下文 + 历史，不支持工具调用。"""

from fastapi import APIRouter

from app.api.schemas import ChatRequest
from app.chat.service import chat_reply
from app.core.responses import ok

router = APIRouter(prefix='/ai', tags=['ai'])


@router.post('/chat')
def chat(data: ChatRequest):
    reply = chat_reply(
        persona=data.persona,
        question=data.question,
        history=data.history,
        message=data.message,
    )
    return ok({'reply': reply})
