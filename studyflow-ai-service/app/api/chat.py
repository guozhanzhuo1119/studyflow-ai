"""POST /ai/chat：心月狐陪练；默认挂载受限的只读工具，可用 use_tools=false 关闭。"""

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
        use_tools=data.use_tools,
    )
    return ok({'reply': reply})
