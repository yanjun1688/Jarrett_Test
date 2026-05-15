"""
Token Economics 模块

提供 Token 精确计算、分层压缩等功能。

核心组件：
- TokenCalculator: Token 精确计算器
- TokenEconomicsContextStore: 分层压缩上下文存储
- TierConfig: 三层配置数据类
- ContextTierManager: 三层上下文管理器
- SmartSummarizer: 智能摘要生成器
- IncrementalStore: 增量写入引擎
- CacheOptimizer: 缓存优化器（实验性，未集成）

接口约定（对齐 PromptBuilder）：
- get_messages_for_llm() -> optimized_history
- TokenCalculator.count_tokens() -> int

使用示例：
    from core.context.token_economics import (
        TokenCalculator,
        TokenEconomicsContextStore,
        ContextTierManager,
        SmartSummarizer
    )

    # Token 计算
    calc = TokenCalculator(model_name="gpt-4")
    tokens = calc.count_tokens("Hello world")

    # 上下文存储
    store = TokenEconomicsContextStore(root_dir=Path("context_data"), model_name="gpt-4")
    messages = store.get_messages_for_llm(session_id="xxx", user_id="1")

    # 三层管理
    tier_manager = ContextTierManager(total_budget=5632)
    tier_state = tier_manager.calculate_tier_state(messages, calc)

    # 智能摘要
    summarizer = SmartSummarizer()
    summary = summarizer.generate_warm_summary(messages, calc)

Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md
"""

from .token_calculator import TokenCalculator
from .context_store import TokenEconomicsContextStore
from .tier_manager import (
    TierState,
    ZoneInfo,
    ContextTierManager,
)
from .smart_summarizer import (
    SmartSummarizer,
    SummaryConfig,
)
from .incremental_store import (
    IncrementalStore,
    SessionIndex,
    IndexEntry,
)
# CacheOptimizer/CacheFriendlyPromptBuilder 已实现但未集成到 prompt 构建流程，暂不导出
# from .cache_optimizer import (
#     CacheOptimizer,
#     CacheStats,
#     CacheConfig,
#     CacheFriendlyPromptBuilder,
# )
from .base import (
    OptimizedContext,
    CompressionResult,
    TokenStatistics,
    ZoneType,
    CalculationMethod,
    TierConfig,
    StructuredSummary,
    get_model_config,
)

__all__ = [
    "TokenCalculator",
    "TokenEconomicsContextStore",
    "TierConfig",
    "TierState",
    "ZoneInfo",
    "ContextTierManager",
    "SmartSummarizer",
    "StructuredSummary",
    "SummaryConfig",
    "IncrementalStore",
    "SessionIndex",
    "IndexEntry",
    "OptimizedContext",
    "CompressionResult",
    "TokenStatistics",
    "ZoneType",
    "CalculationMethod",
    "get_model_config",
]
