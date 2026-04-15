"""
智能摘要生成器

实现温区和冷区的摘要生成。

摘要类型：
- 温区摘要（结构化）：提取主题、决策、实体、待办
- 冷区摘要（语义）：LLM 生成段落级总结

Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md 机制5
"""

import re
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .base import StructuredSummary

logger = logging.getLogger(__name__)


@dataclass
class SummaryConfig:
    """摘要配置"""
    max_warm_summary_tokens: int = 500
    max_cold_summary_tokens: int = 200
    max_topics: int = 5
    max_entities: int = 10
    max_actions: int = 5
    enable_llm_summarization: bool = True


class SmartSummarizer:
    """
    智能摘要生成器
    
    功能：
    1. 温区结构化摘要：提取关键信息
    2. 冷区语义摘要：LLM 生成总结
    3. Token 预算控制
    
    使用示例：
        summarizer = SmartSummarizer(llm_service=llm_service)
        warm_summary = summarizer.generate_warm_summary(messages, token_calc)
        cold_summary = summarizer.generate_cold_summary(summary_history)
    """
    
    DEFAULT_CONFIG = SummaryConfig()
    
    KEYWORDS_PATTERN = [
        (r'测试用例|test case', '测试用例'),
        (r'API|接口', 'API测试'),
        (r'UI|界面|页面', 'UI测试'),
        (r'pytest|unittest', '单元测试'),
        (r'Playwright|Selenium', '自动化测试'),
        (r'登录|注册|认证', '认证功能'),
        (r'数据库|database', '数据库'),
        (r'配置|config', '配置'),
    ]
    
    def __init__(
        self,
        llm_service: Optional[Any] = None,
        config: Optional[SummaryConfig] = None
    ) -> None:
        """
        初始化摘要生成器
        
        Args:
            llm_service: LLM 服务（可选，用于生成语义摘要）
            config: 摘要配置
        """
        self.llm_service = llm_service
        self.config = config or self.DEFAULT_CONFIG
    
    def generate_warm_summary(
        self,
        messages: List[Dict[str, Any]],
        token_calculator: Optional[Any] = None
    ) -> StructuredSummary:
        """
        生成温区结构化摘要
        
        提取：
        - 主题标签
        - 关键决策
        - 实体（API、文件、变量名）
        - 待办事项
        
        Args:
            messages: 温区消息列表
            token_calculator: Token 计算器
            
        Returns:
            StructuredSummary 对象
        """
        if not messages:
            return StructuredSummary()
        
        topics = set()
        decisions = []
        entities = set()
        actions = []
        
        all_content = ""
        for msg in messages:
            content = msg.get("content", "")
            all_content += content + "\n"
            
            for pattern, topic in self.KEYWORDS_PATTERN:
                if re.search(pattern, content, re.IGNORECASE):
                    topics.add(topic)
            
            code_blocks = re.findall(r'```(\w+)', content)
            topics.update(code_blocks)
            
            urls = re.findall(r'https?://[^\s]+', content)
            entities.update(urls)
            
            file_paths = re.findall(r'[\w/\-\.]+\.(py|js|ts|json|yaml|yml)', content)
            entities.update(file_paths)
            
            function_names = re.findall(r'def\s+(\w+)|function\s+(\w+)', content)
            for match in function_names:
                name = match[0] or match[1]
                if name:
                    entities.add(name)
            
            decision_markers = re.findall(
                r'(?:决定|确定|选择|使用)(.+?)(?:，|。|\n|$)',
                content
            )
            for decision in decision_markers:
                decision = decision.strip()
                if len(decision) > 5 and len(decision) < 100:
                    decisions.append(decision)
            
            action_markers = re.findall(
                r'(?:需要|待办|TODO|下一步)(.+?)(?:，|。|\n|$)',
                content,
                re.IGNORECASE
            )
            for action in action_markers:
                action = action.strip()
                if len(action) > 3 and len(action) < 100:
                    actions.append(action)
        
        topics_list = list(topics)[:self.config.max_topics]
        entities_list = list(entities)[:self.config.max_entities]
        actions = actions[:self.config.max_actions]
        decisions = decisions[:5]
        
        original_tokens = 0
        if token_calculator:
            original_tokens = token_calculator.count_messages_tokens(messages)
        
        summary_text = self._format_summary_text(topics_list, decisions, entities_list, actions)
        summary_tokens = 0
        if token_calculator:
            summary_tokens = token_calculator.count_tokens(summary_text)
        
        tokens_saved = max(0, original_tokens - summary_tokens)
        compression_ratio = tokens_saved / original_tokens if original_tokens > 0 else 0
        
        return StructuredSummary(
            topics=topics_list,
            decisions=decisions,
            entities=entities_list,
            actions=actions,
            token_saved=tokens_saved,
            compression_ratio=compression_ratio
        )
    
    def _format_summary_text(
        self,
        topics: List[str],
        decisions: List[str],
        entities: List[str],
        actions: List[str]
    ) -> str:
        """格式化摘要文本"""
        lines = []
        
        if topics:
            lines.append(f"主题: {', '.join(topics)}")
        
        if decisions:
            lines.append("决策:")
            for d in decisions[:3]:
                lines.append(f"  - {d}")
        
        if entities:
            lines.append(f"实体: {', '.join(entities[:5])}")
        
        if actions:
            lines.append("待办:")
            for a in actions[:3]:
                lines.append(f"  - {a}")
        
        return "\n".join(lines)
    
    async def generate_cold_summary_async(
        self,
        summary_history: List[str],
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        异步生成冷区语义摘要
        
        使用 LLM 生成段落级总结
        
        Args:
            summary_history: 历史摘要列表
            messages: 原始消息（可选）
            
        Returns:
            语义摘要文本
        """
        if not summary_history and not messages:
            return ""
        
        if self.llm_service:
            return await self._generate_llm_summary(summary_history, messages)
        else:
            return self._generate_simple_summary(summary_history, messages)
    
    def generate_cold_summary(
        self,
        summary_history: List[str],
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """同步生成冷区摘要"""
        if not summary_history and not messages:
            return ""
        
        return self._generate_simple_summary(summary_history, messages)
    
    async def _generate_llm_summary(
        self,
        summary_history: List[str],
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """使用 LLM 生成摘要"""
        context_parts = []
        
        if summary_history:
            context_parts.append("历史摘要:\n" + "\n".join(summary_history[-3:]))
        
        if messages:
            msg_summary = self._extract_message_highlights(messages)
            context_parts.append("关键对话:\n" + msg_summary)
        
        prompt = f"""基于以下内容，生成一个简洁的总结（100-200字）：

{chr(10).join(context_parts)}

要求：
- 保留关键业务上下文
- 删除具体实现细节
- 突出当前阶段和下一步
- 使用专业术语
"""
        
        try:
            assert self.llm_service is not None
            response: str = await self.llm_service.generate(prompt)
            return response.strip()[:500]
        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}")
            return self._generate_simple_summary(summary_history, messages)
    
    def _generate_simple_summary(
        self,
        summary_history: List[str],
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """生成简单摘要（无 LLM）"""
        parts = []
        
        if summary_history:
            parts.append(f"包含 {len(summary_history)} 个历史阶段")
        
        if messages:
            user_count = sum(1 for m in messages if m.get("role") == "user")
            assistant_count = sum(1 for m in messages if m.get("role") == "assistant")
            parts.append(f"用户提问 {user_count} 次，助手回复 {assistant_count} 次")
            
            if user_count > 0:
                first_user_msg = next(
                    (m for m in messages if m.get("role") == "user"),
                    None
                )
                if first_user_msg:
                    content = first_user_msg.get("content", "")[:50]
                    parts.append(f"始于: {content}...")
        
        return " | ".join(parts) if parts else ""
    
    def _extract_message_highlights(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """提取消息亮点"""
        highlights = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                content = content[:100]
                highlights.append(f"用户: {content}")
            
            if len(highlights) >= 5:
                break
        
        return "\n".join(highlights)
    
    def estimate_summary_tokens(
        self,
        messages: List[Dict[str, Any]],
        zone_type: str,
        token_calculator: Any
    ) -> int:
        """
        估算摘要的 Token 数
        
        Args:
            messages: 原始消息
            zone_type: 区域类型
            token_calculator: Token 计算器
            
        Returns:
            预估的摘要 Token 数
        """
        original = token_calculator.count_messages_tokens(messages)
        
        if zone_type == "warm":
            return min(
                self.config.max_warm_summary_tokens,
                int(original * 0.3)
            )
        elif zone_type == "cold":
            return min(
                self.config.max_cold_summary_tokens,
                int(original * 0.1)
            )
        
        return int(original * 0.2)