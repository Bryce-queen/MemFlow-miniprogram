"""
记忆外挂 v2 — 存储层（SQLite + FTS5）
"""
import logging
from typing import Optional

from db import DatabaseManager

logger = logging.getLogger(__name__)


class MemoryStore:
    """记忆存储 — 委托给 DatabaseManager，保持旧接口兼容"""

    def __init__(self):
        self.db = DatabaseManager()

    # ── CRUD ──

    def create(self, content: str, source: str = "text", source_url: Optional[str] = None,
               tags: Optional[list[str]] = None, entities: Optional[list[dict]] = None,
               summary: Optional[str] = None, keywords: Optional[list[str]] = None,
               related_ids: Optional[list[str]] = None) -> dict:
        return self.db.create(
            content=content, source=source, source_url=source_url,
            tags=tags, entities=entities, summary=summary,
            keywords=keywords, related_ids=related_ids,
        )

    def get(self, mem_id: str) -> Optional[dict]:
        return self.db.get(mem_id)

    def list_all(self, tag: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[dict]:
        return self.db.list_all(tag=tag, limit=limit, offset=offset)

    def update(self, mem_id: str, **kwargs) -> Optional[dict]:
        return self.db.update(mem_id, **kwargs)

    def delete(self, mem_id: str) -> bool:
        return self.db.delete(mem_id)

    # ── 搜索 ──

    def search_keyword(self, query: str, limit: int = 20) -> list[dict]:
        """关键词搜索（保持旧接口，返回旧格式）"""
        results = self.db.search_fts(query, limit=limit)
        return [
            {
                "memory": r,
                "score": float(r.get("bm25_score", 0)),
                "match_reason": "全文匹配",
            }
            for r in results
        ]

    # ── 标签 & 统计 ──

    def get_all_tags(self) -> list[dict]:
        return self.db.get_all_tags()

    def get_stats(self) -> dict:
        return self.db.get_stats()

    # ── 关联 ──

    def find_related(self, mem_id: str, limit: int = 5) -> list[dict]:
        return self.db.find_related(mem_id, limit=limit)
