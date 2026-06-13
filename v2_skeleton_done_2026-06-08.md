# 记忆外挂 v2 骨架完成 — 2026-06-08 20:50

## 目标
从 v1 的 JSON 文件存储升级到 SQLite + FTS5 + 向量搜索，支持三个核心功能：语义搜索、记忆问答（RAG）、定时回顾。

## 新增/重写文件

| 文件 | 行数 | 作用 |
|------|------|------|
| `db.py` | 13.6KB | SQLite + FTS5 数据库层，含 UDF、迁移、全文搜索 |
| `embedder.py` | 4.2KB | 智谱 Embedding API，纯 Python struct 序列化（零依赖） |
| `search.py` | 3.4KB | 混合搜索引擎，融合 FTS5 + 余弦相似度 |
| `store.py` | 2.1KB | 委托给 DatabaseManager，保持旧接口兼容 |
| `main.py` | 9.3KB | 重写，新增 semantic/hybrid 搜索、批量向量化接口 |

## 架构决策

- **零 numpy 依赖**：numpy 2.4.6 安装 OOM killed，改用 `struct.pack/unpack` + 纯 Python 余弦相似度（1024维 ~0.5ms，完全够用）
- **FTS5 触发器修复**：`INSERT ... VALUES('delete')` 在 SQLite 3.50.4 不兼容，改用 `DELETE FROM fts WHERE id=`
- **中文搜索**：FTS5 对中文无效（无分词），搜索时自动 LIKE 回退
- **Embedding 现状**：智谱 `embedding-3` 免费层限流（HTTP 429），语义搜索在 embedding 不可用时优雅降级为空结果
- **JSON → SQLite 迁移**：首次启动时自动从 data/memories.json 迁移

## 已测试通过

- 全部模块导入 ✓
- 数据库 CRUD（含 Update 触发器） ✓
- 关键词搜索（FTS5 + LIKE 回退） ✓
- AI 自动加工（标签/实体/摘要） ✓
- 标签统计 ✓
- 向量序列化（pack/unpack） ✓
- 余弦相似度计算 ✓

## 下一步建议

- **语义搜索可用**：升级 API Plan 或换 embedding 模型（如 text-embedding-3-small）
- **RAG 记忆问答**：结合搜索 + LLM 回答"我上个月学了什么"类问题
- **定时回顾**：cron 触发每日/每周随机回顾
- **小程序前端适配**：搜索接口从单 mode 改为 keyword/semantic/hybrid 三模式
