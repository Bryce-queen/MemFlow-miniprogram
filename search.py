"""
记忆外挂 v2 — 混合搜索引擎
FTS5 全文 + 向量语义 → 融合排序
"""
import logging
from typing import Optional

from config import get_config
from db import DatabaseManager
from embedder import EmbeddingService

logger = logging.getLogger(__name__)


class HybridSearch:
    """全文 + 语义混合检索"""

    def __init__(self, db: DatabaseManager, embedder: EmbeddingService):
        self.db = db
        self.embedder = embedder
        self.alpha = get_config().hybrid_alpha  # 0=纯语义, 1=纯关键词

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """
        混合搜索：融合 FTS5/LIKE 和向量语义分数
        返回 [{memory, score, match_reason}, ...]
        """
        # 1. 全文搜索
        fts_results = self.db.search_fts(query, limit=limit)
        # 2. 语义搜索（如果有 embedding）
        vec_results: dict[str, float] = {}
        if self.embedder.is_available():
            query_vec = self.embedder.encode(query)
            if query_vec is not None:
                candidates = self.db.get_all_embeddings()
                if candidates:
                    scored = self.embedder.search(query_vec, candidates, top_k=limit)
                    vec_results = {mem_id: score for mem_id, score in scored}

        # 3. 融合
        all_ids: set[str] = set()
        fts_scores: dict[str, float] = {}
        for r in fts_results:
            mid = r["id"]
            all_ids.add(mid)
            # 归一化 BM25 分数（越小越好 → 越大越好）
            fts_scores[mid] = r.get("bm25_score", -1)
        for mid in vec_results:
            all_ids.add(mid)

        if not all_ids:
            return []

        # 归一化
        fts_norm = self._normalize(fts_scores)
        vec_norm = self._normalize(vec_results)
        alpha = self.alpha

        # 如果只有语义或只有全文，调整权重
        if not fts_scores:
            alpha = 0.0
        if not vec_results:
            alpha = 1.0

        # 计算最终分数
        final: list[tuple[str, float]] = []
        for mid in all_ids:
            f = fts_norm.get(mid, 0.0)
            v = vec_norm.get(mid, 0.0)
            score = alpha * f + (1 - alpha) * v
            final.append((mid, round(score, 4)))

        final.sort(key=lambda x: -x[1])
        final = final[:limit]

        # 组装结果
        mem_map = {m["id"]: m for m in self.db.get_many_by_ids([f[0] for f in final])}
        results = []
        for mid, score in final:
            mem = mem_map.get(mid)
            if mem is None:
                continue
            reasons = []
            if fts_norm.get(mid, 0) > 0:
                reasons.append("关键词匹配")
            if vec_norm.get(mid, 0) > 0:
                reasons.append("语义相似")
            results.append({
                "memory": mem,
                "score": score,
                "match_reason": "; ".join(reasons) or "综合匹配",
            })
        return results

    @staticmethod
    def _normalize(scores: dict[str, float]) -> dict[str, float]:
        """Min-Max 归一化到 [0, 1]"""
        if not scores:
            return {}
        vals = list(scores.values())
        vmin, vmax = min(vals), max(vals)
        if vmax == vmin:
            return {k: 1.0 for k in scores}
        return {k: (v - vmin) / (vmax - vmin) for k, v in scores.items()}
