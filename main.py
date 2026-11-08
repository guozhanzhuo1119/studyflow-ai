import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app import engine, SessionLocal
from app.models.problem import Base as ProblemBase
from app.models.user import Base as UserBase
from app.models.chat import Base as ChatBase
from app.routers import categories, problems, recommend, chat, auth

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表
    ProblemBase.metadata.create_all(bind=engine)
    UserBase.metadata.create_all(bind=engine)
    ChatBase.metadata.create_all(bind=engine)

    # 把数据库中的题目同步进 FAISS，保证语义检索可用
    from app.rag.retriever import sync_all_problems
    try:
        with SessionLocal() as db:
            sync_all_problems(db)
    except Exception as e:
        logger.error('向量库初始化失败，语义检索不可用：%s', e)

    yield
    # 关闭时清理（可以留空）


app = FastAPI(
    title='StudyFlow AI',
    version='1.0',
    description='AI 刷题推荐系统 - 基于 LangChain + FAISS + DeepSeek',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# 注册路由
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(problems.router)
app.include_router(recommend.router)
app.include_router(chat.router)


@app.get('/')
def root():
    return {
        'message': 'StudyFlow AI API 运行中',
        'docs': '/docs',
        'health': '/health'
    }


@app.get('/health')
def health():
    return {'status': 'ok'}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8002)
