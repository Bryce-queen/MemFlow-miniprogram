"""
记忆外挂 v2 — FastAPI 主入口
启动: uvicorn main:app --reload --port 8701
"""
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from config import get_config
from models import MemoryCreate, MemoryResponse, MemoryUpdate, SearchResult, StatsResponse
from store import MemoryStore
from ai_processor import AIProcessor
from embedder import EmbeddingService
from search import HybridSearch

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

store = MemoryStore()
processor = AIProcessor()
embedder = EmbeddingService()
hybrid_search = HybridSearch(store.db, embedder)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🧠 记忆外挂 v2 启动")
    if processor.is_available():
        logger.info(f"✅ AI 处理器就绪, 模型: {processor.model}")
    else:
        logger.warning("⚠️  LLM API Key 未配置, 将使用规则提取模式")
    if embedder.is_available():
        logger.info(f"✅ Embedding 就绪, 模型: {embedder.model}, 维度: {embedder.dim}")
    else:
        logger.warning("⚠️  Embedding API 不可用, 语义搜索禁用")
    yield
    logger.info("🧠 记忆外挂 v2 关闭")


app = FastAPI(
    title="记忆外挂 API v2",
    description="你的第二大脑 — SQLite + FTS5 + 向量搜索",
    version="2.0.0",
    lifespan=lifespan,
)


# ── 认证中间件 ──

_UNPROTECTED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """API Key 认证中间件 — 密钥为空时自动放行（本地开发模式）"""

    async def dispatch(self, request: Request, call_next):
        cfg = get_config()
        # 未配置密钥 = 本地开发模式，跳过认证
        if not cfg.api_key:
            return await call_next(request)
        # 健康检查 / 文档页免认证
        if request.url.path in _UNPROTECTED_PATHS:
            return await call_next(request)
        # 校验 X-API-Key 头
        client_key = request.headers.get("X-API-Key", "")
        if client_key != cfg.api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "无效或缺失 API Key"},
            )
        return await call_next(request)


# ── 限流中间件 ──

class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单令牌桶限流 — 每 IP 每分钟 N 次"""

    def __init__(self, app, max_per_min: int = 60):
        super().__init__(app)
        self.max_per_min = max_per_min
        self._windows: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _UNPROTECTED_PATHS:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = now - 60  # 滑动窗口 60s

        # 清理过期记录
        self._windows[ip] = [t for t in self._windows[ip] if t > window]

        if len(self._windows[ip]) >= self.max_per_min:
            logger.warning(f"⛔ 限流触发: {ip} ({len(self._windows[ip])} req/min)")
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后重试"},
            )

        self._windows[ip].append(now)
        return await call_next(request)


from starlette.responses import JSONResponse

app.add_middleware(
    APIKeyMiddleware,
)
app.add_middleware(
    RateLimitMiddleware,
    max_per_min=get_config().rate_limit_per_min,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 健康检查 ──

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "ai_available": processor.is_available(),
        "model": processor.model if processor.is_available() else None,
        "embedding_available": embedder.is_available(),
        "embedding_model": embedder.model if embedder.is_available() else None,
        "total_memories": store.db.count(),
    }


# ── 记忆 CRUD ──

@app.post("/memories", response_model=MemoryResponse, status_code=201)
def create_memory(body: MemoryCreate):
    """创建记忆，AI 自动加工 + 向量化"""
    logger.info(f"📥 新记忆: {body.content[:50]}...")

    # 1. AI 加工
    ai_result = processor.process(body.content)
    tags = ai_result.get("tags", [])
    entities = ai_result.get("entities", [])
    summary = ai_result.get("summary", "")
    keywords = ai_result.get("keywords", [])

    # 2. 创建记忆（先不写 embedding）
    mem = store.create(
        content=body.content,
        source=body.source.value,
        source_url=body.source_url,
        tags=tags,
        entities=entities,
        summary=summary,
        keywords=keywords,
    )

    # 3. 生成 embedding（异步更新）
    if embedder.is_available():
        try:
            vec = embedder.encode(body.content)
            if vec is not None:
                store.db.update(mem["id"], embedding=embedder.pack(vec))
                logger.debug(f"🧬 Embedding 已生成: {mem['id']}")
                mem = store.get(mem["id"])  # 刷新以获取新标签
        except Exception as e:
            logger.warning(f"Embedding 生成失败: {e}")

    # 4. 关联检测
    all_memories = store.list_all(limit=200)
    related = processor.detect_links(mem, all_memories)
    if related:
        store.update(mem["id"], related_ids=related)
        mem["related_ids"] = related
        for rid in related:
            rmem = store.get(rid)
            if rmem and mem["id"] not in rmem.get("related_ids", []):
                store.update(rid, related_ids=rmem.get("related_ids", []) + [mem["id"]])

    logger.info(f"✅ 记忆 {mem['id']} 创建, 标签: {tags}")
    return MemoryResponse(**mem)


@app.get("/memories", response_model=list[MemoryResponse])
def list_memories(
    tag: str = Query(default=None, description="按标签筛选"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """获取记忆列表，支持标签过滤"""
    memories = store.list_all(tag=tag, limit=limit, offset=offset)
    return [MemoryResponse(**m) for m in memories]


@app.get("/memories/search", response_model=list[SearchResult])
def search_memories(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(default=20, ge=1, le=50),
    mode: str = Query(default="keyword", description="keyword / semantic / hybrid"),
):
    """
    搜索记忆
    - keyword: 全文关键词搜索（FTS5 + LIKE）
    - semantic: 语义向量搜索
    - hybrid: 混合搜索（关键词 + 语义）
    """
    logger.info(f"🔍 搜索 [{mode}]: {q}")

    if mode == "semantic" and embedder.is_available():
        query_vec = embedder.encode(q)
        if query_vec is not None:
            candidates = store.db.get_all_embeddings()
            scored = embedder.search(query_vec, candidates, top_k=limit)
            mem_map = {m["id"]: m for m in store.db.get_many_by_ids([s[0] for s in scored])}
            return [
                SearchResult(memory=mem_map[mid], score=score, match_reason="语义相似")
                for mid, score in scored if mid in mem_map
            ]
        # fallback to keyword
        results = store.search_keyword(q, limit=limit)
        return [SearchResult(**r) for r in results]

    elif mode == "hybrid":
        results = hybrid_search.search(q, limit=limit)
        return [SearchResult(**r) for r in results]

    else:  # keyword (default)
        results = store.search_keyword(q, limit=limit)
        return [SearchResult(**r) for r in results]


@app.get("/memories/{mem_id}", response_model=MemoryResponse)
def get_memory(mem_id: str):
    """获取单条记忆详情"""
    mem = store.get(mem_id)
    if not mem:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return MemoryResponse(**mem)


@app.patch("/memories/{mem_id}", response_model=MemoryResponse)
def update_memory(mem_id: str, body: MemoryUpdate):
    """手动编辑记忆"""
    mem = store.update(
        mem_id,
        content=body.content,
        tags=body.tags,
        summary=body.summary,
    )
    if not mem:
        raise HTTPException(status_code=404, detail="记忆不存在")
    # 如果内容变更了，重新生成 embedding
    if body.content and embedder.is_available():
        try:
            vec = embedder.encode(body.content)
            if vec is not None:
                store.db.update(mem_id, embedding=embedder.pack(vec))
        except Exception as e:
            logger.warning(f"Re-embedding 失败: {e}")
    return MemoryResponse(**store.get(mem_id) or mem)


@app.delete("/memories/{mem_id}", status_code=204)
def delete_memory(mem_id: str):
    """删除一条记忆"""
    if not store.delete(mem_id):
        raise HTTPException(status_code=404, detail="记忆不存在")


# ── 标签 & 统计 ──

@app.get("/tags")
def list_tags():
    """获取所有标签及计数"""
    return store.get_all_tags()


@app.get("/stats", response_model=StatsResponse)
def get_stats():
    """获取统计信息"""
    return StatsResponse(**store.get_stats())


# ── 关联记忆 ──

@app.get("/memories/{mem_id}/related", response_model=list[MemoryResponse])
def get_related_memories(mem_id: str):
    """获取与指定记忆关联的其他记忆"""
    mem = store.get(mem_id)
    if not mem:
        raise HTTPException(status_code=404, detail="记忆不存在")
    related = []
    for rid in mem.get("related_ids", []):
        rmem = store.get(rid)
        if rmem:
            related.append(MemoryResponse(**rmem))
    return related


# ── 批量向量化 ──

@app.post("/admin/reindex-embeddings", status_code=200)
def reindex_embeddings():
    """为所有缺少 embedding 的记忆生成向量（管理接口）"""
    if not embedder.is_available():
        raise HTTPException(status_code=400, detail="Embedding 服务不可用")

    all_mems = store.list_all(limit=10000)
    missing = store.db.conn.execute(
        "SELECT id, content FROM memories WHERE embedding IS NULL"
    ).fetchall()

    if not missing:
        return {"message": "所有记忆已有 embedding", "count": 0}

    logger.info(f"🔧 开始向量化 {len(missing)} 条记忆...")
    count = 0
    batch_size = 10
    for i in range(0, len(missing), batch_size):
        batch = missing[i:i + batch_size]
        texts = [r["content"] for r in batch]
        vecs = embedder.encode_batch(texts)
        for r, vec in zip(batch, vecs):
            if vec is not None:
                store.db.conn.execute(
                    "UPDATE memories SET embedding = ? WHERE id = ?",
                    (embedder.pack(vec), r["id"]),
                )
                count += 1
        store.db.conn.commit()
        if i + batch_size < len(missing):
            logger.info(f"  进度: {min(i + batch_size, len(missing))}/{len(missing)}")

    logger.info(f"✅ 向量化完成: {count}/{len(missing)}")
    return {"message": f"已为 {count} 条记忆生成 embedding", "count": count}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8701, reload=True)
