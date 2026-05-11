"""
Token 经济学基础数据模型

定义核心数据结构：
- BudgetStatus: Token 预算状态
- OptimizedContext: 优化后的上下文
- StructuredSummary: 结构化摘要（温区）
- CompressionResult: 压缩结果
- TokenStatistics: Token 使用统计
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class BudgetStatusType(Enum):
    """Token 预算状态类型"""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


class CalculationMethod(Enum):
    """Token 计算方式"""
    TIKTOKEN = "tiktoken"
    API_OR_ESTIMATE = "api_or_estimate"
    ESTIMATE = "estimate"


class ZoneType(Enum):
    """上下文区域类型"""
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


@dataclass
class TierConfig:
    """三层上下文配置"""
    hot_zone_size: int = 10
    warm_zone_size: int = 40
    cold_zone_size: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hot_zone_size": self.hot_zone_size,
            "warm_zone_size": self.warm_zone_size,
            "cold_zone_size": self.cold_zone_size
        }


@dataclass
class BudgetConfig:
    """Token 预算配置"""
    total_limit: int = 8192
    output_reserve: int = 2048
    safety_buffer: int = 512
    soft_limit_ratio: float = 0.8
    
    @property
    def effective_budget(self) -> int:
        """有效预算（扣除预留和安全缓冲）"""
        return self.total_limit - self.output_reserve - self.safety_buffer
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_limit": self.total_limit,
            "output_reserve": self.output_reserve,
            "safety_buffer": self.safety_buffer,
            "soft_limit_ratio": self.soft_limit_ratio,
            "effective_budget": self.effective_budget
        }


@dataclass
class BudgetStatus:
    """
    Token 预算状态
    
    用于描述当前会话的 Token 使用情况和预算状态
    """
    total_budget: int
    used_tokens: int
    available_tokens: int
    utilization: float
    status: BudgetStatusType
    recommendations: List[str] = field(default_factory=list)
    tier_breakdown: Dict[str, int] = field(default_factory=dict)
    
    @property
    def is_ok(self) -> bool:
        return self.status == BudgetStatusType.OK
    
    @property
    def is_warning(self) -> bool:
        return self.status == BudgetStatusType.WARNING
    
    @property
    def is_critical(self) -> bool:
        return self.status == BudgetStatusType.CRITICAL
    
    @property
    def is_exceeded(self) -> bool:
        return self.status == BudgetStatusType.EXCEEDED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_budget": self.total_budget,
            "used_tokens": self.used_tokens,
            "available_tokens": self.available_tokens,
            "utilization": self.utilization,
            "status": self.status.value,
            "recommendations": self.recommendations,
            "tier_breakdown": self.tier_breakdown
        }


@dataclass
class StructuredSummary:
    """
    结构化摘要（温区）
    
    包含主题、决策、实体和待办事项
    """
    topics: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    token_saved: int = 0
    compression_ratio: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topics": self.topics,
            "decisions": self.decisions,
            "entities": self.entities,
            "actions": self.actions,
            "token_saved": self.token_saved,
            "compression_ratio": self.compression_ratio
        }
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = []
        
        if self.topics:
            lines.append(f"<!-- topics: {self.topics} -->")
        
        if self.decisions:
            lines.append("<!-- decisions:")
            for decision in self.decisions:
                lines.append(f"  - {decision}")
            lines.append("-->")
        
        if self.entities:
            lines.append(f"<!-- entities: {self.entities} -->")
        
        if self.actions:
            lines.append("<!-- actions:")
            for action in self.actions:
                lines.append(f"  - {action}")
            lines.append("-->")
        
        lines.append(f"<!-- token_saved: {self.token_saved} -->")
        lines.append(f"<!-- compression_ratio: {self.compression_ratio:.2f} -->")
        
        return "\n".join(lines)


@dataclass
class OptimizedContext:
    """
    优化后的上下文
    
    包含热区、温区、冷区的消息和摘要
    """
    session_id: str
    user_id: str
    
    hot_zone: List[Dict[str, Any]] = field(default_factory=list)
    warm_zone: Optional[StructuredSummary] = None
    cold_zone: str = ""
    
    total_tokens: int = 0
    hot_tokens: int = 0
    warm_tokens: int = 0
    cold_tokens: int = 0
    
    compression_ratio: float = 0.0
    tokens_saved: int = 0
    original_message_count: int = 0
    
    def to_messages_for_llm(self) -> List[Dict[str, Any]]:
        """
        转换为 LLM 可用的消息格式
        
        Returns:
            包含 zone 字段的消息列表
        """
        messages = []
        
        if self.cold_zone:
            messages.append({
                "role": "system",
                "content": self.cold_zone,
                "zone": ZoneType.COLD.value + "_summary"
            })
        
        if self.warm_zone:
            warm_content = self._format_warm_summary(self.warm_zone)
            messages.append({
                "role": "system",
                "content": warm_content,
                "zone": ZoneType.WARM.value + "_summary"
            })
        
        for msg in self.hot_zone:
            msg_copy = msg.copy()
            msg_copy["zone"] = ZoneType.HOT.value
            messages.append(msg_copy)
        
        return messages
    
    def _format_warm_summary(self, summary: StructuredSummary) -> str:
        """格式化温区摘要"""
        lines = ["## 温区摘要", ""]
        
        if summary.topics:
            lines.append(f"**主题**: {', '.join(summary.topics)}")
        
        if summary.decisions:
            lines.append("**决策**:")
            for decision in summary.decisions:
                lines.append(f"- {decision}")
        
        if summary.entities:
            lines.append(f"**实体**: {', '.join(summary.entities)}")
        
        if summary.actions:
            lines.append("**待办**:")
            for action in summary.actions:
                lines.append(f"- {action}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "hot_zone": self.hot_zone,
            "warm_zone": self.warm_zone.to_dict() if self.warm_zone else None,
            "cold_zone": self.cold_zone,
            "total_tokens": self.total_tokens,
            "hot_tokens": self.hot_tokens,
            "warm_tokens": self.warm_tokens,
            "cold_tokens": self.cold_tokens,
            "compression_ratio": self.compression_ratio,
            "tokens_saved": self.tokens_saved,
            "original_message_count": self.original_message_count
        }


@dataclass
class CompressionResult:
    """压缩结果"""
    success: bool
    tokens_before: int
    tokens_after: int
    tokens_saved: int
    compression_ratio: float
    messages_compressed: int
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "tokens_saved": self.tokens_saved,
            "compression_ratio": self.compression_ratio,
            "messages_compressed": self.messages_compressed,
            "errors": self.errors
        }


@dataclass
class TokenStatistics:
    """Token 使用统计"""
    session_id: str
    user_id: str
    model_name: str
    
    total_messages: int = 0
    total_tokens: int = 0
    hot_tokens: int = 0
    warm_tokens: int = 0
    cold_tokens: int = 0
    
    calculation_method: str = CalculationMethod.TIKTOKEN.value
    calculation_accuracy: float = 0.0
    
    compression_stats: Dict[str, Any] = field(default_factory=dict)
    cache_stats: Dict[str, Any] = field(default_factory=dict)
    
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "model_name": self.model_name,
            "total_messages": self.total_messages,
            "total_tokens": self.total_tokens,
            "hot_tokens": self.hot_tokens,
            "warm_tokens": self.warm_tokens,
            "cold_tokens": self.cold_tokens,
            "calculation_method": self.calculation_method,
            "calculation_accuracy": self.calculation_accuracy,
            "compression_stats": self.compression_stats,
            "cache_stats": self.cache_stats,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class SessionTokenMetadata:
    """会话 Token 元数据"""
    session_id: str
    user_id: str
    model_name: str
    
    token_budget: Dict[str, Any] = field(default_factory=dict)
    tier_config: Dict[str, Any] = field(default_factory=dict)
    compression_stats: Dict[str, Any] = field(default_factory=dict)
    cache_stats: Dict[str, Any] = field(default_factory=dict)
    
    created_at: str = ""
    updated_at: str = ""
    last_compression: str = ""
    
    def to_frontmatter(self) -> str:
        """转换为 YAML frontmatter"""
        import yaml
        
        data = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "model_name": self.model_name,
            "token_budget": self.token_budget,
            "tier_config": self.tier_config,
            "compression_stats": self.compression_stats,
            "cache_stats": self.cache_stats,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_compression": self.last_compression
        }
        
        return yaml.dump(data, allow_unicode=True, default_flow_style=False)


MODEL_CONFIGS = {
    "gpt-4": {
        "tokenizer": CalculationMethod.TIKTOKEN.value,
        "encoding": "cl100k_base",
        "context_window": 8192,
        "calculation_method": CalculationMethod.TIKTOKEN.value
    },
    "gpt-4-turbo": {
        "tokenizer": CalculationMethod.TIKTOKEN.value,
        "encoding": "cl100k_base",
        "context_window": 128000,
        "calculation_method": CalculationMethod.TIKTOKEN.value
    },
    "gpt-3.5-turbo": {
        "tokenizer": CalculationMethod.TIKTOKEN.value,
        "encoding": "cl100k_base",
        "context_window": 16384,
        "calculation_method": CalculationMethod.TIKTOKEN.value
    },
    "glm-4": {
        "tokenizer": "glm",
        "context_window": 128000,
        "calculation_method": CalculationMethod.API_OR_ESTIMATE.value,
        "conservative_ratio": 1.2
    },
    "glm-4-plus": {
        "tokenizer": "glm",
        "context_window": 128000,
        "calculation_method": CalculationMethod.API_OR_ESTIMATE.value,
        "conservative_ratio": 1.2
    },
    "glm-4-flash": {
        "tokenizer": "glm",
        "context_window": 128000,
        "calculation_method": CalculationMethod.API_OR_ESTIMATE.value,
        "conservative_ratio": 1.2
    },
    "qwen-turbo": {
        "tokenizer": "qwen",
        "context_window": 128000,
        "calculation_method": CalculationMethod.API_OR_ESTIMATE.value,
        "conservative_ratio": 1.15
    },
    "qwen-plus": {
        "tokenizer": "qwen",
        "context_window": 128000,
        "calculation_method": CalculationMethod.API_OR_ESTIMATE.value,
        "conservative_ratio": 1.15
    },
    "qwen-max": {
        "tokenizer": "qwen",
        "context_window": 32000,
        "calculation_method": CalculationMethod.API_OR_ESTIMATE.value,
        "conservative_ratio": 1.15
    },
    "qwen3-coder-plus": {
        "tokenizer": "qwen",
        "context_window": 128000,
        "calculation_method": CalculationMethod.API_OR_ESTIMATE.value,
        "conservative_ratio": 1.15
    },
    "deepseek-chat": {
        "tokenizer": CalculationMethod.TIKTOKEN.value,
        "encoding": "cl100k_base",
        "context_window": 32000,
        "calculation_method": CalculationMethod.TIKTOKEN.value
    },
    "deepseek-coder": {
        "tokenizer": CalculationMethod.TIKTOKEN.value,
        "encoding": "cl100k_base",
        "context_window": 16384,
        "calculation_method": CalculationMethod.TIKTOKEN.value
    },
    "claude-3-opus": {
        "tokenizer": "claude",
        "context_window": 200000,
        "calculation_method": CalculationMethod.API_OR_ESTIMATE.value,
        "conservative_ratio": 1.2
    },
    "claude-3-sonnet": {
        "tokenizer": "claude",
        "context_window": 200000,
        "calculation_method": CalculationMethod.API_OR_ESTIMATE.value,
        "conservative_ratio": 1.2
    }
}


def get_model_config(model_name: str) -> Dict[str, Any]:
    """获取模型配置（精确匹配 > 前缀匹配 > 包含匹配 > 兜底）"""
    normalized = model_name.lower()

    if normalized in MODEL_CONFIGS:
        return MODEL_CONFIGS[normalized]

    matches = [(k, v) for k, v in MODEL_CONFIGS.items() if normalized.startswith(k)]
    if matches:
        return max(matches, key=lambda x: len(x[0]))[1]

    for key, config in MODEL_CONFIGS.items():
        if key in normalized:
            return config

    return {
        "tokenizer": "unknown",
        "context_window": 8192,
        "calculation_method": CalculationMethod.ESTIMATE.value,
        "conservative_ratio": 1.3
    }