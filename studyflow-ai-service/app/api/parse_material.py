"""POST /ai/parse-material：教材解析 + 正则大纲草案，纯文本计算。"""

from fastapi import APIRouter

from app.api.schemas import ParseMaterialRequest
from app.core.responses import ok
from app.parsing.materials import parse_material_payload

router = APIRouter(prefix='/ai', tags=['ai'])


@router.post('/parse-material')
def parse_material(data: ParseMaterialRequest):
    return ok(parse_material_payload(
        filename=data.filename,
        content_base64=data.content_base64,
        text=data.text,
        title=data.title,
    ))
