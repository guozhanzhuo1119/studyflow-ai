"""AI 服务请求体定义；响应统一走 app.core.responses。"""

from typing import Literal

from pydantic import BaseModel, Field


class ParseMaterialRequest(BaseModel):
    filename: str = ''
    content_base64: str | None = None
    text: str | None = None
    title: str | None = None


class GenerateQuestionsRequest(BaseModel):
    chapter_title: str = Field(..., min_length=1)
    chapter_content: str = Field(..., min_length=1)
    count: int = Field(default=5, ge=1, le=10)
    # problems.difficulty 是整数 1~5；easy/medium/hard 只用于 variants.difficulty。
    difficulty: int = Field(default=3, ge=1, le=5)
    existing_titles: list[str] = Field(default_factory=list)


class Hierarchy(BaseModel):
    subject_name: str | None = None
    chapter_name: str | None = None
    knowledge_point_name: str | None = None


class VariantRequest(BaseModel):
    stem: str = Field(..., min_length=1)
    options: list[str] | None = None
    answer: str | None = None
    explanation: str | None = None
    count: int = Field(default=5, ge=1, le=10)
    hierarchy: Hierarchy | None = None
    source: str | None = None
    tags: str | None = None
    # 兼容上一版扁平字段；hierarchy 优先。Java 按 §5.4 传 hierarchy 即可。
    knowledge_point_name: str | None = None
    chapter_name: str | None = None
    subject_name: str | None = None


class ChatQuestion(BaseModel):
    title: str = ''
    options: list[str] | None = None
    user_answer: str | None = None
    correct_answer: str | None = None
    explanation: str | None = None


class ChatHistoryItem(BaseModel):
    role: Literal['user', 'assistant', 'system'] = 'user'
    content: str = ''


class ChatRequest(BaseModel):
    persona: str = 'xinyuehu'
    question: ChatQuestion | None = None
    history: list[ChatHistoryItem] = Field(default_factory=list)
    message: str = Field(..., min_length=1)


class IndexItem(BaseModel):
    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class IndexRebuildRequest(BaseModel):
    # 空 items 由 API 层返回 400（而非 422），与其余业务错误保持一致。
    items: list[IndexItem] = Field(default_factory=list)


class SearchRequest(BaseModel):
    # 空 query 由 API 层返回 400；top_k 不合法仍走统一 422。
    query: str = ''
    top_k: int = Field(default=5, ge=1, le=50)
