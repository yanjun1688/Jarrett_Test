"""
Token 经济学上下文存储

继承自 MarkdownContextStore，增加 Token 预算管理和分层压缩功能。

核心接口：
- get_messages_for_llm(): 获取优化后的消息列表
- check_budget(): 检查 Token 预算状态

Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from core.context.markdown_store import MarkdownContextStore
from .token_calculator import TokenCalculator
from .budget_manager import TokenBudgetManager, BudgetStatus, BudgetConfig

logger = logging.getLogger(__name__)


class TokenEconomicsContextStore(MarkdownContextStore):
    """
    Token 经济学上下文存储
    
    继承 MarkdownContextStore，增加：
    1. Token 精确计算
    2. 预算管理
    3. 分层上下文（热/温/冷区）
    4. 智能压缩
    
    接口约定（对齐 PromptBuilder）：
    - get_messages_for_llm() -> optimized_history
    - check_budget() -> BudgetStatus
    
    Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md
    """
    
    DEFAULT_HOT_ZONE_SIZE = 10
    DEFAULT_WARM_ZONE_SIZE = 40
    
    def __init__(
        self,
        root_dir: Path,
        model_name: str = "gpt-4",
        budget_config: Optional[BudgetConfig] = None
    ):
        """
        初始化 Token 经济学上下文存储
        
        Args:
            root_dir: 存储根目录
            model_name: 模型名称
            budget_config: 预算配置
        """
        super().__init__(root_dir)
        
        self.model_name = model_name
        self.token_calc = TokenCalculator(model_name)
        self.budget_manager = TokenBudgetManager(model_name, budget_config)
        
        # 摘要缓存: {session_id: {"warm": (hash, summary), "cold": (hash, summary)}}
        self._summary_cache: Dict[str, Dict[str, Any]] = {}
        # 缓存统计
        self._cache_stats = {
            "warm_hits": 0,
            "warm_misses": 0,
            "cold_hits": 0,
            "cold_misses": 0,
        }
        
        logger.info(f"TokenEconomicsContextStore initialized for {model_name}")
    
    def get_messages_for_llm(
        self,
        session_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取用于 LLM 的消息列表（优化后）
        
        实现三层管理：
        - 热区: 最近 N 条完整消息
        - 温区: 结构化摘要
        - 冷区: 语义摘要
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            
        Returns:
            优化后的消息列表，格式：
            [
                {"role": "user", "content": "...", "zone": "hot"},
                {"role": "assistant", "content": "...", "zone": "hot"},
                {"zone": "warm_summary", "content": "温区摘要"},
                {"zone": "cold_summary", "content": "冷区摘要"}
            ]
        """
        logger.info(f"[ContextStore] ========== get_messages_for_llm ==========")
        logger.info(f"[ContextStore] Session: {session_id}, User: {user_id}")
        
        context = self.get_context(session_id, user_id)
        
        if not context:
            logger.info(f"[ContextStore] 上下文不存在，返回空列表")
            return []
        
        messages = context.get("messages", [])
        
        if not messages:
            logger.info(f"[ContextStore] 无消息历史，返回空列表")
            return []
        
        logger.info(f"[ContextStore] 原始消息数: {len(messages)}")
        
        hot_zone_size = self.DEFAULT_HOT_ZONE_SIZE
        warm_zone_size = self.DEFAULT_WARM_ZONE_SIZE
        
        result = []
        total_messages = len(messages)
        
        if total_messages <= hot_zone_size:
            logger.info(f"[ContextStore] 消息数<{hot_zone_size}，全部进入热区")
            for msg in messages:
                result.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "zone": "hot"
                })
        else:
            logger.info(f"[ContextStore] 消息数>{hot_zone_size}，启动三层管理")
            logger.info(f"[ContextStore] 热区={hot_zone_size}, 温区={warm_zone_size}")
            
            hot_messages = messages[-hot_zone_size:]
            for msg in hot_messages:
                result.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "zone": "hot"
                })
            logger.info(f"[ContextStore] 热区消息: {len(hot_messages)}条")
            
            remaining = total_messages - hot_zone_size
            
            if remaining > warm_zone_size:
                warm_start = total_messages - hot_zone_size - warm_zone_size
                warm_messages = messages[warm_start:-hot_zone_size]
                
                if warm_messages:
                    warm_summary = self._generate_warm_summary(warm_messages, session_id)
                    result.append({
                        "zone": "warm_summary",
                        "content": warm_summary
                    })
                logger.info(f"[ContextStore] 温区摘要: {len(warm_messages)}条 -> 1条摘要")
                
                cold_messages = messages[:warm_start]
                if cold_messages:
                    cold_summary = self._generate_cold_summary(cold_messages, session_id)
                    result.append({
                        "zone": "cold_summary",
                        "content": cold_summary
                    })
                logger.info(f"[ContextStore] 冷区摘要: {len(cold_messages)}条 -> 1条摘要")
            else:
                warm_messages = messages[:-hot_zone_size]
                if warm_messages:
                    warm_summary = self._generate_warm_summary(warm_messages, session_id)
                    result.append({
                        "zone": "warm_summary",
                        "content": warm_summary
                    })
                logger.info(f"[ContextStore] 温区摘要: {len(warm_messages)}条 -> 1条摘要")
        
        logger.info(f"[ContextStore] 返回优化消息: {len(result)}条")
        logger.info(f"[ContextStore] ========== get_messages_for_llm 完成 ==========")
        
        return result
    
    def check_budget(
        self,
        session_id: str,
        user_id: str
    ) -> BudgetStatus:
        """
        检查 Token 预算状态
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            
        Returns:
            BudgetStatus 包含：
            - total_budget: 总预算
            - used_tokens: 已使用
            - available_tokens: 可用
            - utilization: 利用率
            - status: 状态
            - recommendations: 建议
            - tier_breakdown: 各层占用
        """
        logger.info(f"[ContextStore] ========== check_budget ==========")
        context = self.get_context(session_id, user_id)
        
        if not context:
            logger.info(f"[ContextStore] 上下文不存在，返回初始预算状态")
            return self.budget_manager.check_budget(0)
        
        messages = context.get("messages", [])
        total_tokens = self.token_calc.count_messages_tokens(messages)
        logger.info(f"[ContextStore] 总Token数: {total_tokens}")
        
        status = self.budget_manager.check_budget(total_tokens)
        
        hot_tokens = 0
        warm_tokens = 0
        cold_tokens = 0
        
        hot_zone_size = self.DEFAULT_HOT_ZONE_SIZE
        warm_zone_size = self.DEFAULT_WARM_ZONE_SIZE
        total_messages = len(messages)
        
        if total_messages <= hot_zone_size:
            hot_tokens = total_tokens
        else:
            hot_messages = messages[-hot_zone_size:]
            hot_tokens = self.token_calc.count_messages_tokens(hot_messages)
            
            remaining = total_messages - hot_zone_size
            
            if remaining > warm_zone_size:
                warm_start = total_messages - hot_zone_size - warm_zone_size
                warm_messages = messages[warm_start:-hot_zone_size]
                cold_messages = messages[:warm_start]
                
                warm_tokens = self.token_calc.count_messages_tokens(warm_messages)
                cold_tokens = self.token_calc.count_messages_tokens(cold_messages)
            else:
                warm_messages = messages[:-hot_zone_size]
                warm_tokens = self.token_calc.count_messages_tokens(warm_messages)
        
        status.tier_breakdown = {
            "hot": hot_tokens,
            "warm": warm_tokens,
            "cold": cold_tokens,
            "hot_count": min(total_messages, hot_zone_size),
            "warm_count": max(0, min(total_messages - hot_zone_size, warm_zone_size)),
            "cold_count": max(0, total_messages - hot_zone_size - warm_zone_size),
        }
        
        logger.info(f"[ContextStore] 分层Token: hot={hot_tokens}, warm={warm_tokens}, cold={cold_tokens}")
        logger.info(f"[ContextStore] 分层消息数: hot={status.tier_breakdown['hot_count']}, warm={status.tier_breakdown['warm_count']}, cold={status.tier_breakdown['cold_count']}")
        logger.info(f"[ContextStore] 预算状态: {status.status.value}, 利用率={status.utilization:.2%}")
        logger.info(f"[ContextStore] ========== check_budget 完成 ==========")
        
        return status
    
    def get_token_statistics(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        获取 Token 使用统计
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            
        Returns:
            Token 统计信息
        """
        context = self.get_context(session_id, user_id)
        
        if not context:
            return {
                "total_tokens": 0,
                "message_count": 0,
                "model": self.model_name,
                "context_window": self.token_calc.get_context_window(),
            }
        
        messages = context.get("messages", [])
        total_tokens = self.token_calc.count_messages_tokens(messages)
        
        return {
            "total_tokens": total_tokens,
            "message_count": len(messages),
            "model": self.model_name,
            "context_window": self.token_calc.get_context_window(),
            "calculation_method": self.token_calc.get_calculation_method(),
            "is_precise": self.token_calc.is_precise(),
        }
    
    def append_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        追加消息（带 Token 计算）
        
        如果会话不存在，自动创建会话。
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            role: 角色
            content: 内容
            metadata: 元数据
            
        Returns:
            是否成功
        """
        filepath = self._get_path(user_id, session_id)
        if not filepath.exists():
            self.create_session(session_id=session_id, user_id=user_id)
        
        token_count = self.token_calc.count_tokens(content)
        
        msg_metadata = metadata or {}
        msg_metadata["token_count"] = token_count
        
        return super().append_message(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            metadata=msg_metadata
        )
    
    def _generate_warm_summary(
        self,
        messages: List[Dict[str, Any]],
        session_id: str = ""
    ) -> str:
        """
        生成温区结构化摘要（增量缓存）
        
        缓存策略：记录上次处理过的消息数量，只对新增消息做增量提取，
        然后合并到已有摘要中。这样即使温区边界每次移动2条，
        也只需处理新增部分，之前的摘要直接复用。
        
        Args:
            messages: 温区消息列表
            session_id: 会话ID，用于缓存键
            
        Returns:
            摘要文本
        """
        if not messages:
            return ""
        
        session_cache = self._summary_cache.get(session_id, {})
        cached = session_cache.get("warm")
        
        # cached 格式: (processed_count, first_content_hash, topics, entities, first_msg, last_msg)
        # first_content_hash 用于检测温区头部是否发生了变化（冷区出现导致头部被截掉）
        first_hash = hashlib.sha256(
            messages[0].get("content", "")[:200].encode("utf-8")
        ).hexdigest()[:12]
        
        if cached and cached[1] == first_hash and cached[0] <= len(messages):  # type: ignore[operator,index]
            # 头部没变，只是尾部新增了消息 -> 增量处理
            prev_count = cached[0]  # type: ignore[index]
            topics = set(cached[2])  # type: ignore[index]
            entities = set(cached[3])  # type: ignore[index]
            
            if prev_count == len(messages):
                # 完全没变，直接命中
                self._cache_stats["warm_hits"] += 1
                total = self._cache_stats["warm_hits"] + self._cache_stats["warm_misses"]
                hit_rate = self._cache_stats["warm_hits"] / total if total > 0 else 0
                summary = self._format_warm_summary(topics, entities, messages)
                logger.info(
                    f"[ContextStore] [CACHE HIT] 温区摘要完全命中 "
                    f"(count={len(messages)}, hits={self._cache_stats['warm_hits']}, "
                    f"misses={self._cache_stats['warm_misses']}, hit_rate={hit_rate:.1%})"
                )
                return summary
            
            # 增量处理新增的消息
            new_messages = messages[prev_count:]
            self._extract_warm_features(new_messages, topics, entities)
            
            self._cache_stats["warm_hits"] += 1
            total = self._cache_stats["warm_hits"] + self._cache_stats["warm_misses"]
            hit_rate = self._cache_stats["warm_hits"] / total if total > 0 else 0
            logger.info(
                f"[ContextStore] [CACHE HIT] 温区摘要增量命中 "
                f"(cached={prev_count}, new={len(new_messages)}, total={len(messages)}, "
                f"hits={self._cache_stats['warm_hits']}, misses={self._cache_stats['warm_misses']}, "
                f"hit_rate={hit_rate:.1%})"
            )
        else:
            # 头部变了或首次生成 -> 全量处理
            topics = set()
            entities = set()
            self._extract_warm_features(messages, topics, entities)
            
            self._cache_stats["warm_misses"] += 1
            total = self._cache_stats["warm_hits"] + self._cache_stats["warm_misses"]
            hit_rate = self._cache_stats["warm_hits"] / total if total > 0 else 0
            reason = "首次生成" if not cached else "头部变化(冷区扩展)"
            logger.info(
                f"[ContextStore] [CACHE MISS] 温区摘要未命中({reason})，全量生成 "
                f"(count={len(messages)}, hits={self._cache_stats['warm_hits']}, "
                f"misses={self._cache_stats['warm_misses']}, hit_rate={hit_rate:.1%})"
            )
        
        summary = self._format_warm_summary(topics, entities, messages)
        
        # 写入缓存
        if session_id:
            if session_id not in self._summary_cache:
                self._summary_cache[session_id] = {}
            self._summary_cache[session_id]["warm"] = (
                len(messages), first_hash,
                list(topics), list(entities),
                None, None  # 保留位，兼容
            )
        
        return summary
    
    def _extract_warm_features(
        self,
        messages: List[Dict[str, Any]],
        topics: set,
        entities: set
    ):
        """从消息中提取温区特征（topics, entities）"""
        import re
        for msg in messages:
            content = msg.get("content", "")
            code_blocks = re.findall(r'```(\w+)', content)
            topics.update(code_blocks)
            urls = re.findall(r'https?://[^\s]+', content)
            entities.update(urls)
    
    def _format_warm_summary(
        self,
        topics: set,
        entities: set,
        messages: List[Dict[str, Any]]
    ) -> str:
        """格式化温区摘要文本"""
        lines = [f"共 {len(messages)} 条历史消息"]
        
        if topics:
            lines.append(f"涉及技术: {', '.join(sorted(topics)[:5])}")
        if entities:
            lines.append(f"相关资源: {', '.join(list(entities)[:3])}")
        
        first_msg = messages[0].get("content", "")[:100]
        last_msg = messages[-1].get("content", "")[:100]
        
        if len(messages) > 1:
            lines.append(f"起始: {first_msg}...")
            lines.append(f"结束: {last_msg}...")
        else:
            lines.append(f"内容: {first_msg}...")
        
        return "\n".join(lines)
    
    def _generate_cold_summary(
        self,
        messages: List[Dict[str, Any]],
        session_id: str = ""
    ) -> str:
        """
        生成冷区语义摘要（增量缓存）
        
        冷区只在消息数超过 hot+warm 时才出现，且冷区头部固定（从最早的消息开始），
        只有尾部会增长。用增量策略：记录已处理数量，新增部分直接合并统计。
        
        Args:
            messages: 冷区消息列表
            session_id: 会话ID，用于缓存键
            
        Returns:
            摘要文本
        """
        if not messages:
            return ""
        
        session_cache = self._summary_cache.get(session_id, {})
        cached = session_cache.get("cold")
        
        # cached 格式: (processed_count, user_count, assistant_count, first_user_content)
        if cached and cached[0] <= len(messages):  # type: ignore[operator]
            prev_count = cached[0]  # type: ignore[index]
            
            if prev_count == len(messages):
                # 完全没变
                self._cache_stats["cold_hits"] += 1
                total = self._cache_stats["cold_hits"] + self._cache_stats["cold_misses"]
                hit_rate = self._cache_stats["cold_hits"] / total if total > 0 else 0
                summary = self._format_cold_summary(
                    len(messages), cached[1], cached[2], cached[3]  # type: ignore[arg-type,index]
                )
                logger.info(
                    f"[ContextStore] [CACHE HIT] 冷区摘要完全命中 "
                    f"(count={len(messages)}, hits={self._cache_stats['cold_hits']}, "
                    f"misses={self._cache_stats['cold_misses']}, hit_rate={hit_rate:.1%})"
                )
                return summary
            
            # 增量：只统计新增消息
            new_messages = messages[prev_count:]
            new_user = sum(1 for m in new_messages if m.get("role") == "user")
            new_assistant = sum(1 for m in new_messages if m.get("role") == "assistant")
            
            user_count = cached[1] + new_user  # type: ignore[operator,index]
            assistant_count = cached[2] + new_assistant  # type: ignore[operator,index]
            first_user_content = cached[3]  # type: ignore[index]
            
            self._cache_stats["cold_hits"] += 1
            total = self._cache_stats["cold_hits"] + self._cache_stats["cold_misses"]
            hit_rate = self._cache_stats["cold_hits"] / total if total > 0 else 0
            logger.info(
                f"[ContextStore] [CACHE HIT] 冷区摘要增量命中 "
                f"(cached={prev_count}, new={len(new_messages)}, total={len(messages)}, "
                f"hits={self._cache_stats['cold_hits']}, misses={self._cache_stats['cold_misses']}, "
                f"hit_rate={hit_rate:.1%})"
            )
        else:
            # 全量处理
            user_count = sum(1 for m in messages if m.get("role") == "user")
            assistant_count = sum(1 for m in messages if m.get("role") == "assistant")
            user_msgs = [m for m in messages if m.get("role") == "user"]
            first_user_content = user_msgs[0].get("content", "")[:80] if user_msgs else ""
            
            self._cache_stats["cold_misses"] += 1
            total = self._cache_stats["cold_hits"] + self._cache_stats["cold_misses"]
            hit_rate = self._cache_stats["cold_hits"] / total if total > 0 else 0
            logger.info(
                f"[ContextStore] [CACHE MISS] 冷区摘要未命中，全量生成 "
                f"(count={len(messages)}, hits={self._cache_stats['cold_hits']}, "
                f"misses={self._cache_stats['cold_misses']}, hit_rate={hit_rate:.1%})"
            )
        
        summary = self._format_cold_summary(
            len(messages), user_count, assistant_count, first_user_content
        )
        
        # 写入缓存
        if session_id:
            if session_id not in self._summary_cache:
                self._summary_cache[session_id] = {}
            self._summary_cache[session_id]["cold"] = (
                len(messages), user_count, assistant_count, first_user_content
            )
        
        return summary
    
    def _format_cold_summary(
        self,
        total_count: int,
        user_count: int,
        assistant_count: int,
        first_user_content: str
    ) -> str:
        """格式化冷区摘要文本"""
        lines = [
            f"早期对话: {total_count} 条消息",
            f"用户提问 {user_count} 次",
            f"助手回复 {assistant_count} 次",
        ]
        if first_user_content:
            lines.append(f"首个问题: {first_user_content}...")
        return " | ".join(lines)
    
    def _compute_messages_hash(self, messages: List[Dict[str, Any]]) -> str:
        """
        计算消息列表的哈希值，用于缓存键
        
        基于消息数量 + 首尾消息内容生成哈希，
        避免对全部消息做完整哈希的开销。
        """
        parts = [str(len(messages))]
        if messages:
            first = messages[0].get("content", "")[:200]
            last = messages[-1].get("content", "")[:200]
            parts.append(first)
            parts.append(last)
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取摘要缓存统计"""
        warm_total = self._cache_stats["warm_hits"] + self._cache_stats["warm_misses"]
        cold_total = self._cache_stats["cold_hits"] + self._cache_stats["cold_misses"]
        return {
            "warm_hits": self._cache_stats["warm_hits"],
            "warm_misses": self._cache_stats["warm_misses"],
            "warm_hit_rate": (self._cache_stats["warm_hits"] / warm_total) if warm_total > 0 else 0,
            "cold_hits": self._cache_stats["cold_hits"],
            "cold_misses": self._cache_stats["cold_misses"],
            "cold_hit_rate": (self._cache_stats["cold_hits"] / cold_total) if cold_total > 0 else 0,
            "cached_sessions": len(self._summary_cache),
        }