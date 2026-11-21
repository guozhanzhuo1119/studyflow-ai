"""语义检索入口：串起 embedder 与内存索引。"""

from app.rag import embedder
from app.rag.index import vector_index


def rebuild_index(items: list) -> int:
    """items 为 {id, text} 对象列表；全量替换内存索引，返回收录条数。"""
    pairs = [(item.id, item.text) for item in items]
    return vector_index.rebuild(pairs)


def search_semantic(query: str, top_k: int = 5) -> list[dict]:
    """查询文本 -> 向量 -> 索引，返回 [{id, score, text}]。索引为空时返回 []。"""
    if not vector_index.status()['count']:
        return []
    query_vec = embedder.encode([query], is_query=True)[0]
    return vector_index.search(query_vec, top_k)


def index_status() -> dict:
    return vector_index.status()
