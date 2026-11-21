"""进程内向量索引：ids 列表 + {id: text} + FAISS IndexFlatIP，线程安全。

无状态服务不连数据库，索引只活在进程内存里：
- 由调用方通过 /ai/index/rebuild 全量喂数据；
- 服务重启即失，count 回到 0，由 Java 重新灌入；
- 向量已在 embedder 里 L2 归一化，IndexFlatIP 的内积即余弦相似度。
"""

import logging
import threading

import faiss
import numpy as np

from app.rag import embedder

logger = logging.getLogger(__name__)


class MemoryVectorIndex:
    def __init__(self):
        self._lock = threading.Lock()
        self._index: faiss.IndexFlatIP | None = None
        self._ids: list[str] = []
        self._texts: dict[str, str] = {}
        self._dim = 0

    def rebuild(self, items: list[tuple[str, str]]) -> int:
        """全量替换索引，返回收录条数。embedding 在锁外计算，避免阻塞查询。"""
        # 重复 id 保留最后一条，保证 ids 与 _texts 一一对应。
        deduped: dict[str, str] = {}
        for item_id, text in items:
            deduped[item_id] = text
        ids = list(deduped.keys())
        texts = [deduped[item_id] for item_id in ids]

        vectors = embedder.encode(texts)
        dim = int(vectors.shape[1]) if vectors.size else embedder.dimension()

        index = faiss.IndexFlatIP(dim)
        if vectors.size:
            index.add(vectors)

        with self._lock:
            self._index = index
            self._ids = ids
            self._texts = dict(zip(ids, texts))
            self._dim = dim

        logger.info('向量索引重建完成：%s 条，维度 %s', len(ids), dim)
        return len(ids)

    def search(self, query_vec: np.ndarray, top_k: int) -> list[dict]:
        """query_vec 为 shape (dim,) 的已归一化向量，按余弦相似度降序返回。"""
        with self._lock:
            if self._index is None or self._index.ntotal == 0:
                return []
            k = min(max(top_k, 1), self._index.ntotal)
            query = np.asarray(query_vec, dtype='float32').reshape(1, -1)
            scores, positions = self._index.search(query, k)
            results = []
            for score, position in zip(scores[0], positions[0]):
                if position < 0:
                    continue
                item_id = self._ids[int(position)]
                results.append(
                    {
                        'id': item_id,
                        'score': float(score),
                        'text': self._texts.get(item_id, ''),
                    }
                )
            return results

    def status(self) -> dict:
        with self._lock:
            count = len(self._ids)
            dim = self._dim or embedder.dimension()
        return {'count': count, 'dim': dim, 'model': embedder.MODEL_NAME}


# 进程内单例：所有端点共享同一份索引。
vector_index = MemoryVectorIndex()
