"""
Token 经济学上下文存储

继承自 MarkdownContextStore，增加 Token 预算管理和分层压缩功能。

核心接口：
- get_messages_for_llm(): 获取优化后的消息列表
- check_budget(): 检查 Token 预算状态

设计原则：
- 使用 SmartSummarizer 统一生成摘要
- 缓存机制避免重复计算
- 单一实现，避免重复代码

Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime

from core.context.markdown_store import MarkdownContextStore
from .token_calculator import TokenCalculator
from .budget_manager import TokenBudgetManager, BudgetStatus, BudgetConfig
from .smart_summarizer import SmartSummarizer, SummaryConfig, StructuredSummary

if TYPE_CHECKING:
    from core.agents.llm.base_llm import BaseLLMService

logger = logging.getLogger(__name__)


class TokenEconomicsContextStore(MarkdownContextStore):
    """
    Token 经济学上下文存储

    继承 MarkdownContextStore，增加：
    1. Token 精确计算
    2. 预算管理
    3. 分层上下文（热/温/冷区）
    4. 智能压缩（使用 SmartSummarizer）

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
        model_name: str = 'gpt-4',
        budget_config: Optional[BudgetConfig] = None,
        llm_service: Optional[BaseLLMService] = None,
        summary_config: Optional[SummaryConfig] = None
    ):
        """
        初始化 Token 经济学上下文存储

        Args:
            root_dir: 存储根目录
            model_name: 模型名称
            budget_config: 预算配置
            llm_service: LLM 服务（用于智能摘要）
            summary_config: 摘要配置
        """
        super().__init__(root_dir)

        self.model_name = model_name
        self.token_calc = TokenCalculator(model_name)
        self.budget_manager = TokenBudgetManager(model_name, budget_config)

        self.llm_service = llm_service
        self.summarizer = SmartSummarizer(
            llm_service=llm_service,
            config=summary_config
        )

        self._summary_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_stats = {
            'warm_hits': 0,
            'warm_misses': 0,
            'cold_hits': 0,
            'cold_misses': 0,
        }

        logger.info(f'TokenEconomicsContextStore initialized for {model_name}')

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
        logger.info(f'[ContextStore] ========== get_messages_for_llm ==========')
        logger.info(f'[ContextStore] Session: {session_id}, User: {user_id}')

        context = self.get_context(session_id, user_id)

        if not context:
            logger.info(f'[ContextStore] 上下文不存在，返回空列表')
            return []

        messages = context.get('messages', [])

        if not messages:
            logger.info(f'[ContextStore] 无消息历史，返回空列表')
            return []

        logger.info(f'[ContextStore] 原始消息数: {len(messages)}')

        hot_zone_size = self.DEFAULT_HOT_ZONE_SIZE
        warm_zone_size = self.DEFAULT_WARM_ZONE_SIZE

        result: List[Dict[str, Any]] = []
        total_messages = len(messages)

        if total_messages <= hot_zone_size:
            logger.info(f'[ContextStore] 消息数<{hot_zone_size}，全部进入热区')
            for msg in messages:
                result.append({
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', ''),
                    'zone': 'hot'
                })
        else:
            logger.info(f'[ContextStore] 消息数>{hot_zone_size}，启动三层管理')
            logger.info(f'[ContextStore] 热区={hot_zone_size}, 温区={warm_zone_size}')

            hot_messages = messages[-hot_zone_size:]
            for msg in hot_messages:
                result.append({
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', ''),
                    'zone': 'hot'
                })
            logger.info(f'[ContextStore] 热区消息: {len(hot_messages)}条')

            remaining = total_messages - hot_zone_size

            if remaining > warm_zone_size:
                warm_start = total_messages - hot_zone_size - warm_zone_size
                warm_messages = messages[warm_start:-hot_zone_size]

                if warm_messages:
                    warm_summary = self._get_cached_warm_summary(warm_messages, session_id)
                    warm_content = self.summarizer.format_warm_summary_for_context(
                        warm_summary, warm_messages
                    )
                    result.append({
                        'zone': 'warm_summary',
                        'content': warm_content
                    })
                logger.info(f'[ContextStore] 温区摘要: {len(warm_messages)}条 -> 1条摘要')

                cold_messages = messages[:warm_start]
                if cold_messages:
                    cold_summary = self._get_cached_cold_summary(cold_messages, session_id)
                    result.append({
                        'zone': 'cold_summary',
                        'content': cold_summary
                    })
                logger.info(f'[ContextStore] 冷区摘要: {len(cold_messages)}条 -> 1条摘要')
            else:
                warm_messages = messages[:-hot_zone_size]
                if warm_messages:
                    warm_summary = self._get_cached_warm_summary(warm_messages, session_id)
                    warm_content = self.summarizer.format_warm_summary_for_context(
                        warm_summary, warm_messages
                    )
                    result.append({
                        'zone': 'warm_summary',
                        'content': warm_content
                    })
                logger.info(f'[ContextStore] 温区摘要: {len(warm_messages)}条 -> 1条摘要')

        logger.info(f'[ContextStore] 返回优化消息: {len(result)}条')
        logger.info(f'[ContextStore] ========== get_messages_for_llm 完成 ==========')

        return result

    async def get_messages_for_llm_async(
        self,
        session_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        异步获取用于 LLM 的消息列表（使用 LLM 智能摘要）

        Args:
            session_id: 会话 ID
            user_id: 用户 ID

        Returns:
            优化后的消息列表
        """
        logger.info(f'[ContextStore] ========== get_messages_for_llm_async ==========')
        logger.info(f'[ContextStore] Session: {session_id}, User: {user_id}')

        context = self.get_context(session_id, user_id)

        if not context:
            logger.info(f'[ContextStore] 上下文不存在，返回空列表')
            return []

        messages = context.get('messages', [])

        if not messages:
            logger.info(f'[ContextStore] 无消息历史，返回空列表')
            return []

        logger.info(f'[ContextStore] 原始消息数: {len(messages)}')

        hot_zone_size = self.DEFAULT_HOT_ZONE_SIZE
        warm_zone_size = self.DEFAULT_WARM_ZONE_SIZE

        result: List[Dict[str, Any]] = []
        total_messages = len(messages)

        if total_messages <= hot_zone_size:
            logger.info(f'[ContextStore] 消息数<{hot_zone_size}，全部进入热区')
            for msg in messages:
                result.append({
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', ''),
                    'zone': 'hot'
                })
        else:
            logger.info(f'[ContextStore] 消息数>{hot_zone_size}，启动三层管理')

            hot_messages = messages[-hot_zone_size:]
            for msg in hot_messages:
                result.append({
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', ''),
                    'zone': 'hot'
                })

            remaining = total_messages - hot_zone_size

            if remaining > warm_zone_size:
                warm_start = total_messages - hot_zone_size - warm_zone_size
                warm_messages = messages[warm_start:-hot_zone_size]

                if warm_messages:
                    warm_summary = await self._get_cached_warm_summary_async(warm_messages, session_id)
                    warm_content = self.summarizer.format_warm_summary_for_context(
                        warm_summary, warm_messages
                    )
                    result.append({
                        'zone': 'warm_summary',
                        'content': warm_content
                    })

                cold_messages = messages[:warm_start]
                if cold_messages:
                    cold_summary = await self._get_cached_cold_summary_async(cold_messages, session_id)
                    result.append({
                        'zone': 'cold_summary',
                        'content': cold_summary
                    })
            else:
                warm_messages = messages[:-hot_zone_size]
                if warm_messages:
                    warm_summary = await self._get_cached_warm_summary_async(warm_messages, session_id)
                    warm_content = self.summarizer.format_warm_summary_for_context(
                        warm_summary, warm_messages
                    )
                    result.append({
                        'zone': 'warm_summary',
                        'content': warm_content
                    })

        logger.info(f'[ContextStore] 返回优化消息: {len(result)}条')
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
        logger.info(f'[ContextStore] ========== check_budget ==========')
        context = self.get_context(session_id, user_id)

        if not context:
            logger.info(f'[ContextStore] 上下文不存在，返回初始预算状态')
            return self.budget_manager.check_budget(0)

        messages = context.get('messages', [])
        total_tokens = self.token_calc.count_messages_tokens(messages)
        logger.info(f'[ContextStore] 总Token数: {total_tokens}')

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
            'hot': hot_tokens,
            'warm': warm_tokens,
            'cold': cold_tokens,
            'hot_count': min(total_messages, hot_zone_size),
            'warm_count': max(0, min(total_messages - hot_zone_size, warm_zone_size)),
            'cold_count': max(0, total_messages - hot_zone_size - warm_zone_size),
        }

        logger.info(f'[ContextStore] 分层Token: hot={hot_tokens}, warm={warm_tokens}, cold={cold_tokens}')
        logger.info(f'[ContextStore] 分层消息数: hot={status.tier_breakdown["hot_count"]}, warm={status.tier_breakdown["warm_count"]}, cold={status.tier_breakdown["cold_count"]}')
        logger.info(f'[ContextStore] 预算状态: {status.status.value}, 利用率={status.utilization:.2%}')
        logger.info(f'[ContextStore] ========== check_budget 完成 ==========')

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
                'total_tokens': 0,
                'message_count': 0,
                'model': self.model_name,
                'context_window': self.token_calc.get_context_window(),
            }

        messages = context.get('messages', [])
        total_tokens = self.token_calc.count_messages_tokens(messages)

        return {
            'total_tokens': total_tokens,
            'message_count': len(messages),
            'model': self.model_name,
            'context_window': self.token_calc.get_context_window(),
            'calculation_method': self.token_calc.get_calculation_method(),
            'is_precise': self.token_calc.is_precise(),
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
        msg_metadata['token_count'] = token_count

        return super().append_message(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            metadata=msg_metadata
        )

    def _get_cached_warm_summary(
        self,
        messages: List[Dict[str, Any]],
        session_id: str
    ) -> StructuredSummary:
        """
        获取缓存的温区摘要（同步，使用正则 fallback）

        缓存策略：
        - first_hash: 检测温区边界变化（首条消息变化 = 边界移动）
        - last_hash: 检测尾部新增消息（最后一条消息变化 = 有新消息）
        - count: 消息数量一致性校验

        Args:
            messages: 温区消息列表
            session_id: 会话 ID

        Returns:
            StructuredSummary 对象
        """
        if not messages:
            return StructuredSummary()

        session_cache = self._summary_cache.get(session_id, {})
        cached = session_cache.get('warm')

        first_hash = self._compute_first_message_hash(messages)
        last_hash = self._compute_last_message_hash(messages)

        if cached and cached.get('first_hash') == first_hash:
            cached_summary = cached.get('summary')
            cached_count = cached.get('count', 0)
            cached_last_hash = cached.get('last_hash')

            if (cached_count == len(messages)
                    and cached_last_hash == last_hash
                    and cached_summary):
                self._cache_stats['warm_hits'] += 1
                logger.info(
                    f'[ContextStore] [CACHE HIT] 温区摘要完全命中 (count={len(messages)})'
                )
                return cached_summary

        summary = self.summarizer.generate_warm_summary(messages, self.token_calc)

        self._cache_stats['warm_misses'] += 1
        logger.info(
            f'[ContextStore] [CACHE MISS] 温区摘要重新生成 (count={len(messages)})'
        )

        if session_id:
            if session_id not in self._summary_cache:
                self._summary_cache[session_id] = {}
            self._summary_cache[session_id]['warm'] = {
                'count': len(messages),
                'first_hash': first_hash,
                'last_hash': last_hash,
                'summary': summary,
            }

        return summary

    async def _get_cached_warm_summary_async(
        self,
        messages: List[Dict[str, Any]],
        session_id: str
    ) -> StructuredSummary:
        """
        获取缓存的温区摘要（异步，使用 LLM）

        缓存策略同 _get_cached_warm_summary：first_hash + last_hash + count

        Args:
            messages: 温区消息列表
            session_id: 会话 ID

        Returns:
            StructuredSummary 对象
        """
        if not messages:
            return StructuredSummary()

        session_cache = self._summary_cache.get(session_id, {})
        cached = session_cache.get('warm')

        first_hash = self._compute_first_message_hash(messages)
        last_hash = self._compute_last_message_hash(messages)

        if cached and cached.get('first_hash') == first_hash:
            cached_summary = cached.get('summary')
            cached_count = cached.get('count', 0)
            cached_last_hash = cached.get('last_hash')

            if (cached_count == len(messages)
                    and cached_last_hash == last_hash
                    and cached_summary):
                self._cache_stats['warm_hits'] += 1
                logger.info(
                    f'[ContextStore] [CACHE HIT] 温区摘要完全命中 (count={len(messages)})'
                )
                return cached_summary

        summary = await self.summarizer.generate_warm_summary_async(messages, self.token_calc)

        self._cache_stats['warm_misses'] += 1
        logger.info(
            f'[ContextStore] [CACHE MISS] 温区摘要重新生成 (count={len(messages)})'
        )

        if session_id:
            if session_id not in self._summary_cache:
                self._summary_cache[session_id] = {}
            self._summary_cache[session_id]['warm'] = {
                'count': len(messages),
                'first_hash': first_hash,
                'last_hash': last_hash,
                'summary': summary,
            }

        return summary

    def _get_cached_cold_summary(
        self,
        messages: List[Dict[str, Any]],
        session_id: str
    ) -> str:
        """
        获取缓存的冷区摘要（同步）

        Args:
            messages: 冷区消息列表
            session_id: 会话 ID

        Returns:
            摘要文本
        """
        if not messages:
            return ''

        session_cache = self._summary_cache.get(session_id, {})
        cached = session_cache.get('cold')

        if cached and cached.get('count') == len(messages):
            cached_summary = cached.get('summary')
            if cached_summary:
                self._cache_stats['cold_hits'] += 1
                logger.info(
                    f'[ContextStore] [CACHE HIT] 冷区摘要完全命中 (count={len(messages)})'
                )
                return cached_summary

        summary = self.summarizer.generate_cold_summary([], messages)

        self._cache_stats['cold_misses'] += 1
        logger.info(
            f'[ContextStore] [CACHE MISS] 冷区摘要重新生成 (count={len(messages)})'
        )

        if session_id:
            if session_id not in self._summary_cache:
                self._summary_cache[session_id] = {}
            self._summary_cache[session_id]['cold'] = {
                'count': len(messages),
                'summary': summary,
            }

        return summary

    async def _get_cached_cold_summary_async(
        self,
        messages: List[Dict[str, Any]],
        session_id: str
    ) -> str:
        """
        获取缓存的冷区摘要（异步，使用 LLM）

        Args:
            messages: 冷区消息列表
            session_id: 会话 ID

        Returns:
            摘要文本
        """
        if not messages:
            return ''

        session_cache = self._summary_cache.get(session_id, {})
        cached = session_cache.get('cold')

        if cached and cached.get('count') == len(messages):
            cached_summary = cached.get('summary')
            if cached_summary:
                self._cache_stats['cold_hits'] += 1
                logger.info(
                    f'[ContextStore] [CACHE HIT] 冷区摘要完全命中 (count={len(messages)})'
                )
                return cached_summary

        summary = await self.summarizer.generate_cold_summary_async([], messages)

        self._cache_stats['cold_misses'] += 1
        logger.info(
            f'[ContextStore] [CACHE MISS] 冷区摘要重新生成 (count={len(messages)})'
        )

        if session_id:
            if session_id not in self._summary_cache:
                self._summary_cache[session_id] = {}
            self._summary_cache[session_id]['cold'] = {
                'count': len(messages),
                'summary': summary,
            }

        return summary

    def _compute_first_message_hash(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        计算首条消息哈希（用于检测温区边界变化）

        Args:
            messages: 消息列表

        Returns:
            哈希字符串
        """
        if not messages:
            return ''
        first_content = messages[0].get('content', '')[:200]
        return hashlib.sha256(first_content.encode('utf-8')).hexdigest()[:12]

    def _compute_last_message_hash(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        计算末条消息哈希（用于检测尾部新增消息）

        Args:
            messages: 消息列表

        Returns:
            哈希字符串
        """
        if not messages:
            return ''
        last_content = messages[-1].get('content', '')[:200]
        return hashlib.sha256(last_content.encode('utf-8')).hexdigest()[:12]

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取摘要缓存统计"""
        warm_total = self._cache_stats['warm_hits'] + self._cache_stats['warm_misses']
        cold_total = self._cache_stats['cold_hits'] + self._cache_stats['cold_misses']
        return {
            'warm_hits': self._cache_stats['warm_hits'],
            'warm_misses': self._cache_stats['warm_misses'],
            'warm_hit_rate': (self._cache_stats['warm_hits'] / warm_total) if warm_total > 0 else 0,
            'cold_hits': self._cache_stats['cold_hits'],
            'cold_misses': self._cache_stats['cold_misses'],
            'cold_hit_rate': (self._cache_stats['cold_hits'] / cold_total) if cold_total > 0 else 0,
            'cached_sessions': len(self._summary_cache),
        }

    def clear_cache(self, session_id: Optional[str] = None) -> None:
        """
        清除摘要缓存

        Args:
            session_id: 会话 ID（可选，不提供则清除全部）
        """
        if session_id:
            self._summary_cache.pop(session_id, None)
        else:
            self._summary_cache.clear()
        logger.info(f'[ContextStore] 缓存已清除: session={session_id or "ALL"}')