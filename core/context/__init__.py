"""
上下文存储模块

提供基于 Markdown 文件的会话上下文存储功能，以及 Token 经济学管理。

核心模块：
- MarkdownContextStore: 基础 Markdown 存储器
- SessionContext: 会话上下文数据结构
- TokenCalculator: Token 精确计算器
- TokenEconomicsContextStore: 分层压缩上下文存储

高级模块：
- ContextTierManager: 三层上下文管理器
- SmartSummarizer: 智能摘要生成器
- IncrementalStore: 增量写入引擎
- CacheOptimizer: 缓存优化器（实验性，未集成）

接口约定（对齐 PromptBuilder）：
- get_messages_for_llm() -> optimized_history
- TokenCalculator.count_tokens() -> int

Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md
"""

from .markdown_store import MarkdownContextStore, SessionContext
from .token_economics import (
    TokenCalculator,
    TokenEconomicsContextStore,
    ContextTierManager,
    SmartSummarizer,
    IncrementalStore,
    TierConfig,
    ZoneType,
)

__all__ = [
    "MarkdownContextStore",
    "SessionContext",
    "TokenCalculator",
    "TokenEconomicsContextStore",
    "ContextTierManager",
    "SmartSummarizer",
    "IncrementalStore",
    "TierConfig",
    "ZoneType",
]
