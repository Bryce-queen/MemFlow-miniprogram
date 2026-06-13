# 记忆外挂 · 后端骨架搭建完成

**日期**: 2026-06-08 09:33-09:35
**状态**: 后端 MVP 完成，全链路跑通

## 产出
- memory-app/config.py - 配置模块（LLM API、存储路径）
- memory-app/models.py - Pydantic 数据模型（MemoryCreate/Response/Update/SearchResult/TagStats/StatsResponse）
- memory-app/store.py - JSON 文件存储（create/get/list/search/update/delete/get_all_tags/get_stats/find_related）
- memory-app/ai_processor.py - AI 加工器（标签提取、实体提取、摘要生成、关联检测）
- memory-app/main.py - FastAPI 入口（9个端点 + CORS + 健康检查）
- memory-app/requirements.txt

## API 端点
POST /memories, GET /memories, GET /memories/search, GET /memories/{id}, PATCH /memories/{id}, DELETE /memories/{id}, GET /memories/{id}/related, GET /tags, GET /stats, GET /health

## 当前模式
AI 处理器运行在规则模式（LLM API Key 未配置），接上 DeepSeek Key 后自动切换到 AI 模式。

## 下一步选项
A) 接 DeepSeek Key 验证 AI 加工效果
B) 开始搭微信小程序前端
C) 升级存储层到 PostgreSQL
D) 用户决定
