"""POST /ai/variants：变式题推荐纯函数端点，Java 负责保存。"""

from fastapi import APIRouter

from app.api.schemas import VariantRequest
from app.core.responses import ok
from app.generation.variants import ProblemInput, recommend_variants

router = APIRouter(prefix='/ai', tags=['ai'])


@router.post('/variants')
def variants(data: VariantRequest):
    problem = ProblemInput(
        title=data.stem,
        source=(data.source or '').strip(),
        tags=(data.tags or '').strip(),
    )
    if data.hierarchy:
        hierarchy = data.hierarchy.model_dump()
    else:
        hierarchy = {
            'knowledge_point_name': data.knowledge_point_name,
            'chapter_name': data.chapter_name,
            'subject_name': data.subject_name,
        }
    items = recommend_variants(problem=problem, hierarchy=hierarchy, count=data.count)
    return ok({'variants': items, 'dropped': 0})
