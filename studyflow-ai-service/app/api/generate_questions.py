"""POST /ai/generate-questions：出题纯函数端点，Java 负责落库。"""

from fastapi import APIRouter

from app.api.schemas import GenerateQuestionsRequest
from app.core.responses import ok
from app.generation.question_generator import generate_questions_payload

router = APIRouter(prefix='/ai', tags=['ai'])


@router.post('/generate-questions')
def generate_questions(data: GenerateQuestionsRequest):
    return ok(generate_questions_payload(
        chapter_title=data.chapter_title,
        chapter_content=data.chapter_content,
        count=data.count,
        difficulty=data.difficulty,
        existing_titles=data.existing_titles,
    ))
