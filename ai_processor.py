"""
记忆外挂 v2 — AI 处理器
LLM 模式：调 LLM API 提取标签/实体/摘要/关键词
规则模式：纯 Python 启发式提取（无需 API Key）
"""
import json
import logging
import re
from typing import Optional

import httpx

from config import get_config

logger = logging.getLogger(__name__)


# ── 规则模式：常见中文停用词 ──
_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "这个",
    "那个", "可以", "这个", "什么", "怎么", "如果", "因为", "所以", "但是",
    "然后", "而且", "或者", "虽然", "不过", "还是", "只是", "已经", "比较",
    "非常", "真的", "还是", "特别", "应该", "可能", "需要", "觉得", "知道",
}


# ── 规则模式：实体提取正则 ──
_ENTITY_PATTERNS = [
    # 书名
    (r'《([^》]+)》', 'book'),
    # 日期
    (r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?)', 'date'),
    # 时间
    (r'(今天|昨天|明天|上周|下周|本月|上月|今年|去年)', 'date'),
    # URL
    (r'https?://[^\s，。！？、]+', 'link'),
    # 邮箱
    (r'[\w.-]+@[\w.-]+\.\w+', 'contact'),
    # 手机号
    (r'1[3-9]\d{9}', 'contact'),
]


class AIProcessor:
    """AI 加工器 — 自动从记忆中提取结构化信息"""

    def __init__(self):
        cfg = get_config()
        self.api_base = cfg.llm_api_base.rstrip("/")
        self.api_key = cfg.llm_api_key
        self.model = cfg.llm_model
        self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    # ── 主加工入口 ──

    def process(self, content: str) -> dict:
        """对一条记忆进行 AI 加工，返回 {tags, entities, summary, keywords}"""
        if self.is_available():
            try:
                return self._ai_process(content)
            except Exception as e:
                logger.warning("AI 加工失败，回退到规则模式: %s", e)
        return self._rule_process(content)

    # ── AI 模式 ──

    def _ai_process(self, content: str) -> dict:
        """调 LLM API 进行结构化提取"""
        prompt = _build_extraction_prompt(content)
        response = self._call_llm(prompt)

        # 尝试从 Markdown 代码块中解析 JSON
        json_str = response
        if "```json" in response:
            match = re.search(r"```json\s*([\s\S]*?)```", response)
            if match:
                json_str = match.group(1)
        elif "```" in response:
            match = re.search(r"```\s*([\s\S]*?)```", response)
            if match:
                json_str = match.group(1)

        try:
            result = json.loads(json_str.strip())
        except json.JSONDecodeError:
            logger.warning("LLM 返回非 JSON，使用规则回退: %s", response[:100])
            return self._rule_process(content)

        return {
            "tags": self._clean_list(result.get("tags", [])),
            "entities": result.get("entities", []),
            "summary": result.get("summary", ""),
            "keywords": self._clean_list(result.get("keywords", [])),
        }

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM API"""
        resp = self.client.post(
            f"{self.api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个知识管理助手，擅长从文本中提取结构化信息。请严格按 JSON 格式回复。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 800,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    # ── 规则模式（零依赖回退）──

    def _rule_process(self, content: str) -> dict:
        """纯 Python 启发式提取"""
        tags = self._extract_tags_rule(content)
        entities = self._extract_entities_rule(content)
        summary = self._generate_summary_rule(content)
        keywords = self._extract_keywords_rule(content)
        return {
            "tags": tags,
            "entities": entities,
            "summary": summary,
            "keywords": keywords,
        }

    def _extract_tags_rule(self, content: str) -> list[str]:
        """基于 n-gram + 词频提取标签"""
        # 1. 提取英文单词（2+字母）
        eng_words = re.findall(r'[a-zA-Z]{2,}', content)

        # 2. 中文 n-gram（2-4字）
        chinese = re.sub(r'[^\u4e00-\u9fff]', '', content)
        cn_ngrams = []
        for n in (4, 3, 2):
            for i in range(len(chinese) - n + 1):
                cn_ngrams.append(chinese[i:i + n])

        # 3. 词频统计（位置加权：越靠前权重越高）
        freq = {}
        total = len(cn_ngrams) + len(eng_words)
        for idx, w in enumerate(eng_words):
            w_lower = w.lower()
            if w_lower not in _STOP_WORDS:
                pos_weight = 1.0 + 0.5 * (1 - idx / max(total, 1))
                freq[w_lower] = freq.get(w_lower, 0) + pos_weight
        for idx, ng in enumerate(cn_ngrams):
            if ng not in _STOP_WORDS:
                pos_weight = 1.0 + 0.3 * (1 - idx / max(total, 1))
                freq[ng] = freq.get(ng, 0) + pos_weight

        # 4. 去重：短 ngram 被长 ngram 包含且频次相近则过滤
        sorted_items = sorted(freq.items(), key=lambda x: -x[1])
        tags = []
        for w, score in sorted_items:
            if len(tags) >= 8:
                break
            # 检查是否被已有标签包含
            contained = any(
                w != t and w in t and freq.get(t, 0) >= score * 0.9
                for t in tags
            )
            if not contained:
                tags.append(w)

        return tags[:8]

    def _extract_entities_rule(self, content: str) -> list[dict]:
        """用正则提取实体"""
        entities = []
        seen = set()
        for pattern, etype in _ENTITY_PATTERNS:
            for match in re.finditer(pattern, content):
                name = match.group(1) if match.lastindex else match.group(0)
                if name not in seen:
                    seen.add(name)
                    entities.append({"name": name, "type": etype})
        return entities[:10]

    def _generate_summary_rule(self, content: str) -> str:
        """简单摘要：取前 120 字符"""
        if len(content) <= 120:
            return content
        # 尝试在句号处截断
        end = content[:150].rfind("。")
        if end > 40:
            return content[:end + 1]
        return content[:120] + "…"

    def _extract_keywords_rule(self, content: str) -> list[str]:
        """提取关键词（n-gram + 去重保序）"""
        eng_words = re.findall(r'[a-zA-Z]{2,}', content)
        chinese = re.sub(r'[^\u4e00-\u9fff]', '', content)
        cn_ngrams = []
        for i in range(len(chinese) - 1):
            for n in (4, 3, 2):
                if i + n <= len(chinese):
                    cn_ngrams.append(chinese[i:i + n])
        seen = set()
        keywords = []
        for w in eng_words + cn_ngrams:
            w_lower = w.lower() if w.isascii() else w
            if w_lower not in seen and w_lower not in _STOP_WORDS and len(w_lower) >= 2:
                seen.add(w_lower)
                keywords.append(w_lower)
        return keywords[:12]

    # ── 关联检测 ──

    def detect_links(self, mem: dict, all_memories: list[dict],
                     max_links: int = 5) -> list[str]:
        """检测与已有记忆的关联，返回关联记忆 ID 列表"""
        mem_tags = set(mem.get("tags", []))
        mem_keywords = set(mem.get("keywords", []))
        mem_entities = set(e.get("name", "") for e in mem.get("entities", []))

        if not mem_tags and not mem_keywords and not mem_entities:
            return []

        scored = []
        for other in all_memories:
            if other["id"] == mem.get("id"):
                continue

            o_tags = set(other.get("tags", []))
            o_keywords = set(other.get("keywords", []))
            o_entities = set(e.get("name", "") for e in other.get("entities", []))

            # 标签重叠 x3，关键词重叠 x2，实体重叠 x2
            score = len(mem_tags & o_tags) * 3
            score += len(mem_keywords & o_keywords) * 2
            score += len(mem_entities & o_entities) * 2

            # 复用 store 已有的 find_related 分数（如果有）
            if "score" in other:
                score += other["score"]

            if score > 0:
                scored.append((score, other["id"]))

        scored.sort(key=lambda x: -x[0])
        return [mid for _, mid in scored[:max_links]]

    # ── 工具 ──

    @staticmethod
    def _clean_list(items: list) -> list[str]:
        """清理列表：去重、去空、裁剪"""
        seen = set()
        result = []
        for item in items:
            if isinstance(item, str):
                s = item.strip()
                if s and s not in seen:
                    seen.add(s)
                    result.append(s)
        return result[:15]


def _build_extraction_prompt(content: str) -> str:
    """构建 LLM 提取提示词"""
    return f"""请从以下文本中提取结构化信息，返回纯 JSON（不要 Markdown 包裹）：

{{
    "tags": ["标签1", "标签2", ...],        // 3-8 个标签，概括主题
    "entities": [                           // 实体列表
        {{"name": "实体名", "type": "person|book|place|org|date|link"}},
        ...
    ],
    "summary": "一句话摘要，不超过 100 字",
    "keywords": ["关键词1", "关键词2", ...] // 5-10 个核心关键词
}}

原文：
{content[:3000]}"""
