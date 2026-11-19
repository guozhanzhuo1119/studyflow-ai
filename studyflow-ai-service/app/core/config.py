"""服务配置：只保留 AI 服务所需的环境变量，不包含任何数据库配置。"""

import os
from pathlib import Path

from dotenv import load_dotenv

SERVICE_ROOT = Path(__file__).resolve().parents[2]

# 本地联调时可用 DOTENV_PATH 指向外部 .env（例如旧服务的 .env）；
# 默认读取服务根目录下的 .env。这里不读取、也不允许出现数据库配置。
_DOTENV_PATH = os.getenv('DOTENV_PATH') or str(SERVICE_ROOT / '.env')
load_dotenv(dotenv_path=_DOTENV_PATH)

INTERNAL_TOKEN = os.getenv('INTERNAL_TOKEN') or 'studyflow-dev-token'

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL') or 'https://api.deepseek.com/v1'
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL') or 'deepseek-chat'
LLM_TIMEOUT_SECONDS = int(os.getenv('LLM_TIMEOUT_SECONDS') or '120')

AI_SERVICE_HOST = os.getenv('AI_SERVICE_HOST') or '0.0.0.0'
AI_SERVICE_PORT = int(os.getenv('AI_SERVICE_PORT') or '8001')
