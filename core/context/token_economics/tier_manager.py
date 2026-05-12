"""
三层上下文管理器

实现热/温/冷三层上下文管理策略。

层级定义：
- 热区 (Hot Zone): 最近 N 条完整消息，Token占比 60%
- 温区 (Warm Zone): 结构化摘要，Token占比 30%
- 冷区 (Cold Zone): 语义摘要，Token占比 10%

功能：
- 自动层级升降"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from .base import (
    TierConfig,
    ZoneType,
)

logger = logging.getLogger(__name__)


@dataclass
class ZoneInfo:
    """区域信息"""
    zone_type: ZoneType
    message_count: int
    token_count: int
    token_budget: int
    utilization: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_type": self.zone_type.value,
            "message_count": self.message_count,
            "token_count": self.token_count,
            "token_budget": self.token_budget,
            "utilization": self.utilization
        }


@dataclass
class TierState:
    """三层状态"""
    hot: Optional[ZoneInfo] = None
    warm: Optional[ZoneInfo] = None
    cold: Optional[ZoneInfo] = None
    total_tokens: int = 0
    total_budget: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hot": self.hot.to_dict() if self.hot else None,
            "warm": self.warm.to_dict() if self.warm else None,
            "cold": self.cold.to_dict() if self.cold else None,
            "total_tokens": self.total_tokens,
            "total_budget": self.total_budget
        }


class ContextTierManager:
    """
    三层上下文管理器
    
    功能：
    1. 管理热/温/冷三层
    2. 自动层级升降
    3. Token 预算分配
    4. 压缩触发判断
    
    使用示例：
        manager = ContextTierManager(
            total_budget=5632,
            config=TierConfig(hot_zone_size=10, warm_zone_size=40)
        )
        state = manager.calculate_tier_state(messages, token_calculator)
    """
    
    DEFAULT_HOT_RATIO = 0.6
    DEFAULT_WARM_RATIO = 0.3
    DEFAULT_COLD_RATIO = 0.1
    
    def __init__(
        self,
        total_budget: int,
        config: Optional[TierConfig] = None
    ):
        """
        初始化三层管理器
        
        Args:
            total_budget: 总 Token 预算
            config: 层级配置
        """
        self.total_budget = total_budget
        self.config = config or TierConfig()
        
        self.hot_budget = int(total_budget * self.DEFAULT_HOT_RATIO)
        self.warm_budget = int(total_budget * self.DEFAULT_WARM_RATIO)
        self.cold_budget = int(total_budget * self.DEFAULT_COLD_RATIO)
    
    def classify_messages(
        self,
        messages: List[Dict[str, Any]],
        token_calculator: Any
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        将消息分类到三个区域
        
        Args:
            messages: 消息列表
            token_calculator: Token 计算器
            
        Returns:
            (hot_messages, warm_messages, cold_messages)
        """
        total = len(messages)
        
        hot_size = self.config.hot_zone_size
        warm_size = self.config.warm_zone_size
        
        if total <= hot_size:
            return messages, [], []
        
        hot_messages = messages[-hot_size:]
        remaining = total - hot_size
        
        if remaining <= warm_size:
            warm_messages = messages[:-hot_size]
            return hot_messages, warm_messages, []
        
        warm_start = total - hot_size - warm_size
        warm_messages = messages[warm_start:-hot_size]
        cold_messages = messages[:warm_start]
        
        return hot_messages, warm_messages, cold_messages
    
    def calculate_tier_state(
        self,
        messages: List[Dict[str, Any]],
        token_calculator: Any
    ) -> TierState:
        """
        计算三层状态
        
        Args:
            messages: 消息列表
            token_calculator: Token 计算器
            
        Returns:
            TierState 对象
        """
        hot_msgs, warm_msgs, cold_msgs = self.classify_messages(
            messages, token_calculator
        )
        
        hot_tokens = token_calculator.count_messages_tokens(hot_msgs) if hot_msgs else 0
        warm_tokens = token_calculator.count_messages_tokens(warm_msgs) if warm_msgs else 0
        cold_tokens = token_calculator.count_messages_tokens(cold_msgs) if cold_msgs else 0
        
        total_tokens = hot_tokens + warm_tokens + cold_tokens
        
        hot_zone = ZoneInfo(
            zone_type=ZoneType.HOT,
            message_count=len(hot_msgs),
            token_count=hot_tokens,
            token_budget=self.hot_budget,
            utilization=hot_tokens / self.hot_budget if self.hot_budget > 0 else 0
        )
        
        warm_zone = ZoneInfo(
            zone_type=ZoneType.WARM,
            message_count=len(warm_msgs),
            token_count=warm_tokens,
            token_budget=self.warm_budget,
            utilization=warm_tokens / self.warm_budget if self.warm_budget > 0 else 0
        )
        
        cold_zone = ZoneInfo(
            zone_type=ZoneType.COLD,
            message_count=len(cold_msgs),
            token_count=cold_tokens,
            token_budget=self.cold_budget,
            utilization=cold_tokens / self.cold_budget if self.cold_budget > 0 else 0
        )
        
        return TierState(
            hot=hot_zone,
            warm=warm_zone,
            cold=cold_zone,
            total_tokens=total_tokens,
            total_budget=self.total_budget
        )
    
    def should_compress_zone(
        self,
        zone_type: ZoneType,
        token_count: int
    ) -> bool:
        """
        判断是否应该压缩某个区域
        
        Args:
            zone_type: 区域类型
            token_count: 当前 Token 数
            
        Returns:
            是否应该压缩
        """
        if zone_type == ZoneType.HOT:
            return token_count > self.hot_budget
        elif zone_type == ZoneType.WARM:
            return token_count > self.warm_budget
        else:
            return token_count > self.cold_budget
    
    def get_compression_priority(
        self,
        tier_state: TierState
    ) -> List[ZoneType]:
        """
        获取压缩优先级（从高到低）
        
        Args:
            tier_state: 三层状态
            
        Returns:
            区域类型列表（按优先级排序）
        """
        priorities = []
        
        if tier_state.cold and tier_state.cold.utilization > 1.0:
            priorities.append(ZoneType.COLD)
        
        if tier_state.warm and tier_state.warm.utilization > 1.0:
            priorities.append(ZoneType.WARM)
        
        if tier_state.hot and tier_state.hot.utilization > 1.0:
            priorities.append(ZoneType.HOT)
        
        return priorities
    
    def estimate_compression_savings(
        self,
        messages: List[Dict[str, Any]],
        zone_type: ZoneType,
        token_calculator: Any
    ) -> int:
        """
        估算压缩节省的 Token 数
        
        Args:
            messages: 要压缩的消息
            zone_type: 区域类型
            token_calculator: Token 计算器
            
        Returns:
            预计节省的 Token 数
        """
        if not messages:
            return 0
        
        original_tokens: int = token_calculator.count_messages_tokens(messages)
        
        if zone_type == ZoneType.WARM:
            estimated_summary_tokens = min(
                len(messages) * 10,
                int(original_tokens * 0.3)
            )
        elif zone_type == ZoneType.COLD:
            estimated_summary_tokens = int(original_tokens * 0.1)
        else:
            estimated_summary_tokens = int(original_tokens * 0.5)
        
        return max(0, original_tokens - estimated_summary_tokens)
    
    def get_tier_config(self) -> Dict[str, Any]:
        """获取层级配置"""
        return {
            "hot_zone_size": self.config.hot_zone_size,
            "warm_zone_size": self.config.warm_zone_size,
            "cold_zone_size": self.config.cold_zone_size,
            "hot_budget": self.hot_budget,
            "warm_budget": self.warm_budget,
            "cold_budget": self.cold_budget,
            "total_budget": self.total_budget
        }
    
    def update_budget(self, new_budget: int) -> None:
        """更新 Token 预算"""
        self.total_budget = new_budget
        self.hot_budget = int(new_budget * self.DEFAULT_HOT_RATIO)
        self.warm_budget = int(new_budget * self.DEFAULT_WARM_RATIO)
        self.cold_budget = int(new_budget * self.DEFAULT_COLD_RATIO)
        
        logger.info(f"Updated tier budgets: hot={self.hot_budget}, warm={self.warm_budget}, cold={self.cold_budget}")
    
    def get_zone_boundaries(
        self,
        total_messages: int
    ) -> Dict[str, Tuple[int, int]]:
        """
        获取各区域的边界索引
        
        Args:
            total_messages: 总消息数
            
        Returns:
            {zone_type: (start_index, end_index)}
        """
        hot_size = self.config.hot_zone_size
        warm_size = self.config.warm_zone_size
        
        if total_messages <= hot_size:
            return {
                ZoneType.HOT.value: (0, total_messages),
                ZoneType.WARM.value: (0, 0),
                ZoneType.COLD.value: (0, 0)
            }
        
        if total_messages <= hot_size + warm_size:
            return {
                ZoneType.HOT.value: (total_messages - hot_size, total_messages),
                ZoneType.WARM.value: (0, total_messages - hot_size),
                ZoneType.COLD.value: (0, 0)
            }
        
        warm_start = total_messages - hot_size - warm_size
        
        return {
            ZoneType.HOT.value: (total_messages - hot_size, total_messages),
            ZoneType.WARM.value: (warm_start, total_messages - hot_size),
            ZoneType.COLD.value: (0, warm_start)
        }