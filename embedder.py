"""
记忆外挂 v2 — Embedding 服务
调用智谱 Embedding API 生成向量，纯 Python 余弦相似度检索（零依赖）
"""
import logging
import math
import struct
import time
from typing import Optional

import httpx

from config import get_config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """向量生成 & 相似度检索 — 纯 Python 实现"""

    def __init__(self):
        cfg = get_config()
        self.api_base = cfg.embedding_api_base.rstrip("/")
        self.api_key = cfg.embedding_api_key
        self.model = cfg.embedding_model
        self.dim = cfg.embedding_dim
        self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    # ── 单条/批量编码 ──

    def encode(self, text: str) -> Optional[list[float]]:
        """对单条文本生成 embedding，返回 float 列表"""
        result = self.encode_batch([text])
        return result[0] if result else None

    def encode_batch(self, texts: list[str], retries: int = 2) -> list[Optional[list[float]]]:
        """批量生成 embeddings，自动重试"""
        if not self.is_available():
            logger.warning("Embedding API 未配置")
            return [None] * len(texts)

        for attempt in range(retries + 1):
            try:
                resp = self.client.post(
                    f"{self.api_base}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "input": texts,
                    },
                )
                if resp.status_code == 429:
                    wait = min(2 ** attempt, 8)
                    logger.warning("Embedding rate limited, retry in %ds...", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                items = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in items]
            except Exception as e:
                if attempt < retries:
                    logger.warning("Embedding 失败 (attempt %d): %s", attempt + 1, e)
                    time.sleep(1)
                else:
                    logger.error("Embedding 彻底失败: %s", e)
                    return [None] * len(texts)
        return [None] * len(texts)

    # ── 序列化（float list ↔ BLOB） ──

    @staticmethod
    def pack(vec: list[float]) -> bytes:
        """float list → SQLite BLOB（小端 float32）"""
        return struct.pack(f"<{len(vec)}f", *vec)

    @staticmethod
    def unpack(data: bytes) -> list[float]:
        """SQLite BLOB → float list"""
        count = len(data) // 4
        return list(struct.unpack(f"<{count}f", data))

    # ── 余弦相似度（纯 Python） ──

    @staticmethod
    def cosine(a: list[float], b: list[float]) -> float:
        """纯 Python 余弦相似度，1024 维 ~0.5ms"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query_vec: list[float], candidates: list[tuple[str, bytes]],
               top_k: int = 20) -> list[tuple[str, float]]:
        """在候选向量中搜索 top_k 最相似"""
        scored: list[tuple[str, float]] = []
        for mem_id, emb_bytes in candidates:
            try:
                emb = self.unpack(emb_bytes)
                sim = self.cosine(query_vec, emb)
                scored.append((mem_id, round(sim, 4)))
            except Exception:
                continue
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]
