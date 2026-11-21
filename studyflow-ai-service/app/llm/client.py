"""统一的 LLM 客户端：支持 DeepSeek 云端 / Ollama 本地模型切换。"""

from langchain_openai import ChatOpenAI

from app.core.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    LLM_PROVIDER,
    LLM_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from app.core.errors import ServiceError


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    if LLM_PROVIDER == 'ollama':
        # 本地模型：key 是占位符，Ollama 不校验
        return ChatOpenAI(
            model=OLLAMA_MODEL,
            api_key='ollama',
            base_url=OLLAMA_BASE_URL,
            temperature=temperature,
            timeout=LLM_TIMEOUT_SECONDS,
        )
    # 默认：DeepSeek 云端
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
