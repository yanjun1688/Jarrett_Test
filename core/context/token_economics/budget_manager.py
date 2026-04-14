"""
Token 预算管理器

管理 Token 预算，提供预算状态检查和建议。

Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md
"""

from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BudgetStatusType(Enum):
    """预算状态类型"""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


@dataclass
class BudgetStatus:
    """
    Token 预算状态
    
    Attributes:
        total_budget: 总预算
        used_tokens: 已使用 Token
        available_tokens: 可用 Token
        utilization: 利用率 (0.0 - 1.0)
        status: 状态类型
        recommendations: 建议列表
        tier_breakdown: 各层 Token 占用
    """
    total_budget: int
    used_tokens: int
    available_tokens: int
    utilization: float
    status: BudgetStatusType
    recommendations: List[str] = field(default_factory=list)
    tier_breakdown: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "total_budget": self.total_budget,
            "used_tokens": self.used_tokens,
            "available_tokens": self.available_tokens,
            "utilization": self.utilization,
            "status": self.status.value,
            "recommendations": self.recommendations,
            "tier_breakdown": self.tier_breakdown,
        }


@dataclass
class BudgetConfig:
    """预算配置"""
    total_limit: int = 8192
    output_reserve: int = 2048
    safety_buffer: int = 512
    soft_limit_ratio: float = 0.8
    
    @property
    def effective_budget(self) -> int:
        """有效预算（扣除预留）"""
        return self.total_limit - self.output_reserve - self.safety_buffer


class TokenBudgetManager:
    """
    Token 预算管理器
    
    管理对话上下文的 Token 预算，提供状态检查和建议。
    
    使用示例：
        config = BudgetConfig(total_limit=8192)
        manager = TokenBudgetManager("gpt-4", config)
        status = manager.check_budget(current_tokens=5000)
    
    Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md
    """
    
    DEFAULT_CONFIGS = {
        "gpt-4": BudgetConfig(total_limit=8192, output_reserve=2048, safety_buffer=512),
        "gpt-4-turbo": BudgetConfig(total_limit=128000, output_reserve=8192, safety_buffer=1024),
        "gpt-3.5-turbo": BudgetConfig(total_limit=16384, output_reserve=4096, safety_buffer=512),
        "glm-4": BudgetConfig(total_limit=128000, output_reserve=8192, safety_buffer=1024),
        "glm-4-plus": BudgetConfig(total_limit=128000, output_reserve=8192, safety_buffer=1024),
        "glm-4-flash": BudgetConfig(total_limit=128000, output_reserve=4096, safety_buffer=512),
        "glm-4.7-flash": BudgetConfig(total_limit=8192, output_reserve=2048, safety_buffer=256),
        "glm-5": BudgetConfig(total_limit=4096, output_reserve=1024, safety_buffer=128),
        "qwen-plus": BudgetConfig(total_limit=128000, output_reserve=8192, safety_buffer=1024),
    }
    
    def __init__(self, model_name: str, config: Optional[BudgetConfig] = None):
        """
        初始化预算管理器
        
        Args:
            model_name: 模型名称
            config: 预算配置（可选）
        """
        self.model_name = model_name.lower()
        
        if config is None:
            config = self._get_default_config(self.model_name)
        
        self.config = config
        self.total_budget = config.effective_budget
    
    def _get_default_config(self, model_name: str) -> BudgetConfig:
        """获取模型的默认配置"""
        for key, config in self.DEFAULT_CONFIGS.items():
            if key in model_name or model_name in key:
                return config
        
        return BudgetConfig()
    
    def check_budget(self, current_tokens: int) -> BudgetStatus:
        """
        检查预算状态
        
        Args:
            current_tokens: 当前使用的 Token 数
            
        Returns:
            预算状态
        """
        utilization = current_tokens / self.total_budget if self.total_budget > 0 else 0
        available = max(0, self.total_budget - current_tokens)
        
        if utilization > 1.0:
            status = BudgetStatusType.EXCEEDED
            recommendations = [
                "立即触发强制压缩",
                "截断早期消息",
                "考虑开启新会话"
            ]
        elif utilization > 0.95:
            status = BudgetStatusType.CRITICAL
            recommendations = [
                "触发紧急压缩",
                "建议用户开启新会话"
            ]
        elif utilization > self.config.soft_limit_ratio:
            status = BudgetStatusType.WARNING
            recommendations = [
                "触发常规压缩",
                "监控 Token 使用"
            ]
        else:
            status = BudgetStatusType.OK
            recommendations = []
        
        return BudgetStatus(
            total_budget=self.total_budget,
            used_tokens=current_tokens,
            available_tokens=available,
            utilization=utilization,
            status=status,
            recommendations=recommendations,
        )
    
    def get_budget_for_tier(
        self,
        hot_zone_size: int = 10,
        warm_zone_size: int = 40
    ) -> dict:
        """
        获取各层的预算分配
        
        Args:
            hot_zone_size: 热区消息数
            warm_zone_size: 温区消息数
            
        Returns:
            各层预算配置
        """
        hot_ratio = 0.6
        warm_ratio = 0.3
        cold_ratio = 0.1
        
        return {
            "hot_zone_budget": int(self.total_budget * hot_ratio),
            "warm_zone_budget": int(self.total_budget * warm_ratio),
            "cold_zone_budget": int(self.total_budget * cold_ratio),
            "hot_zone_size": hot_zone_size,
            "warm_zone_size": warm_zone_size,
        }