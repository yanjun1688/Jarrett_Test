"""
智能摘要生成器

实现温区和冷区的摘要生成。

摘要类型：
- 温区摘要（结构化）：LLM 提取主题、决策、实体、待办
- 冷区摘要（语义）：LLM 生成段落级总结

设计原则：
- LLM 为主要提取方式，正则为 fallback
- 单一实现，避免重复代码
- 类型注解完整

Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md 机制5
"""

from __future__ import annotations

import json
import re
import logging
from typing import Dict, Any, Optional, List, Set, TYPE_CHECKING
from dataclasses import dataclass, field

from .base import StructuredSummary

if TYPE_CHECKING:
    from core.agents.llm.base_llm import BaseLLMService

logger = logging.getLogger(__name__)


@dataclass
class SummaryConfig:
    """摘要配置"""
    max_warm_summary_tokens: int = 500
    max_cold_summary_tokens: int = 200
    max_topics: int = 5
    max_entities: int = 10
    max_actions: int = 5
    max_decisions: int = 5
    enable_llm_summarization: bool = True


@dataclass
class ExtractedEntities:
    """提取的实体分类"""
    apis: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    modules: List[str] = field(default_factory=list)
    error_types: List[str] = field(default_factory=list)

    def to_flat_list(self) -> List[str]:
        """转换为扁平列表"""
        return self.apis + self.files + self.functions + self.urls + self.modules + self.error_types


class SmartSummarizer:
    """
    智能摘要生成器

    功能：
    1. 温区结构化摘要：LLM/正则提取关键信息
    2. 冷区语义摘要：LLM 生成总结
    3. Token 预算控制
    4. Fallback 机制：LLM 失败时降级为正则提取

    使用示例：
        summarizer = SmartSummarizer(llm_service=llm_service)

        # 异步方式（推荐）
        warm_summary = await summarizer.generate_warm_summary_async(messages, token_calc)

        # 同步方式（使用正则 fallback）
        warm_summary = summarizer.generate_warm_summary(messages, token_calc)

        cold_summary = await summarizer.generate_cold_summary_async(summary_history)
    """

    DEFAULT_CONFIG = SummaryConfig()

    LLM_PROMPT_TEMPLATE = """从以下对话内容中提取结构化信息，以 JSON 格式返回。

要求：
1. 提取的主题要有边界约束，避免误匹配（如 "UI" 不应匹配 "UUID")
2. 决策要识别显式和隐式表达（如 "最终方案是..."、"采纳了..."、"选择使用..."）
3. 实体按类型分类：API路径、文件名、函数名、URL、模块名、错误类型
4. 待办事项提取内容和优先级（high/medium/low）

返回格式（严格 JSON）：
```json
{{
  "topics": ["主题1", "主题2"],
  "decisions": ["决策内容1", "决策内容2"],
  "entities": {{
    "apis": ["GET /api/users", "POST /api/login"],
    "files": ["test_api.py", "config.yaml"],
    "functions": ["process_data", "validate_input"],
    "urls": ["https://example.com"],
    "modules": ["django.db", "pytest"],
    "error_types": ["ValueError", "TypeError"]
  }},
  "actions": [
    {{"content": "完成登录功能测试", "priority": "high"}},
    {{"content": "编写单元测试", "priority": "medium"}}
  ]
}}
```

对话内容：
{content}
"""

    FALLBACK_KEYWORDS_PATTERN = [
        (r'\b测试用例\b|\btest\s*case\b', '测试用例'),
        (r'\bAPI\b|\b接口\b', 'API测试'),
        (r'\bUI\b|\b界面\b|\b页面\b', 'UI测试'),
        (r'\bpytest\b|\bunittest\b', '单元测试'),
        (r'\bPlaywright\b|\bSelenium\b', '自动化测试'),
        (r'\b登录\b|\b注册\b|\b认证\b', '认证功能'),
        (r'\b数据库\b|\bdatabase\b', '数据库'),
        (r'\b配置\b|\bconfig\b', '配置'),
        (r'\b压测\b|\b压力测试\b', '压力测试'),
        (r'\b性能\b|\bperformance\b', '性能测试'),
    ]

    FALLBACK_DECISION_PATTERN = r'(?:决定|确定|选择|使用|最终方案|采纳|采用)(.+?)(?=[，。,.\n]|$)'

    FALLBACK_ACTION_PATTERN = r'(?:需要|待办|TODO|下一步|接下来|稍后|本周|尽快)(.+?)(?=[，。,.\n]|$)'

    def __init__(
        self,
        llm_service: Optional[BaseLLMService] = None,
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

    async def generate_warm_summary_async(
        self,
        messages: List[Dict[str, Any]],
        token_calculator: Optional[Any] = None
    ) -> StructuredSummary:
        """
        异步生成温区结构化摘要（LLM 优先）

        Args:
            messages: 温区消息列表
            token_calculator: Token 计算器

        Returns:
            StructuredSummary 对象
        """
        if not messages:
            return StructuredSummary()

        if self.llm_service:
            try:
                summary = await self._generate_warm_summary_with_llm(messages, token_calculator)
                if summary:
                    return summary
            except Exception as e:
                logger.warning(f"LLM 温区摘要生成失败，降级为正则提取: {e}")

        return self._generate_warm_summary_with_regex(messages, token_calculator)

    def generate_warm_summary(
        self,
        messages: List[Dict[str, Any]],
        token_calculator: Optional[Any] = None
    ) -> StructuredSummary:
        """
        同步生成温区结构化摘要（正则提取）

        作为 fallback 方法，当 LLM 不可用时使用。

        Args:
            messages: 温区消息列表
            token_calculator: Token 计算器

        Returns:
            StructuredSummary 对象
        """
        if not messages:
            return StructuredSummary()

        return self._generate_warm_summary_with_regex(messages, token_calculator)

    async def _generate_warm_summary_with_llm(
        self,
        messages: List[Dict[str, Any]],
        token_calculator: Optional[Any] = None
    ) -> Optional[StructuredSummary]:
        """
        使用 LLM 生成温区结构化摘要

        Args:
            messages: 消息列表
            token_calculator: Token 计算器

        Returns:
            StructuredSummary 或 None（失败时）
        """
        all_content = self._concat_messages_content(messages)

        if len(all_content) < 50:
            logger.info("内容过短，跳过 LLM 提取")
            return None

        prompt = self.LLM_PROMPT_TEMPLATE.format(content=all_content[:3000])

        try:
            assert self.llm_service is not None
            response = await self.llm_service.generate(
                prompt=prompt,
                system_message="你是一个专业的测试领域信息提取助手。请严格按照 JSON 格式返回结果。"
            )

            parsed = self._parse_llm_response(response)

            if parsed:
                original_tokens = 0
                summary_tokens = 0
                if token_calculator:
                    original_tokens = token_calculator.count_messages_tokens(messages)
                    # flatten entities for _format_summary_text (LLM 返回的是嵌套 dict)
                    flat_entities = self._flatten_entities(parsed.get('entities', {}))
                    flat_actions = [
                        a.get('content', str(a)) if isinstance(a, dict) else str(a)
                        for a in parsed.get('actions', [])
                    ]
                    summary_text = self._format_summary_text({
                        'topics': parsed.get('topics', []),
                        'decisions': parsed.get('decisions', []),
                        'entities': flat_entities,
                        'actions': flat_actions,
                    })
                    summary_tokens = token_calculator.count_tokens(summary_text)

                return StructuredSummary(
                    topics=parsed.get('topics', [])[:self.config.max_topics],
                    decisions=parsed.get('decisions', [])[:self.config.max_decisions],
                    entities=self._flatten_entities(parsed.get('entities', {}))[:self.config.max_entities],
                    actions=[a.get('content', str(a)) for a in parsed.get('actions', [])][:self.config.max_actions],
                    token_saved=max(0, original_tokens - summary_tokens),
                    compression_ratio=max(0, original_tokens - summary_tokens) / original_tokens if original_tokens > 0 else 0
                )

        except json.JSONDecodeError as e:
            logger.warning(f"LLM 返回 JSON 解析失败: {e}")
        except Exception as e:
            logger.warning(f"LLM 温区摘要生成异常: {e}")

        return None

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        解析 LLM 返回的 JSON

        Args:
            response: LLM 返回的文本

        Returns:
            解析后的字典或 None
        """
        try:
            json_match = re.search(r'```json\s*([\s\S]+?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                else:
                    return None

            return json.loads(json_str)  # type: ignore[no-any-return]

        except json.JSONDecodeError:
            return None

    def _flatten_entities(self, entities: Dict[str, Any]) -> List[str]:
        """
        将实体字典转换为扁平列表

        Args:
            entities: 实体分类字典

        Returns:
            扁平实体列表
        """
        result: List[str] = []
        for key in ['apis', 'files', 'functions', 'urls', 'modules', 'error_types']:
            values = entities.get(key, [])
            if isinstance(values, list):
                result.extend(values)
        return result

    def _generate_warm_summary_with_regex(
        self,
        messages: List[Dict[str, Any]],
        token_calculator: Optional[Any] = None
    ) -> StructuredSummary:
        """
        使用正则表达式生成温区结构化摘要（fallback）

        Args:
            messages: 消息列表
            token_calculator: Token 计算器

        Returns:
            StructuredSummary 对象
        """
        topics: Set[str] = set()
        decisions: List[str] = []
        entities = ExtractedEntities()
        actions: List[str] = []

        all_content = self._concat_messages_content(messages)

        for pattern, topic in self.FALLBACK_KEYWORDS_PATTERN:
            if re.search(pattern, all_content, re.IGNORECASE):
                topics.add(topic)

        code_blocks = re.findall(r'```(\w+)\b', all_content)
        topics.update(code_blocks)

        entities.urls = re.findall(r'https?://[^\s<>"\']+', all_content)

        entities.files = re.findall(r'[\w/\-\.]+\.(?:py|js|ts|tsx|json|yaml|yml|md|txt|xml)\b', all_content)

        function_matches = re.findall(r'def\s+(\w+)\b|function\s+(\w+)\b|class\s+(\w+)\b', all_content)
        for match in function_matches:
            name = match[0] or match[1] or match[2]
            if name:
                entities.functions.append(name)

        module_matches = re.findall(r'from\s+([\w\.]+)\s+import|import\s+([\w\.]+)', all_content)
        for match in module_matches:
            module = match[0] or match[1]
            if module:
                entities.modules.append(module)

        error_types = re.findall(r'\b(ValueError|TypeError|KeyError|IndexError|AttributeError|RuntimeError|AssertionError)\b', all_content)
        entities.error_types = list(set(error_types))

        api_patterns = re.findall(r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[\w/\-\.{}]+)', all_content)
        entities.apis = api_patterns

        decision_matches = re.findall(self.FALLBACK_DECISION_PATTERN, all_content)
        for decision in decision_matches:
            decision = decision.strip()
            if 5 < len(decision) < 100:
                decisions.append(decision)

        action_matches = re.findall(self.FALLBACK_ACTION_PATTERN, all_content, re.IGNORECASE)
        for action in action_matches:
            action = action.strip()
            if 3 < len(action) < 100:
                actions.append(action)

        topics_list = list(topics)[:self.config.max_topics]
        entities_list = entities.to_flat_list()[:self.config.max_entities]
        decisions_list = decisions[:self.config.max_decisions]
        actions_list = actions[:self.config.max_actions]

        original_tokens = 0
        summary_tokens = 0
        if token_calculator:
            original_tokens = token_calculator.count_messages_tokens(messages)
            summary_text = self._format_summary_text({
                'topics': topics_list,
                'decisions': decisions_list,
                'entities': entities_list,
                'actions': actions_list
            })
            summary_tokens = token_calculator.count_tokens(summary_text)

        return StructuredSummary(
            topics=topics_list,
            decisions=decisions_list,
            entities=entities_list,
            actions=actions_list,
            token_saved=max(0, original_tokens - summary_tokens),
            compression_ratio=max(0, original_tokens - summary_tokens) / original_tokens if original_tokens > 0 else 0
        )

    def _concat_messages_content(self, messages: List[Dict[str, Any]]) -> str:
        """
        合并消息内容

        Args:
            messages: 消息列表

        Returns:
            合并后的文本
        """
        contents = []
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, str):
                contents.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        contents.append(block.get('text', ''))
        return '\n'.join(contents)

    def _format_summary_text(
        self,
        data: Dict[str, Any]
    ) -> str:
        """
        格式化摘要文本

        Args:
            data: 摘要数据字典

        Returns:
            格式化的摘要文本
        """
        lines = []

        topics = data.get('topics', [])
        if topics:
            lines.append(f"主题: {', '.join(topics)}")

        decisions = data.get('decisions', [])
        if decisions:
            lines.append("决策:")
            for d in decisions[:3]:
                lines.append(f"  - {d}")

        entities = data.get('entities', [])
        if entities:
            lines.append(f"实体: {', '.join(entities[:5])}")

        actions = data.get('actions', [])
        if actions:
            lines.append("待办:")
            for a in actions[:3]:
                lines.append(f"  - {a}")

        return '\n'.join(lines)

    async def generate_cold_summary_async(
        self,
        summary_history: List[str],
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        异步生成冷区语义摘要

        Args:
            summary_history: 历史摘要列表
            messages: 原始消息（可选）

        Returns:
            语义摘要文本
        """
        if not summary_history and not messages:
            return ''

        if self.llm_service:
            return await self._generate_llm_cold_summary(summary_history, messages)
        else:
            return self._generate_simple_cold_summary(summary_history, messages)

    def generate_cold_summary(
        self,
        summary_history: List[str],
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        同步生成冷区摘要

        Args:
            summary_history: 历史摘要列表
            messages: 原始消息（可选）

        Returns:
            摘要文本
        """
        if not summary_history and not messages:
            return ''

        return self._generate_simple_cold_summary(summary_history, messages)

    async def _generate_llm_cold_summary(
        self,
        summary_history: List[str],
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        使用 LLM 生成冷区摘要

        Args:
            summary_history: 历史摘要
            messages: 原始消息

        Returns:
            LLM 生成的摘要
        """
        context_parts: List[str] = []

        if summary_history:
            context_parts.append('历史摘要:\n' + '\n'.join(summary_history[-3:]))

        if messages:
            msg_summary = self._extract_message_highlights(messages)
            context_parts.append('关键对话:\n' + msg_summary)

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
            response = await self.llm_service.generate(prompt)
            return str(response).strip()[:500]
        except Exception as e:
            logger.warning(f"LLM 冷区摘要生成失败: {e}")
            return self._generate_simple_cold_summary(summary_history, messages)

    def _generate_simple_cold_summary(
        self,
        summary_history: List[str],
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        生成简单冷区摘要（无 LLM）

        Args:
            summary_history: 历史摘要
            messages: 原始消息

        Returns:
            简单摘要文本
        """
        parts: List[str] = []

        if summary_history:
            parts.append(f'包含 {len(summary_history)} 个历史阶段')

        if messages:
            user_count = sum(1 for m in messages if m.get('role') == 'user')
            assistant_count = sum(1 for m in messages if m.get('role') == 'assistant')
            parts.append(f'用户提问 {user_count} 次，助手回复 {assistant_count} 次')

            if user_count > 0:
                first_user_msg = next(
                    (m for m in messages if m.get('role') == 'user'),
                    None
                )
                if first_user_msg:
                    content = first_user_msg.get('content', '')[:50]
                    parts.append(f'始于: {content}...')

        return ' | '.join(parts) if parts else ''

    def _extract_message_highlights(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        提取消息亮点

        Args:
            messages: 消息列表

        Returns:
            亮点文本
        """
        highlights: List[str] = []

        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')

            if role == 'user':
                content = content[:100]
                highlights.append(f'用户: {content}')

            if len(highlights) >= 5:
                break

        return '\n'.join(highlights)

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
            zone_type: 区域类型 ('warm' 或 'cold')
            token_calculator: Token 计算器

        Returns:
            预估的摘要 Token 数
        """
        original = token_calculator.count_messages_tokens(messages)

        if zone_type == 'warm':
            return min(
                self.config.max_warm_summary_tokens,
                int(original * 0.3)
            )
        elif zone_type == 'cold':
            return min(
                self.config.max_cold_summary_tokens,
                int(original * 0.1)
            )

        return int(original * 0.2)

    def format_warm_summary_for_context(
        self,
        summary: StructuredSummary,
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        格式化温区摘要用于上下文注入

        Args:
            summary: 结构化摘要
            messages: 原始消息（可选，用于附加信息）

        Returns:
            格式化的摘要文本
        """
        lines: List[str] = []

        if messages:
            lines.append(f'共 {len(messages)} 条历史消息')

        if summary.topics:
            lines.append(f'涉及技术: {", ".join(sorted(summary.topics))}')

        if summary.decisions:
            lines.append('关键决策:')
            for d in summary.decisions[:3]:
                lines.append(f'  - {d}')

        if summary.entities:
            lines.append(f'相关资源: {", ".join(summary.entities[:5])}')

        if summary.actions:
            lines.append('待办事项:')
            for a in summary.actions[:3]:
                lines.append(f'  - {a}')

        if messages and len(messages) > 1:
            first_msg = messages[0].get('content', '')[:80]
            last_msg = messages[-1].get('content', '')[:80]
            lines.append(f'起始: {first_msg}...')
            lines.append(f'结束: {last_msg}...')

        return '\n'.join(lines)