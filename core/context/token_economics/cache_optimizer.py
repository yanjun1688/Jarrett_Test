"""
缓存优化器

实现 API 层 Prompt 缓存优化。

功能：
- 静态前缀分离
- 缓存边界标记
- 缓存命中率监控
- 前缀哈希验证

缓存边界约定：
- 由 PromptBuilder 统一管理
- 本系统提供辅助方法

Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md 机制6
"""

import hashlib
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """缓存统计"""
    prefix_hash: str = ""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    estimated_savings_tokens: int = 0
    estimated_savings_usd: float = 0.0
    last_hit_time: str = ""
    
    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prefix_hash": self.prefix_hash,
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": round(self.hit_rate, 3),
            "estimated_savings_tokens": self.estimated_savings_tokens,
            "estimated_savings_usd": round(self.estimated_savings_usd, 4),
            "last_hit_time": self.last_hit_time
        }


@dataclass
class CacheConfig:
    """缓存配置"""
    enable_caching: bool = True
    static_prefix_max_tokens: int = 4096
    min_prefix_tokens_for_cache: int = 1024
    pricing_per_million_tokens: float = 30.0


class CacheOptimizer:
    """
    缓存优化器
    
    功能：
    1. 静态前缀管理
    2. 缓存边界设计
    3. 缓存命中率监控
    4. 成本节省估算
    
    缓存边界约定（对齐 PromptBuilder）：
    - 边界标记由 PromptBuilder 统一管理
    - 本系统提供辅助方法
    
    使用示例：
        optimizer = CacheOptimizer(static_prefix="你是测试助手...")
        friendly_prompt = optimizer.build_cache_friendly_prompt(dynamic_context)
    """
    
    CACHE_BOUNDARY_MARKER = "<!-- CACHE_BOUNDARY -->"
    
    def __init__(
        self,
        static_prefix: str = "",
        config: Optional[CacheConfig] = None
    ):
        """
        初始化缓存优化器
        
        Args:
            static_prefix: 静态前缀内容
            config: 缓存配置
        """
        self.static_prefix = static_prefix
        self.config = config or CacheConfig()
        self.prefix_hash = self._calculate_hash(static_prefix) if static_prefix else ""
        self.stats = CacheStats(prefix_hash=self.prefix_hash)
    
    def _calculate_hash(self, text: str) -> str:
        """计算文本哈希"""
        if not text:
            return ""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def set_static_prefix(self, prefix: str):
        """设置静态前缀"""
        self.static_prefix = prefix
        self.prefix_hash = self._calculate_hash(prefix)
        self.stats.prefix_hash = self.prefix_hash
        logger.debug(f"Updated static prefix, hash: {self.prefix_hash}")
    
    def build_cache_friendly_prompt(
        self,
        dynamic_context: str,
        include_boundary: bool = True
    ) -> str:
        """
        构建缓存友好的 Prompt
        
        结构：
        [静态前缀] - 可缓存
        [边界标记]
        [动态内容] - 不缓存
        
        Args:
            dynamic_context: 动态上下文
            include_boundary: 是否包含边界标记
            
        Returns:
            完整的 Prompt
        """
        if not self.static_prefix:
            return dynamic_context
        
        if include_boundary:
            return (
                self.static_prefix + 
                "\n\n" + 
                self.CACHE_BOUNDARY_MARKER + 
                "\n\n" + 
                dynamic_context
            )
        else:
            return self.static_prefix + "\n\n" + dynamic_context
    
    def record_cache_hit(
        self,
        tokens_saved: int,
        is_hit: bool
    ):
        """
        记录缓存命中情况
        
        Args:
            tokens_saved: 节省的 Token 数
            is_hit: 是否命中缓存
        """
        self.stats.total_requests += 1
        
        if is_hit:
            self.stats.cache_hits += 1
            self.stats.estimated_savings_tokens += tokens_saved
            self.stats.last_hit_time = datetime.now().isoformat()
            
            savings = (tokens_saved / 1_000_000) * self.config.pricing_per_million_tokens
            self.stats.estimated_savings_usd += savings
        else:
            self.stats.cache_misses += 1
    
    def get_cache_stats(self) -> CacheStats:
        """获取缓存统计"""
        return self.stats
    
    def validate_prefix_consistency(
        self,
        other_prefix: str
    ) -> bool:
        """
        验证前缀一致性
        
        Args:
            other_prefix: 要比较的前缀
            
        Returns:
            是否一致
        """
        other_hash = self._calculate_hash(other_prefix)
        return other_hash == self.prefix_hash
    
    def estimate_cache_benefit(
        self,
        static_tokens: int,
        requests_per_day: int = 100
    ) -> Dict[str, Any]:
        """
        估算缓存收益
        
        Args:
            static_tokens: 静态部分的 Token 数
            requests_per_day: 每日请求数
            
        Returns:
            收益估算
        """
        hit_rate = self.stats.hit_rate if self.stats.total_requests > 0 else 0.8
        
        daily_savings_tokens = static_tokens * requests_per_day * hit_rate
        daily_savings_usd = (daily_savings_tokens / 1_000_000) * self.config.pricing_per_million_tokens
        
        return {
            "static_tokens": static_tokens,
            "estimated_hit_rate": hit_rate,
            "daily_savings_tokens": int(daily_savings_tokens),
            "daily_savings_usd": round(daily_savings_usd, 4),
            "monthly_savings_usd": round(daily_savings_usd * 30, 2),
            "requests_per_day": requests_per_day
        }
    
    def optimize_static_prefix(
        self,
        full_prefix: str,
        max_tokens: int = None,
        token_calculator=None
    ) -> str:
        """
        优化静态前缀（截断到合适大小）
        
        Args:
            full_prefix: 完整前缀
            max_tokens: 最大 Token 数
            token_calculator: Token 计算器
            
        Returns:
            优化后的前缀
        """
        max_tokens = max_tokens or self.config.static_prefix_max_tokens
        
        if not token_calculator:
            return full_prefix
        
        current_tokens = token_calculator.count_tokens(full_prefix)
        
        if current_tokens <= max_tokens:
            return full_prefix
        
        lines = full_prefix.split('\n')
        optimized_lines = []
        current_tokens = 0
        
        for line in lines:
            line_tokens = token_calculator.count_tokens(line + '\n')
            if current_tokens + line_tokens > max_tokens:
                break
            optimized_lines.append(line)
            current_tokens += line_tokens
        
        return '\n'.join(optimized_lines)
    
    def should_enable_caching(
        self,
        static_tokens: int
    ) -> bool:
        """
        判断是否应该启用缓存
        
        Args:
            static_tokens: 静态部分的 Token 数
            
        Returns:
            是否启用缓存
        """
        if not self.config.enable_caching:
            return False
        
        return static_tokens >= self.config.min_prefix_tokens_for_cache
    
    def reset_stats(self):
        """重置统计"""
        self.stats = CacheStats(prefix_hash=self.prefix_hash)
        logger.info("Cache stats reset")


class CacheFriendlyPromptBuilder:
    """
    缓存友好的 Prompt 构建器
    
    辅助类，用于构建符合缓存要求的 Prompt
    """
    
    def __init__(
        self,
        cache_optimizer: CacheOptimizer,
        token_calculator=None
    ):
        self.cache_optimizer = cache_optimizer
        self.token_calculator = token_calculator
    
    def build(
        self,
        static_sections: List[str],
        dynamic_sections: List[str]
    ) -> Dict[str, Any]:
        """
        构建 Prompt
        
        Args:
            static_sections: 静态部分列表
            dynamic_sections: 动态部分列表
            
        Returns:
            {
                "full_prompt": str,
                "static_part": str,
                "dynamic_part": str,
                "static_tokens": int,
                "dynamic_tokens": int,
                "total_tokens": int,
                "cache_recommended": bool
            }
        """
        static_part = "\n\n".join(static_sections)
        dynamic_part = "\n\n".join(dynamic_sections)
        
        self.cache_optimizer.set_static_prefix(static_part)
        
        full_prompt = self.cache_optimizer.build_cache_friendly_prompt(dynamic_part)
        
        static_tokens = 0
        dynamic_tokens = 0
        
        if self.token_calculator:
            static_tokens = self.token_calculator.count_tokens(static_part)
            dynamic_tokens = self.token_calculator.count_tokens(dynamic_part)
        
        total_tokens = static_tokens + dynamic_tokens
        cache_recommended = self.cache_optimizer.should_enable_caching(static_tokens)
        
        return {
            "full_prompt": full_prompt,
            "static_part": static_part,
            "dynamic_part": dynamic_part,
            "static_tokens": static_tokens,
            "dynamic_tokens": dynamic_tokens,
            "total_tokens": total_tokens,
            "cache_recommended": cache_recommended,
            "prefix_hash": self.cache_optimizer.prefix_hash
        }