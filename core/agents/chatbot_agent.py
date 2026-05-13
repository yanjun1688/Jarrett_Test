"""
Chatbot Agent - ReAct 架构

多轮工具调用循环（ReAct），LLM 自主决定工具选择和调用顺序。
不再有单轮 function calling + 后置拦截。

流程：
    用户消息
        → 构建 prompt（system prompt + skills 注入 + 对话历史 + tool definitions）
        → ReActEngine.run（多轮循环）
        → 返回最终结果
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
import logging
import sys

from core.agents.base_agent import BaseAgent
from core.agents.react_engine import ReActEngine
from core.agents.skill_loader import SkillLoader
from core.tools.base_tool import ToolRegistry
from core.tools.bash_tool import BashTool
from core.tools.mcp_tool_adapter import MCPToolAdapter
from core.agents.llm.base_llm import BaseLLMService
from core.prompt import get_prompt_builder
from core.services.conversation_service import get_token_economics_store
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

# test_type 白名单：不同测试类型可用的工具集
TOOL_WHITELIST: Dict[str, Set[str]] = {
    "ui":  {"generate", "save", "bash", "execute_test",
            "query_knowledge", "query_test_scripts"},
    "api": {"generate", "save", "bash", "execute_test",
            "query_knowledge", "query_test_scripts"},
    "prd": {"generate", "save", "bash", "query_knowledge"},
}


class ChatbotAgent(BaseAgent):
    """Chatbot Agent - ReAct 架构"""

    def __init__(
        self,
        llm_service: BaseLLMService,
        knowledge_rag_agent: Any = None,
        tool_orchestrator: Any = None,
        config: Optional[Dict[str, Any]] = None,
        context_store: Any = None,
    ):
        super().__init__(agent_id="chatbot_agent", config=config)

        self.llm_service = llm_service
        self.knowledge_rag_agent = knowledge_rag_agent

        model_name = config.get("model_name", "gpt-4") if config else "gpt-4"
        max_iters = min(int((config or {}).get("max_iterations", 10)), 15)

        self.context_store = context_store or get_token_economics_store(
            model_name=model_name, llm_service=llm_service
        )
        self.prompt_builder = get_prompt_builder(
            context_store=self.context_store, model_name=model_name
        )

        # 唯一注册表
        self.registry = ToolRegistry()
        # 技能加载器（只扫描 skills/，.agents/skills/ 归 opencode 管理）
        self.skill_loader = SkillLoader(skill_dirs=["skills"])
        # ReAct 引擎
        self.react = ReActEngine(
            registry=self.registry,
            llm_service=llm_service,
            max_iterations=max_iters,
        )

        self._init_tools()

        # Legacy: accept tool_orchestrator for backward compat, but don't use it
        logger.info(f"ChatbotAgent initialized with ReAct architecture (model={model_name})")

    def _filter_tool_definitions(self, test_type: Optional[str]) -> List[Dict[str, Any]]:
        """根据 test_type 白名单过滤工具定义"""
        definitions: List[Dict[str, Any]] = self.registry.list_definitions()
        if not test_type:
            return definitions
        allowed = TOOL_WHITELIST.get(test_type, set())
        return [
            t for t in definitions
            if t.get("function", {}).get("name") in allowed
        ]

    def _init_tools(self) -> None:
        """注册所有内置和 MCP 工具到 ToolRegistry"""
        from core.tools.chatbot import (
            GenerateTool,
            SaveTool,
            ExecuteTestTool,
            ExecutePendingTestsTool,
            QueryKnowledgeTool,
            QueryTestScriptsTool,
            InstallSkillTool,
            LoadSkillTool,
            QueryProjectTool,
        )

        tools = [
            GenerateTool(llm_service=self.llm_service),
            SaveTool(),
            ExecuteTestTool(),
            ExecutePendingTestsTool(),
            QueryKnowledgeTool(knowledge_rag_agent=self.knowledge_rag_agent),
            QueryTestScriptsTool(),
            QueryProjectTool(),
            InstallSkillTool(),
            LoadSkillTool(skill_loader=self.skill_loader),
        ]
        for t in tools:
            self.registry.register(t)

        # BashTool
        self.registry.register(BashTool())
        logger.info(f"Registered {self.registry.count()} builtin tools")

    async def initialize(self) -> None:
        if self._state.get("status") == "ready":
            return
        if hasattr(self.llm_service, "initialize"):
            await self.llm_service.initialize()
        await self._init_mcp_tools()
        self.update_state("ready")

    async def _init_mcp_tools(self) -> None:
        from core.agents.capability.mcp_lifespan import global_mcp_manager, load_servers_from_settings
        if not global_mcp_manager._initialized:
            try:
                load_servers_from_settings()
                await global_mcp_manager.initialize()
            except Exception as e:
                logger.warning(f"MCP init failed: {e}")
                return
        if global_mcp_manager.is_connected("playwright"):
            for t in global_mcp_manager.get_tools("playwright"):
                self.registry.register(MCPToolAdapter("playwright", t))
            logger.info(f"Registered {len(global_mcp_manager.get_tools('playwright'))} MCP tools")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        message: str = input_data["message"]
        conversation_id: Optional[str] = input_data.get("conversation_id")
        user_id: Any = input_data.get("user_id")
        project_id: Optional[int] = input_data.get("project_id")
        test_type: Optional[str] = input_data.get("test_type")

        logger.info('[ChatBot] ========== 开始处理消息 ==========')
        logger.info(f'[ChatBot] 会话ID: {conversation_id}, test_type: {test_type}')

        # Build context — 每次请求重新 discover，确保 install_skill 后立即感知新 skill
        skill_infos = self.skill_loader.discover()
        skills_data = [
            {"name": s.name, "description": s.description,
             "allowed_tools": s.allowed_tools}
            for s in skill_infos
        ]
        tool_defs = self._filter_tool_definitions(test_type)

        environment: Dict[str, Any] = {
            "include_conversation_history": False,
            "platform": f"{sys.platform} ({ 'PowerShell' if sys.platform == 'win32' else 'bash' })",
        }
        if test_type:
            environment["test_type"] = test_type
        if project_id:
            environment["project_id"] = project_id

        prompts = await sync_to_async(self.prompt_builder.build_for_chatbot)(
            tools=tool_defs,
            skills=skills_data,
            environment=environment,
        )

        # Get history (before writing user message, to avoid duplication in prompt)
        history: List[Dict[str, Any]] = []
        if self.context_store and conversation_id and user_id:
            try:
                history = await sync_to_async(self.context_store.get_messages_for_llm)(
                    session_id=str(conversation_id), user_id=str(user_id)
                )
            except Exception as e:
                logger.warning(f"Get history failed: {e}")

        # Write user message to store (after getting history)
        if self.context_store and conversation_id and user_id:
            try:
                await sync_to_async(self.context_store.append_message)(
                    session_id=str(conversation_id), user_id=str(user_id),
                    role="user", content=message,
                )
            except Exception as e:
                logger.warning(f"Write user msg failed: {e}")

        system_prompt = prompts["system_prompt"] if isinstance(prompts, dict) else str(prompts)

        # Run ReAct loop
        result = await self.react.run(message, system_prompt, history, tool_defs)

        # Write assistant message
        if self.context_store and conversation_id and user_id and result.response:
            try:
                await sync_to_async(self.context_store.append_message)(
                    session_id=str(conversation_id), user_id=str(user_id),
                    role="assistant", content=result.response,
                )
            except Exception as e:
                logger.warning(f"Write assistant msg failed: {e}")

        logger.info('[ChatBot] ========== 处理完成 ==========')
        response: Dict[str, Any] = {
            "success": True,
            "message": result.response,
            "tool_used": result.tool_calls_made > 0,
            "iterations": result.iterations,
            "stopped_reason": result.stopped_reason,
            "conversation_id": conversation_id,
        }
        if result.options:
            response["options"] = result.options
        return response

    # ── Legacy ──

    async def cleanup_mcp(self) -> None:
        """MCP 连接清理（应用级管理，不再由 Agent 管理）"""
        logger.info("[ChatbotAgent] MCP 状态已重置（连接由应用级管理）")

    async def cleanup(self) -> None:
        """Cleanup agent resources"""
        logger.info("Cleaning up ChatbotAgent")
        if hasattr(self.llm_service, 'cleanup'):
            await self.llm_service.cleanup()
        self.update_state("cleanup")
        logger.info("ChatbotAgent cleanup complete")
