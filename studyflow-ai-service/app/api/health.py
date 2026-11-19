"""健康检查：不需要 X-Internal-Token，供 Java / 部署脚本探活。"""

from fastapi import APIRouter

from app.core.responses import ok

router = APIRouter(tags=['system'])


@router.get('/health')
def health():
    return ok({'status': 'ok', 'service': 'studyflow-ai-service'})
