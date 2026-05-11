"""
Prompt 动态组装模块

提供统一的 Prompt 组装入口，支持：
- 模块化架构（静态宪法 + 动态政策）
- 缓存边界管理
- Skills 能力注入
- Token 统计

核心组件：
- PromptBuilder: 统一组装入口
- PromptSection: 模块基类
- 各具体 Section 实现

接口约定：
- build_for_chatbot() -> {"system_prompt": str, "system_prompt_tokens": int}
- CACHE_BOUNDARY_MARKER: 缓存边界标记

Reference: docs/2026/04/01/prompt_dynamic_assembly_design.md
"""

from .sections import (
    PromptSection,
    IdentitySection,
    BehaviorRulesSection,
    RiskActionsSection,
    ToolUsageGrammarSection,
    ToneAndStyleSection,
    OutputEfficiencySection,
    KnowledgeContextSection,
    SkillsRegistrySection,
    ConversationHistorySection,
    EnvironmentInfoSection,
)

from .prompt_builder import (
    PromptBuilder,
    get_prompt_builder,
)

__all__ = [
    "PromptSection",
    "IdentitySection",
    "BehaviorRulesSection",
    "RiskActionsSection",
    "ToolUsageGrammarSection",
    "ToneAndStyleSection",
    "OutputEfficiencySection",
    "KnowledgeContextSection",
    "SkillsRegistrySection",
    "ConversationHistorySection",
    "EnvironmentInfoSection",
    "PromptBuilder",
    "get_prompt_builder",
]