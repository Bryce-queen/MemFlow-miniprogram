"""
记忆外挂 v2 — SQLite 数据库层
FTS5 全文索引 + 向量存储 + JSON 迁移
"""
import json
import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime
from typing import Optional

from config import get_config

logger = logging.getLogger(__name__)


_SCHEMA = """
-- 主记忆表
CREATE TABLE IF NOT EXISTS memories (
    id         TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT 'text',
    source_url TEXT,
    tags       TEXT NOT NULL DEFAULT '[]',       -- JSON array
    entities   TEXT NOT NULL DEFAULT '[]',       -- JSON array of {name,type}
    summary    TEXT DEFAULT '',
    keywords   TEXT NOT NULL DEFAULT '[]',       -- JSON array
    related_ids TEXT NOT NULL DEFAULT '[]',      -- JSON array
    embedding  BLOB,                             -- float32[] 序列化
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- FTS5 全文索引
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    id UNINDEXED,
    content,
    summary,
    tags,
    keywords,
    tokenize='unicode61 remove_diacritics 1'
);

-- 插入时同步 FTS
CREATE TRIGGER IF NOT EXISTS mem_fts_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(id, content, summary, tags, keywords)
    VALUES (new.id, new.content, new.summary, new.tags, new.keywords);
END;

-- 删除时同步 FTS
CREATE TRIGGER IF NOT EXISTS mem_fts_ad AFTER DELETE ON memories BEGIN
    DELETE FROM memories_fts WHERE id = old.id;
END;

-- 更新时同步 FTS
CREATE TRIGGER IF NOT EXISTS mem_fts_au AFTER UPDATE ON memories BEGIN
    DELETE FROM memories_fts WHERE id = old.id;
    INSERT INTO memories_fts(id, content, summary, tags, keywords)
    VALUES (new.id, new.content, new.summary, new.tags, new.keywords);
END;

-- 索引
CREATE INDEX IF NOT EXISTS idx_mem_created ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_mem_source ON memories(source);

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
"""


class DatabaseManager:
    """SQLite 数据库管理器 — 线程安全"""

    def __init__(self, db_path: Optional[str] = None):
        cfg = get_config()
        self.db_path = db_path or cfg.db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._local = threading.local()
        self._register_udfs()
        self._init_schema()
        self._migrate_json()
        logger.info("Database ready: %s (%d memories)", self.db_path, self.count())

    def _register_udfs(self):
        """注册自定义 SQL 函数"""
        self.conn.create_function(
            "json_array_contains", 2,
            lambda arr, val: int(val in json.loads(arr)),
            deterministic=True,
        )

    # ── 连接管理 ──

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_schema(self):
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def _migrate_json(self):
        """从旧版 memories.json 迁移数据"""
        json_path = os.path.join(os.path.dirname(self.db_path), "memories.json")
        if not os.path.exists(json_path):
            return
        if self.count() > 0:
            return  # 已有数据，跳过
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data:
                return
            logger.info("Migrating %d records from JSON...", len(data))
            items = list(data.values()) if isinstance(data, dict) else data
            for mem in items:
                if isinstance(mem, dict):
                    self.insert_raw(mem)
            logger.info("Migration complete: %d records", len(items))
        except Exception as e:
            logger.warning("JSON migration skipped: %s", e)

    # ── CRUD ──

    def insert_raw(self, mem: dict):
        """插入原始字典（用于迁移）"""
        self.conn.execute(
            """INSERT OR IGNORE INTO memories
               (id, content, source, source_url, tags, entities, summary, keywords,
                related_ids, embedding, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mem["id"],
                mem["content"],
                mem.get("source", "text"),
                mem.get("source_url"),
                json.dumps(mem.get("tags", []), ensure_ascii=False),
                json.dumps(mem.get("entities", []), ensure_ascii=False),
                mem.get("summary", ""),
                json.dumps(mem.get("keywords", []), ensure_ascii=False),
                json.dumps(mem.get("related_ids", []), ensure_ascii=False),
                None,
                mem.get("created_at", datetime.now().isoformat()),
                mem.get("updated_at", datetime.now().isoformat()),
            ),
        )
        self.conn.commit()

    def create(self, content: str, source: str = "text", source_url: Optional[str] = None,
               tags: Optional[list[str]] = None, entities: Optional[list[dict]] = None,
               summary: Optional[str] = None, keywords: Optional[list[str]] = None,
               related_ids: Optional[list[str]] = None, embedding: Optional[bytes] = None) -> dict:
        mem_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        self.conn.execute(
            """INSERT INTO memories (id, content, source, source_url, tags, entities,
               summary, keywords, related_ids, embedding, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mem_id, content, source, source_url,
                json.dumps(tags or [], ensure_ascii=False),
                json.dumps(entities or [], ensure_ascii=False),
                summary or "",
                json.dumps(keywords or [], ensure_ascii=False),
                json.dumps(related_ids or [], ensure_ascii=False),
                embedding, now, now,
            ),
        )
        self.conn.commit()
        return self.get(mem_id)

    def get(self, mem_id: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_all(self, tag: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[dict]:
        if tag:
            rows = self.conn.execute(
                """SELECT * FROM memories
                   WHERE json_array_contains(tags, ?)
                   ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                (tag, limit, offset),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update(self, mem_id: str, **kwargs) -> Optional[dict]:
        existing = self.get(mem_id)
        if not existing:
            return None
        # 合并更新
        for key in ("content", "source_url", "summary"):
            if key in kwargs and kwargs[key] is not None:
                existing[key] = kwargs[key]
        for json_key in ("tags", "entities", "keywords", "related_ids"):
            if json_key in kwargs and kwargs[json_key] is not None:
                existing[json_key] = kwargs[json_key]
        if "embedding" in kwargs and kwargs["embedding"] is not None:
            existing["_embedding"] = kwargs["embedding"]
        existing["updated_at"] = datetime.now().isoformat()

        self.conn.execute(
            """UPDATE memories SET content=?, source_url=?, tags=?, entities=?,
               summary=?, keywords=?, related_ids=?, embedding=?, updated_at=?
               WHERE id=?""",
            (
                existing["content"], existing.get("source_url"),
                json.dumps(existing["tags"], ensure_ascii=False),
                json.dumps(existing["entities"], ensure_ascii=False),
                existing.get("summary", ""),
                json.dumps(existing["keywords"], ensure_ascii=False),
                json.dumps(existing["related_ids"], ensure_ascii=False),
                existing.pop("_embedding", existing.get("_embedding")),
                existing["updated_at"], mem_id,
            ),
        )
        self.conn.commit()
        return self.get(mem_id)

    def delete(self, mem_id: str) -> bool:
        cur = self.conn.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    # ── 全文搜索 (FTS5) ──

    def search_fts(self, query: str, limit: int = 20) -> list[dict]:
        """全文搜索：FTS5 + LIKE 回退"""
        results = []
        seen_ids = set()

        # 1. FTS5 搜索（英文/数字/中文）
        fts_query = " OR ".join(w for w in query.split() if len(w) > 1) if any(
            c.isascii() and c.isalpha() for c in query
        ) else query.replace(" ", " OR ")
        try:
            rows = self.conn.execute(
                """SELECT m.*, fts.rank AS bm25_score
                   FROM memories_fts fts
                   JOIN memories m ON fts.id = m.id
                   WHERE memories_fts MATCH ?
                   ORDER BY bm25_score
                   LIMIT ?""",
                (fts_query, limit),
            ).fetchall()
            for r in rows:
                d = self._row_to_dict(r)
                d["bm25_score"] = r["bm25_score"]
                results.append(d)
                seen_ids.add(d["id"])
        except sqlite3.OperationalError:
            pass

        # 2. LIKE 回退（中文 + 补充结果）
        remaining = limit - len(results)
        if remaining > 0:
            like_q = f"%{query}%"
            rows = self.conn.execute(
                """SELECT * FROM memories
                   WHERE content LIKE ? OR summary LIKE ? OR tags LIKE ? OR keywords LIKE ?
                   ORDER BY created_at DESC LIMIT ?""",
                (like_q, like_q, like_q, like_q, remaining * 2),
            ).fetchall()
            for r in rows:
                d = self._row_to_dict(r)
                if d["id"] not in seen_ids:
                    d["bm25_score"] = -1  # LIKE 无 BM25 分数
                    results.append(d)
                    seen_ids.add(d["id"])

        return results[:limit]

    # ── 向量搜索 ──

    def get_all_embeddings(self) -> list[tuple[str, Optional[bytes]]]:
        """获取所有有 embedding 的记忆"""
        rows = self.conn.execute(
            "SELECT id, embedding FROM memories WHERE embedding IS NOT NULL"
        ).fetchall()
        return [(r["id"], r["embedding"]) for r in rows]

    def get_many_by_ids(self, ids: list[str]) -> list[dict]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self.conn.execute(
            f"SELECT * FROM memories WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ── 统计 ──

    def get_all_tags(self) -> list[dict]:
        rows = self.conn.execute("SELECT tags FROM memories").fetchall()
        counts = {}
        for r in rows:
            for tag in json.loads(r["tags"]):
                counts[tag] = counts.get(tag, 0) + 1
        return [{"name": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]

    def get_stats(self) -> dict:
        from datetime import timedelta
        now = datetime.now()
        week_ago = (now - timedelta(days=7)).isoformat()
        total = self.count()
        recent = self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE created_at >= ?", (week_ago,)
        ).fetchone()[0]
        tags = self.get_all_tags()
        return {
            "total_memories": total,
            "total_tags": len(tags),
            "recent_count_7d": recent,
            "top_tags": tags[:10],
        }

    def find_related(self, mem_id: str, limit: int = 5) -> list[dict]:
        """基于标签/实体 Jaccard 相似度找关联记忆
        TODO(v3): 改用向量余弦相似度替代全量扫描
        """
        target = self.get(mem_id)
        if not target:
            return []
        target_tags = set(target["tags"])
        target_entities = set(e["name"] for e in target["entities"])
        all_memories = [
            m for m in self.list_all(limit=1000) if m["id"] != mem_id
        ]
        scored = []
        for mem in all_memories:
            score = len(target_tags & set(mem["tags"])) * 3
            score += len(target_entities & set(e["name"] for e in mem["entities"])) * 2
            if score > 0:
                scored.append((score, mem))
        scored.sort(key=lambda x: -x[0])
        return [m for _, m in scored][:limit]

    # ── 工具 ──

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        d.pop("embedding", None)  # 不返回二进制 embedding
        for key in ("tags", "entities", "keywords", "related_ids"):
            try:
                d[key] = json.loads(d.get(key, "[]"))
            except (json.JSONDecodeError, TypeError):
                d[key] = [] if key != "entities" else []
                if key == "entities":
                    d[key] = []
        return d
