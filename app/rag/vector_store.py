"""FAISS 向量检索：
- 使用 sentence-transformers 中文模型把题目编码成 768 维向量
- 使用 FAISS IndexIDMap2 + IndexFlatIP（向量已归一化，内积即余弦相似度）
- 索引与元数据落盘，服务重启后自动恢复，无需重新 embedding
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Iterable, List, Dict, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# 中文语义模型，本地有缓存时离线加载（国外模型对中文题目效果很差）
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'shibing624/text2vec-base-chinese')
DIMENSION = 768

# 索引持久化目录
DATA_DIR = Path(__file__).parent.parent.parent / 'data'
INDEX_PATH = DATA_DIR / 'problems.faiss'
META_PATH = DATA_DIR / 'problems_meta.json'


def _load_model() -> SentenceTransformer:
    try:
        return SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
    except Exception:
        # 本地没有缓存时退回联网下载
        return SentenceTransformer(EMBEDDING_MODEL)


class VectorStore:
    """题目向量库，支持增删改查与磁盘持久化"""

    def __init__(self, dimension: int = DIMENSION):
        self.dimension = dimension
        self._lock = threading.Lock()
        self._model: Optional[SentenceTransformer] = None

        self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(dimension))
        self.next_id = 0
        self.id_to_key: Dict[int, str] = {}     # faiss 内部 id -> 题目 id
        self.key_to_id: Dict[str, int] = {}     # 题目 id -> faiss 内部 id
        self.meta: Dict[str, Dict] = {}         # 题目 id -> 题目元数据

        self._load_from_disk()

    # ---------- 模型 ----------

    @property
    def model(self) -> SentenceTransformer:
        """懒加载，避免 import 时就占用内存和启动时间"""
        if self._model is None:
            self._model = _load_model()
        return self._model

    def embed(self, texts: List[str]) -> np.ndarray:
        """文本 -> 归一化向量"""
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    # ---------- 持久化 ----------

    def _load_from_disk(self):
        if not (INDEX_PATH.exists() and META_PATH.exists()):
            return
        try:
            # 用 Python 读写二进制 + faiss 序列化，避免中文路径导致 C++ 侧 fopen 失败
            index = faiss.deserialize_index(np.frombuffer(INDEX_PATH.read_bytes(), dtype=np.uint8))
            if index.d != self.dimension:
                logger.warning('磁盘索引维度 %s 与当前模型 %s 不一致，将重建', index.d, self.dimension)
                return
            with open(META_PATH, 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.index = index
            self.next_id = state.get('next_id', 0)
            self.id_to_key = {int(k): v for k, v in state.get('id_to_key', {}).items()}
            self.key_to_id = state.get('key_to_id', {})
            self.meta = state.get('meta', {})
            logger.info('向量库已从磁盘恢复，共 %s 条', len(self.key_to_id))
        except Exception as e:
            logger.error('向量库恢复失败，将使用空索引：%s', e)

    def _save_to_disk(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # 同上，避免中文路径下 faiss.write_index 直接 fopen 失败
        INDEX_PATH.write_bytes(faiss.serialize_index(self.index).tobytes())
        state = {
            'next_id': self.next_id,
            'id_to_key': {str(k): v for k, v in self.id_to_key.items()},
            'key_to_id': self.key_to_id,
            'meta': self.meta,
        }
        tmp = META_PATH.with_suffix('.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)
        tmp.replace(META_PATH)

    # ---------- 写入 ----------

    @staticmethod
    def _problem_text(problem: Dict) -> str:
        """拼出用于 embedding 的文本，标题权重最高放最前面"""
        parts = [
            problem.get('title') or '',
            problem.get('subject_name') or '',
            problem.get('chapter_name') or '',
            problem.get('knowledge_point_name') or '',
            problem.get('tags') or '',
        ]
        return ' '.join(p for p in parts if p).strip()

    def add(self, items: Iterable[Dict], save: bool = True) -> int:
        """批量写入，item 必须含 id / title 字段"""
        items = [i for i in items if i.get('id') and self._problem_text(i)]
        if not items:
            return 0

        with self._lock:
            texts = [self._problem_text(i) for i in items]
            vectors = self.embed(texts)
            ids = np.array([self._ensure_id(i['id']) for i in items], dtype=np.int64)
            # 已存在的先删掉，实现覆盖更新
            existed = [i for i in ids if i in self.id_to_key]
            if existed:
                self.index.remove_ids(np.array(existed, dtype=np.int64))
            self.index.add_with_ids(vectors, ids)

            for item in items:
                self.meta[item['id']] = self._clean(item)
            if save:
                self._save_to_disk()
            return len(items)

    def _ensure_id(self, key: str) -> int:
        if key in self.key_to_id:
            return self.key_to_id[key]
        idx = self.next_id
        self.next_id += 1
        self.key_to_id[key] = idx
        self.id_to_key[idx] = key
        return idx

    @staticmethod
    def _clean(item: Dict) -> Dict:
        """只保留可以 JSON 序列化的字段"""
        return {
            k: item.get(k)
            for k in ('id', 'title', 'source', 'tags',
                      'knowledge_point_id', 'knowledge_point_name',
                      'chapter_name', 'subject_name', 'status')
        }

    def update(self, item: Dict, save: bool = True) -> int:
        return self.add([item], save=save)

    def remove(self, problem_ids: List[str], save: bool = True) -> int:
        with self._lock:
            ids = [self.key_to_id[p] for p in problem_ids if p in self.key_to_id]
            if not ids:
                return 0
            self.index.remove_ids(np.array(ids, dtype=np.int64))
            for pid in problem_ids:
                idx = self.key_to_id.pop(pid, None)
                if idx is not None:
                    self.id_to_key.pop(idx, None)
                self.meta.pop(pid, None)
            if save:
                self._save_to_disk()
            return len(ids)

    def rebuild(self, items: List[Dict], save: bool = True) -> int:
        """全量重建索引（更换模型或数据不一致时使用）"""
        with self._lock:
            self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(self.dimension))
            self.next_id = 0
            self.id_to_key.clear()
            self.key_to_id.clear()
            self.meta.clear()
        return self.add(items, save=save)

    @staticmethod
    def _signature(item: Dict) -> tuple:
        """用于判断元数据是否发生变化，变了才重新 embedding"""
        return tuple(
            item.get(k) or ''
            for k in ('title', 'tags', 'knowledge_point_name', 'chapter_name', 'subject_name')
        )

    def sync(self, items: List[Dict]) -> Dict[str, int]:
        """把数据库中的题目与索引对齐：补新增、删多余、刷改动"""
        db_map = {i['id']: i for i in items if i.get('id')}
        indexed = set(self.key_to_id)
        to_add = [i for pid, i in db_map.items() if pid not in indexed]
        to_remove = [pid for pid in indexed if pid not in db_map]
        to_update = [
            i for pid, i in db_map.items()
            if pid in indexed and self._signature(self.meta.get(pid, {})) != self._signature(i)
        ]
        if to_remove:
            self.remove(to_remove, save=False)
        if to_add:
            self.add(to_add, save=False)
        if to_update:
            self.add(to_update, save=False)
        if to_add or to_remove or to_update:
            with self._lock:
                self._save_to_disk()
        return {'added': len(to_add), 'removed': len(to_remove), 'updated': len(to_update)}

    # ---------- 查询 ----------

    def search(self, query: str, top_k: int = 5, exclude_ids: Optional[List[str]] = None) -> List[Dict]:
        """语义检索，返回相似题目 + 相似度分数(0~1)"""
        query = (query or '').strip()
        if not query or self.index.ntotal == 0:
            return []

        exclude = set(exclude_ids or [])
        k = min(top_k + len(exclude), self.index.ntotal)
        query_vector = self.embed([query])
        scores, ids = self.index.search(query_vector, k)

        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue
            key = self.id_to_key.get(int(idx))
            if key is None or key in exclude:
                continue
            item = dict(self.meta.get(key, {}))
            item['score'] = round(float(score), 4)  # 归一化向量的内积 = 余弦相似度
            results.append(item)
            if len(results) >= top_k:
                break
        return results

    def __len__(self):
        return self.index.ntotal


vector_store = VectorStore()


# ---------- 兼容旧调用 ----------

def embed_problems(problems: List[Dict]):
    """将题目批量添加到向量库"""
    return vector_store.add(problems)


def search_similar_problems(query: str, top_k: int = 5) -> List[Dict]:
    """搜索相似题目"""
    return vector_store.search(query, top_k)
