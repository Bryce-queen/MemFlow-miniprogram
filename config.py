"""
记忆外挂 v2 — 配置模块
"""
import os
from dataclasses import dataclass, field
from typing import Optional

try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(_env_path)
except ImportError:
    pass


@dataclass
class Config:
    """全局配置"""

    # ── LLM API ──
    llm_api_base: str = os.getenv("MEMORY_LLM_BASE", "https://open.bigmodel.cn/api/paas/v4")
    llm_api_key: str = os.getenv("MEMORY_LLM_KEY", "")
    llm_model: str = os.getenv("MEMORY_LLM_MODEL", "glm-4.5-air")

    # ── Embedding API ──
    embedding_api_base: str = os.getenv("MEMORY_EMBEDDING_BASE", "")  # 默认与 LLM 同源
    embedding_api_key: str = os.getenv("MEMORY_EMBEDDING_KEY", "")    # 默认与 LLM 同 Key
    embedding_model: str = os.getenv("MEMORY_EMBEDDING_MODEL", "embedding-3")
    embedding_dim: int = int(os.getenv("MEMORY_EMBEDDING_DIM", "1024"))

    # ── 存储 ──
    data_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data"
    ))
    db_path: str = ""  # 惰性计算

    def __post_init__(self):
        if not self.db_path:
            self.db_path = os.path.join(self.data_dir, "memories.db")
        if not self.embedding_api_base:
            self.embedding_api_base = self.llm_api_base
        if not self.embedding_api_key:
            self.embedding_api_key = self.llm_api_key
        # 校验 hybrid_alpha 范围
        if not (0.0 <= self.hybrid_alpha <= 1.0):
            self.hybrid_alpha = 0.5

    # ── 限流 ──
    rate_limit_per_min: int = int(os.getenv("MEMORY_RATE_LIMIT", "60"))  # 每 IP 每分钟最大请求数

    # ── 搜索 ──
    hybrid_alpha: float = float(os.getenv("MEMORY_HYBRID_ALPHA", "0.5"))  # 0=纯语义, 1=纯关键词

    # ── API 安全 ──
    api_key: str = os.getenv("MEMORY_API_KEY", "")  # 为空时不启用认证（仅本地开发）

    # ── 微信小程序 ──
    wx_appid: str = os.getenv("WX_APPID", "")
    wx_secret: str = os.getenv("WX_SECRET", "")


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
