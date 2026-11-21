"""RAG 端点：内存向量索引的构建、状态与语义检索。"""

from fastapi import APIRouter

from app.api.schemas import IndexRebuildRequest, SearchRequest
from app.core.errors import ServiceError
from app.core.responses import ok
from app.rag import search as rag_search

router = APIRouter(prefix='/ai', tags=['ai'])


@router.post('/index/rebuild')
def rebuild(data: IndexRebuildRequest):
    if not data.items:
        raise ServiceError('empty_items', 'items 不能为空', status_code=400)
    indexed = rag_search.rebuild_index(data.items)
    status = rag_search.index_status()
    return ok({'indexed': indexed, 'dim': status['dim']})


@router.get('/index/status')
def status():
    return ok(rag_search.index_status())


@router.post('/search')
def search(data: SearchRequest):
    query = data.query.strip()
    if not query:
        raise ServiceError('empty_query', 'query 不能为空', status_code=400)
    results = rag_search.search_semantic(query, data.top_k)
    return ok({'results': results})
