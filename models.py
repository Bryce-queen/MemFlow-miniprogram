"""
记忆外挂 v2 — Pydantic 数据模型
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    text = "text"
    voice = "voice"
    image = "image"
    link = "link"
    wechat = "wechat"


class MemoryCreate(BaseModel):
    """创建记忆请求体"""
    content: str = Field(..., min_length=1, max_length=5000, description="记忆正文")
    source: SourceType = Field(default=SourceType.text, description="来源类型")
    source_url: Optional[str] = Field(default=None, description="来源链接")


class MemoryUpdate(BaseModel):
    """更新记忆请求体 — 所有字段可选"""
    content: Optional[str] = Field(default=None, description="新内容")
    tags: Optional[list[str]] = Field(default=None, description="新标签列表")
    summary: Optional[str] = Field(default=None, description="新摘要")


class EntityItem(BaseModel):
    """实体信息"""
    name: str
    type: str  # person / book / place / org / date / other


class MemoryResponse(BaseModel):
    """记忆响应体"""
    id: str
    content: str
    source: str
    source_url: Optional[str] = None
    tags: list[str] = []
    entities: list = []
    summary: str = ""
    keywords: list[str] = []
    related_ids: list[str] = []
    created_at: str
    updated_at: str


class SearchResult(BaseModel):
    """搜索结果"""
    memory: MemoryResponse
    score: float
    match_reason: str


class TagItem(BaseModel):
    """标签统计项"""
    name: str
    count: int


class StatsResponse(BaseModel):
    """统计响应体"""
    total_memories: int
    total_tags: int
    recent_count_7d: int
    top_tags: list[dict] = []
