"""统一的 LLM 客户端（DeepSeek），迁移自 代码/app/services/llm.py。"""

from langchain_openai import ChatOpenAI

from app.core.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    LLM_TIMEOUT_SECONDS,
)
from app.core.errors import ServiceError


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    if not DEEPSEEK_API_KEY:
        raise ServiceError(
            'llm_not_configured',
            '未配置 DEEPSEEK_API_KEY，无法调用模型',
            status_code=503,
        )
    return ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=temperature,
        timeout=LLM_TIMEOUT_SECONDS,
    )
