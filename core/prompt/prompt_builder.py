"""
PromptBuilder 统一入口

核心职责：
1. 管理所有 prompt 模块
2. 按静态/动态边界组装
3. 支持缓存友好输出
4. 提供统一调用入口

接口约定：
- build_for_chatbot() -> (system_prompt, user_prompt, tokens)
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
    ToolsSchemaSection,
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
            message="帮我生成 UI 测试",
            intent="generate_ui_test",
            knowledge=[],
            tools=tools_schema,
            skills=skills_data,
            session_id="xxx",
            user_id="1"
        )
        
        system_prompt = prompts["system_prompt"]
        user_prompt = prompts["user_prompt"]
    
    Reference: docs/2026/04/01/prompt_dynamic_assembly_design.md
    """
    
    CACHE_BOUNDARY_MARKER = "<!-- CACHE_BOUNDARY -->"
    
    def __init__(
        self,
        context_store=None,
        model_name: str = "gpt-4"
    ):
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
            self.token_calc = TokenCalculator(model_name=model_name)
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
            ToolsSchemaSection(),
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
            return self.token_calc.count_tokens(text)
        return len(text) // 4
    
    def build_user_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, int]:
        """
        构建 user prompt
        
        Args:
            message: 用户消息
            context: 上下文信息
            
        Returns:
            (prompt_text, token_count)
        """
        prompt = f"## 用户请求\n\n{message}"
        
        if context:
            additional_info = context.get("additional_user_context")
            if additional_info:
                prompt += f"\n\n## 补充信息\n\n{additional_info}"
        
        token_count = self._count_tokens(prompt)
        
        return prompt, token_count
    
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
        message: str,
        intent: str,
        knowledge: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        skills: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        environment: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        为 ChatbotAgent 构建 prompt
        
        Args:
            message: 用户消息
            intent: 检测到的意图
            knowledge: 知识库检索结果
            tools: 可用工具 schema
            skills: 已安装 skills
            session_id: 会话 ID
            user_id: 用户 ID
            environment: 环境信息
            conversation_history: 对话历史
            
        Returns:
            {
                "system_prompt": str,
                "user_prompt": str,
                "system_prompt_tokens": int,
                "user_prompt_tokens": int,
                "history_tokens": dict
            }
        """
        logger.debug(f"[PromptBuilder] build_for_chatbot: intent={intent}, skills={len(skills)}, tools={len(tools)}, knowledge={len(knowledge)}")
        
        optimized_history = []
        history_token_info = {}
        
        if self.context_store and session_id and user_id:
            logger.debug(f"[PromptBuilder] 调用 TokenEconomicsContextStore...")
            try:
                optimized_history = self.context_store.get_messages_for_llm(
                    session_id=session_id,
                    user_id=user_id
                )
                logger.debug(f"[PromptBuilder] ContextStore返回: {len(optimized_history)}条优化历史")
                
                budget_status = self.context_store.check_budget(
                    session_id=session_id,
                    user_id=user_id
                )
                logger.debug(f"[PromptBuilder] Token预算状态: {budget_status.status.value}, 已用={budget_status.used_tokens}")
                
                history_token_info = {
                    "total": budget_status.used_tokens,
                    "hot": budget_status.tier_breakdown.get("hot", 0),
                    "warm": budget_status.tier_breakdown.get("warm", 0),
                    "cold": budget_status.tier_breakdown.get("cold", 0)
                }
                logger.debug(f"[PromptBuilder] 分层Token: hot={history_token_info['hot']}, warm={history_token_info['warm']}, cold={history_token_info['cold']}")
            except Exception as e:
                logger.warning(f"[PromptBuilder] ContextStore调用失败: {e}")
        else:
            logger.debug(f"[PromptBuilder] 跳过ContextStore: context_store={self.context_store is not None}, session={session_id}, user={user_id}")
        
        context = {
            "intent": intent,
            "knowledge": knowledge,
            "available_tools": tools,
            "installed_skills": skills,
            "optimized_history": optimized_history,
            "conversation_history": conversation_history or [],
            "history_token_info": history_token_info,
            "include_conversation_history": True,
            "include_tools_schema": bool(tools),
            "include_skills": True,
            **(environment or {})
        }
        
        logger.debug(f"[PromptBuilder] 构建上下文完成，调用 build_system_prompt...")
        system_prompt, system_tokens = self.build_system_prompt(context)
        logger.debug(f"[PromptBuilder] System prompt构建完成: tokens={system_tokens}")
        
        user_prompt, user_tokens = self.build_user_prompt(message, context)
        logger.debug(f"[PromptBuilder] User prompt构建完成: tokens={user_tokens}")
        
        logger.debug(f"[PromptBuilder] ========== Prompt构建完成 ==========")
        logger.debug(f"[PromptBuilder] 总Token: system={system_tokens}, user={user_tokens}, history={history_token_info.get('total', 0)}")
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "system_prompt_tokens": system_tokens,
            "user_prompt_tokens": user_tokens,
            "history_tokens": history_token_info
        }
    
    def build_for_tool_execution(
        self,
        tool_name: str,
        tool_description: str,
        original_message: str,
        tool_result: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        为工具执行后的解释构建 prompt
        
        Args:
            tool_name: 工具名称
            tool_description: 工具描述
            original_message: 用户原始消息
            tool_result: 工具执行结果
            
        Returns:
            {"system_prompt": str, "user_prompt": str}
        """
        system_prompt = """你是测试助手，负责解释工具执行结果。

解释要求：
1. 简洁说明工具执行了什么
2. 总结关键结果
3. 如果有错误，说明原因和建议
4. 不要前言和后语"""
        
        user_prompt = f"""用户原始请求: {original_message}

执行工具: {tool_name}
工具描述: {tool_description}

执行结果:
{tool_result}

请根据工具执行结果，生成一个简洁的自然语言回复。"""
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }


_global_prompt_builder: Optional[PromptBuilder] = None
_global_prompt_builder_lock = threading.Lock()


def get_prompt_builder(
    context_store=None,
    model_name: str = "gpt-4",
    force_new: bool = False
) -> PromptBuilder:
    """
    获取 PromptBuilder（线程安全单例）
    """
    if force_new:
        return PromptBuilder(context_store=context_store, model_name=model_name)
    
    global _global_prompt_builder
    with _global_prompt_builder_lock:
        if _global_prompt_builder is None:
            _global_prompt_builder = PromptBuilder(context_store=context_store, model_name=model_name)
    return _global_prompt_builder