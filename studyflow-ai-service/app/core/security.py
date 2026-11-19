"""内网鉴权：除 /health 外，所有请求必须携带正确的 X-Internal-Token。"""

import secrets

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import INTERNAL_TOKEN
from app.core.responses import fail

HEALTH_PATH = '/health'


class InternalTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == HEALTH_PATH:
            return await call_next(request)

        provided = request.headers.get('X-Internal-Token', '')
        if not secrets.compare_digest(
            provided.encode('utf-8'), INTERNAL_TOKEN.encode('utf-8')
        ):
            return JSONResponse(
                status_code=401,
                content=fail('unauthorized', '无效的 X-Internal-Token'),
            )
        return await call_next(request)
