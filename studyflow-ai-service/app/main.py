"""StudyFlow AI 能力服务入口：只注册 /ai/** 与 /health，零数据库。"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import chat, generate_questions, health, parse_material, rag, variants
from app.core.config import AI_SERVICE_HOST, AI_SERVICE_PORT
from app.core.errors import ServiceError
from app.core.responses import fail
from app.core.security import InternalTokenMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title='StudyFlow AI Service',
    version='1.0',
    description='StudyFlow 无状态 AI 能力服务，只暴露 /ai/**，零数据库',
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(InternalTokenMiddleware)

app.include_router(health.router)
app.include_router(parse_material.router)
app.include_router(generate_questions.router)
app.include_router(variants.router)
app.include_router(chat.router)
app.include_router(rag.router)


@app.exception_handler(ServiceError)
async def _service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(exc.code, exc.message),
    )


@app.exception_handler(RequestValidationError)
async def _validation_error_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        first = errors[0]
        location = '.'.join(str(part) for part in first.get('loc', ()))
        detail = first.get('msg', '请求参数不合法')
        message = f'{location}: {detail}' if location else detail
    else:
        message = '请求参数不合法'
    return JSONResponse(status_code=422, content=fail('invalid_request', message))


@app.exception_handler(StarletteHTTPException)
async def _http_error_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=fail('http_error', str(exc.detail)),
    )


@app.exception_handler(Exception)
async def _unhandled_error_handler(request: Request, exc: Exception):
    logger.exception('未处理异常：%s %s', request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=fail('internal_error', '服务内部错误'),
    )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        'app.main:app',
        host=AI_SERVICE_HOST,
        port=AI_SERVICE_PORT,
    )
