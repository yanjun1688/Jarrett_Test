"""
PromptBuilder 统一入口

核心职责：
1. 管理所有 prompt 模块
2. 按静态/动态边界组装
3. 支持缓存友好输出
4. 提供统一调用入口

接口约定：
- build_for_chatbot() -> {"system_prompt": str, "system_prompt_tokens": int}
- build_system_prompt() -> (prompt, token_count)
- CACHE_BOUNDARY_MARKER: 缓存边界标记

Reference: docs/2026/04/01/prompt_dynamic_assembly_design.md
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import threading

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

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Prompt 动态组装器
    
    核心职责：
    1. 管理所有 prompt 模块
    2. 按静态/动态边界组装
    3. 支持缓存友好输出
    4. 提供统一调用入口
    
    缓存边界设计：
    - 静态部分（宪法）：不变或极少变化，可被 API 层缓存
    - 动态部分（政策）：每次请求可能不同，不缓存
    
    使用示例：
        builder = PromptBuilder()

        prompts = builder.build_for_chatbot(
            tools=tools_schema,
            skills=skills_data,
            environment={"test_type": "api"},
        )

        system_prompt = prompts["system_prompt"]
    
    Reference: docs/2026/04/01/prompt_dynamic_assembly_design.md
    """
    
    CACHE_BOUNDARY_MARKER = "<!-- CACHE_BOUNDARY -->"
    
    def __init__(
        self,
        context_store: Optional[Any] = None,
        model_name: str = "gpt-4"
    ) -> None:
        """
        初始化 Prompt 构建器
        
        Args:
            context_store: TokenEconomicsContextStore 实例（可选）
            model_name: 模型名称
        """
        self.context_store = context_store
        self.model_name = model_name
        
        try:
            from core.context.token_economics import TokenCalculator
            self.token_calc: Optional[TokenCalculator] = TokenCalculator(model_name=model_name)
        except ImportError:
            logger.warning("TokenCalculator not found, token counting disabled")
            self.token_calc = None
        
        self._static_sections: List[PromptSection] = [
            IdentitySection(),
            BehaviorRulesSection(),
            RiskActionsSection(),
            ToolUsageGrammarSection(),
            ToneAndStyleSection(),
            OutputEfficiencySection(),
        ]
        
        self._dynamic_sections: List[PromptSection] = [
            KnowledgeContextSection(),
            SkillsRegistrySection(),
            ConversationHistorySection(),
            EnvironmentInfoSection(),
        ]
        
        self._static_cache: Optional[str] = None
        self._lock = threading.Lock()
    
    def build_system_prompt(
        self,
        context: Dict[str, Any],
        include_boundary_marker: bool = True
    ) -> Tuple[str, int]:
        """
        构建 system prompt
        
        Args:
            context: 上下文信息
            include_boundary_marker: 是否包含缓存边界标记
            
        Returns:
            (prompt_text, token_count)
        """
        logger.debug(f"[PromptBuilder.build_system_prompt] 开始构建，boundary_marker={include_boundary_marker}")
        
        static_part = self._get_static_part()
        logger.debug(f"[PromptBuilder.build_system_prompt] 静态部分获取完成，length={len(static_part)}")
        
        dynamic_part = self._render_dynamic_part(context)
        logger.debug(f"[PromptBuilder.build_system_prompt] 动态部分渲染完成，length={len(dynamic_part)}")
        
        if include_boundary_marker:
            full_prompt = (
                static_part +
                "\n\n" +
                self.CACHE_BOUNDARY_MARKER +
                "\n\n" +
                dynamic_part
            )
            logger.debug(f"[PromptBuilder.build_system_prompt] 已添加缓存边界标记")
        else:
            full_prompt = static_part + "\n\n" + dynamic_part
        
        token_count = self._count_tokens(full_prompt)
        logger.debug(f"[PromptBuilder.build_system_prompt] System prompt总Token: {token_count}")
        
        return full_prompt, token_count
    
    def _get_static_part(self) -> str:
        """获取静态部分（线程安全缓存）"""
        with self._lock:
            if self._static_cache is None:
                logger.debug(f"[PromptBuilder._get_static_part] 缓存未命中，重新渲染静态部分...")
                self._static_cache = self._render_static_part()
                logger.debug(f"[PromptBuilder._get_static_part] 静态部分已缓存，length={len(self._static_cache)}")
            return self._static_cache
    
    def _render_static_part(self) -> str:
        """渲染静态部分"""
        sections = []
        for section in self._static_sections:
            if section.should_include({}):
                rendered = section.render({})
                if rendered.strip():
                    sections.append(rendered)
        return "\n\n".join(sections)
    
    def _render_dynamic_part(self, context: Dict[str, Any]) -> str:
        """渲染动态部分"""
        sections = []
        included = []
        skipped = []
        for section in self._dynamic_sections:
            if section.should_include(context):
                rendered = section.render(context)
                if rendered.strip():
                    sections.append(rendered)
                    included.append(section.name)
                else:
                    skipped.append(f"{section.name}(空)")
            else:
                skipped.append(section.name)
        
        intent = context.get("intent", "unknown")
        logger.info(
            f"[PromptBuilder] 动态渲染 intent={intent}: "
            f"包含={included}, 跳过={skipped}"
        )
        return "\n\n".join(sections)
    
    def _count_tokens(self, text: str) -> int:
        """计算 Token 数量"""
        if self.token_calc:
            return int(self.token_calc.count_tokens(text))
        return len(text) // 4

    def get_static_part_for_cache(self) -> str:
        """
        获取静态部分用于 API 缓存
        
        Returns:
            静态部分内容
        """
        return self._get_static_part()
    
    def invalidate_static_cache(self) -> None:
        """清除静态缓存（线程安全）"""
        with self._lock:
            self._static_cache = None
    
    def build_for_chatbot(
        self,
        tools: List[Dict[str, Any]],
        skills: List[Dict[str, Any]],
        environment: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        为 ChatbotAgent 构建 prompt

        Args:
            tools: 可用工具 schema
            skills: 已安装 skills
            environment: 环境信息 (test_type, project_id, include_conversation_history 等)

        Returns:
            {
                "system_prompt": str,
                "system_prompt_tokens": int,
            }
        """
        logger.debug(f"[PromptBuilder] build_for_chatbot: skills={len(skills)}, tools={len(tools)}")

        context = {
            "knowledge": [],
            "available_tools": tools,
            "installed_skills": skills,
            "include_skills": True,
            **(environment or {})
        }

        logger.debug(f"[PromptBuilder] 构建上下文完成，调用 build_system_prompt...")
        system_prompt, system_tokens = self.build_system_prompt(context)
        logger.debug(f"[PromptBuilder] System prompt构建完成: tokens={system_tokens}")

        return {
            "system_prompt": system_prompt,
            "system_prompt_tokens": system_tokens,
        }
    


_global_prompt_builder: Optional[PromptBuilder] = None
_global_prompt_builder_lock = threading.Lock()


def get_prompt_builder(
    context_store: Any = None,
    model_name: str = "gpt-4",
    force_new: bool = False
) -> PromptBuilder:
    """
    获取 PromptBuilder（线程安全单例）

    支持延迟注入 context_store：首次创建时可不传，后续调用传入时自动更新。
    这避免了单例创建顺序导致 context_store 为 None 的问题。
    """
    if force_new:
        return PromptBuilder(context_store=context_store, model_name=model_name)
    
    global _global_prompt_builder
    with _global_prompt_builder_lock:
        if _global_prompt_builder is None:
            _global_prompt_builder = PromptBuilder(context_store=context_store, model_name=model_name)
        elif context_store is not None and _global_prompt_builder.context_store is None:
            # 延迟注入：单例已创建但 context_store 为空，后续传入时更新
            _global_prompt_builder.context_store = context_store
            logger.info('[PromptBuilder] context_store 延迟注入完成')
        elif context_store is not None and _global_prompt_builder.context_store is not context_store:
            # context_store 实例变更（如测试场景），同步更新
            _global_prompt_builder.context_store = context_store
            logger.info('[PromptBuilder] context_store 已更新为新实例')
    return _global_prompt_builder