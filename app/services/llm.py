"""统一的 LLM 客户端，避免各处重复初始化"""

from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL') or 'https://api.deepseek.com/v1'
MODEL_NAME = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    return ChatOpenAI(
        model=MODEL_NAME,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=temperature,
        timeout=120,
    )
