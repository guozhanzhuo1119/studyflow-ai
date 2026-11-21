"""bge-small-zh-v1.5 句向量编码：懒加载、L2 归一化。

本机访问不了 HuggingFace，模型必须走 hf-mirror。HF_ENDPOINT 必须在
huggingface_hub 首次导入前设置，所以放在模块顶部，且 sentence_transformers
只在真正需要编码时才 import（懒加载，见 _get_model）。
"""

import logging
import os
import threading

os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = 'BAAI/bge-small-zh-v1.5'
# bge-small-zh-v1.5 的句向量维度；模型加载后以实际维度为准（见 dimension）。
DIM = 512
# BGE 中文检索模型推荐的查询指令；只加在 query 上，文档侧不加。
QUERY_INSTRUCTION = '为这个句子生成表示以用于检索相关文章：'

_model = None
_model_lock = threading.Lock()


def _model_dimension(model) -> int:
    """sentence-transformers 6.x 把 get_sentence_embedding_dimension 改名了。"""
    getter = getattr(model, 'get_embedding_dimension', None) or model.get_sentence_embedding_dimension
    return int(getter())


def _get_model():
    """第一次编码时才加载模型（下载 + 初始化约数秒），之后复用。"""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info('加载嵌入模型 %s（HF_ENDPOINT=%s）', MODEL_NAME, os.environ.get('HF_ENDPOINT'))
                model = SentenceTransformer(MODEL_NAME)
                logger.info('嵌入模型加载完成，维度=%s', _model_dimension(model))
                _model = model
    return _model


def dimension() -> int:
    """索引使用的向量维度；模型未加载时返回静态常量。"""
    model = _model
    if model is None:
        return DIM
    return _model_dimension(model)


def encode(texts: list[str], is_query: bool = False) -> np.ndarray:
    """文本 -> float32 矩阵 (n, dim)，每行已 L2 归一化（内积即余弦相似度）。"""
    if not texts:
        return np.zeros((0, dimension()), dtype='float32')
    model = _get_model()
    inputs = [f'{QUERY_INSTRUCTION}{text}' if is_query else text for text in texts]
    vectors = model.encode(
        inputs,
        batch_size=32,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype='float32')
