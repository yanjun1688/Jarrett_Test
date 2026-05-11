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
from typing import Dict, Any, Optional, List, Tuple, cast, TYPE_CHECKING
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
        """获取用于 LLM 的消息列表（同步，正则摘要）"""
        messages = self._get_context_messages(session_id, user_id, 'get_messages_for_llm')
        if not messages:
            return []

        warm_summary = None
        cold_summary = None
        warm_msgs, cold_msgs = self._split_zones(messages)

        if warm_msgs is not None:
            warm_summary = self._get_cached_warm_summary(warm_msgs, session_id)
        if cold_msgs is not None:
            cold_summary = self._get_cached_cold_summary(cold_msgs, session_id)

        return self._build_zone_result(messages, warm_summary, cold_summary, warm_msgs, caller='get_messages_for_llm')

    async def get_messages_for_llm_async(
        self,
        session_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """获取用于 LLM 的消息列表（异步，LLM 摘要）"""
        messages = self._get_context_messages(session_id, user_id, 'get_messages_for_llm_async')
        if not messages:
            return []

        warm_summary = None
        cold_summary = None
        warm_msgs, cold_msgs = self._split_zones(messages)

        if warm_msgs is not None:
            warm_summary = await self._get_cached_warm_summary_async(warm_msgs, session_id)
        if cold_msgs is not None:
            cold_summary = await self._get_cached_cold_summary_async(cold_msgs, session_id)

        return self._build_zone_result(messages, warm_summary, cold_summary, warm_msgs, caller='get_messages_for_llm_async')

    # ── helpers: 消除 sync/async 重复 ──

    def _get_context_messages(
        self,
        session_id: str,
        user_id: str,
        caller: str,
    ) -> List[Dict[str, Any]]:
        """获取会话消息列表（sync/async 共享前缀）"""
        logger.info(f'[ContextStore] ========== {caller} ==========')
        logger.info(f'[ContextStore] Session: {session_id}, User: {user_id}')

        context = self.get_context(session_id, user_id)
        if not context:
            logger.info(f'[ContextStore] 上下文不存在，返回空列表')
            return []

        messages: List[Dict[str, Any]] = context.get('messages', [])
        if not messages:
            logger.info(f'[ContextStore] 无消息历史，返回空列表')
            return []

        logger.info(f'[ContextStore] 原始消息数: {len(messages)}')
        return messages

    def _split_zones(
        self,
        messages: List[Dict[str, Any]],
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[Dict[str, Any]]]]:
        """按三层区域拆分消息，返回 warm_msgs, cold_msgs（热区由 _build_zone_result 直接取）"""
        total = len(messages)
        hot_size = self.DEFAULT_HOT_ZONE_SIZE
        warm_size = self.DEFAULT_WARM_ZONE_SIZE

        warm_msgs = None
        cold_msgs = None

        if total > hot_size:
            if total - hot_size > warm_size:
                warm_start = max(0, total - hot_size - warm_size)
                warm_msgs = messages[warm_start:-hot_size] if warm_start < total - hot_size else None
                cold_msgs = messages[:warm_start] if warm_start > 0 else None
            else:
                warm_msgs = messages[:-hot_size] if total > hot_size else None

        return warm_msgs, cold_msgs

    def _build_zone_result(
        self,
        messages: List[Dict[str, Any]],
        warm_summary: Optional[StructuredSummary],
        cold_summary: Optional[str],
        warm_msgs: Optional[List[Dict[str, Any]]],
        caller: str = "",
    ) -> List[Dict[str, Any]]:
        """将消息和摘要拼装为三层结果列表（sync/async 共享后缀）"""
        hot_size = self.DEFAULT_HOT_ZONE_SIZE
        result: List[Dict[str, Any]] = []

        if len(messages) <= hot_size:
            logger.info(f'[ContextStore] 消息数<={hot_size}，全部进入热区')
            for msg in messages:
                result.append({
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', ''),
                    'zone': 'hot',
                })
        else:
            logger.info(f'[ContextStore] 消息数>{hot_size}，启动三层管理')
            hot_messages = messages[-hot_size:]
            for msg in hot_messages:
                result.append({
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', ''),
                    'zone': 'hot',
                })
            logger.info(f'[ContextStore] 热区消息: {len(hot_messages)}条')

            if warm_summary is not None:
                warm_content = self.summarizer.format_warm_summary_for_context(
                    warm_summary, warm_msgs or []
                )
                result.append({'zone': 'warm_summary', 'content': warm_content})
                logger.info(f'[ContextStore] 温区摘要: {len(warm_msgs or [])}条 -> 1条摘要')

            if cold_summary:
                result.append({'zone': 'cold_summary', 'content': cold_summary})
                logger.info(f'[ContextStore] 冷区摘要 -> 1条摘要')

        logger.info(f'[ContextStore] 返回优化消息: {len(result)}条')
        logger.info(f'[ContextStore] ========== {caller} 完成 ==========')
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

        budget_status = self.budget_manager.check_budget(total_tokens)

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

        budget_status.tier_breakdown = {
            'hot': hot_tokens,
            'warm': warm_tokens,
            'cold': cold_tokens,
            'hot_count': min(total_messages, hot_zone_size),
            'warm_count': max(0, min(total_messages - hot_zone_size, warm_zone_size)),
            'cold_count': max(0, total_messages - hot_zone_size - warm_zone_size),
        }

        logger.info(f'[ContextStore] 分层Token: hot={hot_tokens}, warm={warm_tokens}, cold={cold_tokens}')
        logger.info(f'[ContextStore] 分层消息数: hot={budget_status.tier_breakdown["hot_count"]}, warm={budget_status.tier_breakdown["warm_count"]}, cold={budget_status.tier_breakdown["cold_count"]}')
        logger.info(f'[ContextStore] 预算状态: {budget_status.status.value}, 利用率={budget_status.utilization:.2%}')
        logger.info(f'[ContextStore] ========== check_budget 完成 ==========')

        return budget_status

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

        return bool(super().append_message(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            metadata=msg_metadata
        ))

    # ── helpers: 消除 warm/cold 缓存 sync/async 重复 ──

    def _check_warm_cache(
        self, messages: List[Dict[str, Any]], session_id: str
    ) -> Tuple[Optional[StructuredSummary], str, str]:
        """检查温区缓存命中。返回 (summary | None, first_hash, last_hash)。"""
        cache_entry = self._summary_cache.get(session_id, {}).get('warm') if session_id else None
        first_hash = self._compute_first_message_hash(messages)
        last_hash = self._compute_last_message_hash(messages)

        if cache_entry and cache_entry.get('first_hash') == first_hash:
            cs = cache_entry.get('summary')
            if (cache_entry.get('count') == len(messages)
                    and cache_entry.get('last_hash') == last_hash
                    and cs is not None):
                return cast(StructuredSummary, cs), first_hash, last_hash

        return None, first_hash, last_hash

    def _store_warm_cache(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        summary: StructuredSummary,
        first_hash: str,
        last_hash: str,
    ) -> None:
        if session_id:
            self._summary_cache.setdefault(session_id, {})['warm'] = {
                'count': len(messages),
                'first_hash': first_hash,
                'last_hash': last_hash,
                'summary': summary,
            }

    def _get_cached_warm_summary(
        self,
        messages: List[Dict[str, Any]],
        session_id: str
    ) -> StructuredSummary:
        if not messages:
            return StructuredSummary()

        cached, first_hash, last_hash = self._check_warm_cache(messages, session_id)
        if cached is not None:
            self._cache_stats['warm_hits'] += 1
            logger.info(f'[ContextStore] [CACHE HIT] 温区摘要完全命中 (count={len(messages)})')
            return cached

        summary = self.summarizer.generate_warm_summary(messages, self.token_calc)
        self._cache_stats['warm_misses'] += 1
        logger.info(f'[ContextStore] [CACHE MISS] 温区摘要重新生成 (count={len(messages)})')
        self._store_warm_cache(session_id, messages, summary, first_hash, last_hash)
        return summary

    async def _get_cached_warm_summary_async(
        self,
        messages: List[Dict[str, Any]],
        session_id: str
    ) -> StructuredSummary:
        if not messages:
            return StructuredSummary()

        cached, first_hash, last_hash = self._check_warm_cache(messages, session_id)
        if cached is not None:
            self._cache_stats['warm_hits'] += 1
            logger.info(f'[ContextStore] [CACHE HIT] 温区摘要完全命中 (count={len(messages)})')
            return cached

        summary = await self.summarizer.generate_warm_summary_async(messages, self.token_calc)
        self._cache_stats['warm_misses'] += 1
        logger.info(f'[ContextStore] [CACHE MISS] 温区摘要重新生成 (count={len(messages)})')
        self._store_warm_cache(session_id, messages, summary, first_hash, last_hash)
        return summary

    def _check_cold_cache(
        self, messages: List[Dict[str, Any]], session_id: str
    ) -> Tuple[Optional[str], str]:
        """检查冷区缓存命中。返回 (summary | None, cold_hash)。"""
        cache_entry = self._summary_cache.get(session_id, {}).get('cold') if session_id else None
        cold_hash = self._compute_cold_messages_hash(messages)

        if cache_entry and cache_entry.get('count') == len(messages) and cache_entry.get('hash') == cold_hash:
            cs = cache_entry.get('summary')
            if cs is not None:
                return str(cs), cold_hash

        return None, cold_hash

    def _store_cold_cache(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        summary: str,
        cold_hash: str,
    ) -> None:
        if session_id:
            self._summary_cache.setdefault(session_id, {})['cold'] = {
                'count': len(messages),
                'hash': cold_hash,
                'summary': summary,
            }

    def _get_cached_cold_summary(
        self,
        messages: List[Dict[str, Any]],
        session_id: str
    ) -> str:
        if not messages:
            return ''

        cached, cold_hash = self._check_cold_cache(messages, session_id)
        if cached is not None:
            self._cache_stats['cold_hits'] += 1
            logger.info(f'[ContextStore] [CACHE HIT] 冷区摘要完全命中 (count={len(messages)})')
            return cached

        summary = str(self.summarizer.generate_cold_summary([], messages))
        self._cache_stats['cold_misses'] += 1
        logger.info(f'[ContextStore] [CACHE MISS] 冷区摘要重新生成 (count={len(messages)})')
        self._store_cold_cache(session_id, messages, summary, cold_hash)
        return summary

    async def _get_cached_cold_summary_async(
        self,
        messages: List[Dict[str, Any]],
        session_id: str
    ) -> str:
        if not messages:
            return ''

        cached, cold_hash = self._check_cold_cache(messages, session_id)
        if cached is not None:
            self._cache_stats['cold_hits'] += 1
            logger.info(f'[ContextStore] [CACHE HIT] 冷区摘要完全命中 (count={len(messages)})')
            return cached

        summary = str(await self.summarizer.generate_cold_summary_async([], messages))
        self._cache_stats['cold_misses'] += 1
        logger.info(f'[ContextStore] [CACHE MISS] 冷区摘要重新生成 (count={len(messages)})')
        self._store_cold_cache(session_id, messages, summary, cold_hash)
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
        return hashlib.sha256(first_content.encode('utf-8')).hexdigest()[:16]

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
        return hashlib.sha256(last_content.encode('utf-8')).hexdigest()[:16]

    def _compute_cold_messages_hash(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """计算冷区消息内容哈希（用于缓存校验）"""
        if not messages:
            return ''
        content_sample = ''.join(
            str(m.get('content', ''))[:100] for m in messages
        )
        return hashlib.sha256(content_sample.encode('utf-8')).hexdigest()[:16]

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