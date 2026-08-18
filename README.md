# 记忆外挂 MemFlow

微信小程序 + FastAPI 后端的个人记忆管理工具，让碎片信息转化为持久知识。

## 功能

- **捕获** — 随时记录想法、灵感、摘录
- **发现** — 浏览社区推荐内容
- **搜索** — 语义搜索 + 关键词混合搜索
- **详情** — 单条记忆的完整查看与编辑

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | 微信小程序（原生组件，5 个 Tab 页面） |
| 后端 | FastAPI + SQLite + FTS5 全文搜索 |
| AI | 支持 LLM 生成摘要 + 向量 Embedding 语义检索 |
| 部署 | 单文件入口，`uvicorn main:app --port 8701` |

## 快速启动

```bash
# 后端
pip install -r requirements.txt
cp .env.example .env   # 填入 API Key
uvicorn main:app --reload --port 8701

# 小程序
# 导入 pages/ 至微信开发者工具，填入后端地址
```

## 主要文件

| 文件 | 说明 |
|------|------|
| `main.py` | FastAPI 主入口 |
| `models.py` | Pydantic 数据模型 |
| `store.py` | SQLite 持久层 |
| `embedder.py` | Embedding 向量服务 |
| `search.py` | 混合搜索（BM25 + 向量） |
| `ai_processor.py` | LLM 摘要生成 |
| `app.js` | 小程序全局逻辑 |
| `config.py` | 配置管理 |

## 环境变量

参考 `.env.example`
