"""
Chatbot Agent - Native Function Calling 架构

所有请求统一走一次 LLM + function calling，LLM 自行判断该直接回复还是调工具。
不再有独立的意图分类步骤。

流程：
    用户消息
        → 构建 prompt（system prompt + 对话历史 + tool definitions）
        → LLM.generate_with_tools（一次调用）
        → 如果有 tool_calls → 执行 tool → 返回结果
        → 如果没有 tool_calls → 直接返回 LLM 的文本回复
"""
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import logging
import re
import os
import json

from core.agents.base_agent import BaseAgent
from core.agents.tool_orchestrator import ToolOrchestrator
from core.agents.rag.knowledge_rag_agent import KnowledgeRAGAgent
from core.agents.llm.base_llm import BaseLLMService
from core.agents.capability import (
    global_capability_registry,
    global_capability_injector
)
from core.prompt import get_prompt_builder
from core.context.token_economics import TokenEconomicsContextStore, TokenCalculator

logger = logging.getLogger(__name__)


class ChatbotAgent(BaseAgent):
    """
    Chatbot Agent - Native Function Calling 架构

    所有请求统一走 LLM + function calling，LLM 自行判断：
    - 直接回复文本
    - 调用内置工具（generate_api_test, execute_test 等）
    - 调用 skill（run_skill__<name>）
    """

    def __init__(
        self,
        llm_service: BaseLLMService,
        knowledge_rag_agent: Optional[KnowledgeRAGAgent] = None,
        tool_orchestrator: Optional[ToolOrchestrator] = None,
        config: Optional[Dict[str, Any]] = None,
        context_store_dir: Optional[Path] = None
    ):
        """
        Initialize Chatbot Agent

        Args:
            llm_service: LLM service for response generation
            knowledge_rag_agent: Knowledge RAG agent for knowledge retrieval
            tool_orchestrator: Tool orchestrator for tool execution
            config: Agent configuration
            context_store_dir: Directory for TokenEconomicsContextStore
        """
        super().__init__(agent_id="chatbot_agent", config=config)

        self.llm_service = llm_service
        self.knowledge_rag_agent = knowledge_rag_agent
        self._internal_logs: List[Dict[str, Any]] = []
        self._execution_logger: Optional[Any] = None

        self.tool_orchestrator = tool_orchestrator if tool_orchestrator is not None else ToolOrchestrator()

        model_name = config.get("model_name", "gpt-4") if config else "gpt-4"

        self.context_store_dir = context_store_dir or Path("context_data")
        if not self.context_store_dir.exists():
            self.context_store_dir.mkdir(parents=True, exist_ok=True)

        self.context_store = TokenEconomicsContextStore(
            root_dir=self.context_store_dir,
            model_name=model_name
        )

        self.prompt_builder = get_prompt_builder(context_store=self.context_store, model_name=model_name)

        self.capability_registry = global_capability_registry
        self.capability_injector = global_capability_injector
        
        self._register_chatbot_tools()
        self._register_capabilities()
        self._register_skills()

        logger.info(f"ChatbotAgent initialized with Native Function Calling and MCP (model={model_name})")

    async def initialize(self) -> None:
        """Initialize the agent"""
        logger.info("Initializing ChatbotAgent")
        
        if self._state.get("status") == "ready":
            logger.info("ChatbotAgent already initialized, skipping")
            return
        
        if hasattr(self.llm_service, 'initialize'):
            await self.llm_service.initialize()
        
        from core.agents.capability.mcp_lifespan import global_mcp_manager, load_servers_from_settings
        
        # 如果 MCP Manager 未初始化，尝试初始化（兼容 runserver 和直接运行场景）
        if not global_mcp_manager._initialized:
            logger.info("[ChatbotAgent] MCP Manager 未初始化，尝试初始化...")
            try:
                load_servers_from_settings()
                await global_mcp_manager.initialize()
                logger.info("[ChatbotAgent] MCP Manager 初始化完成")
            except Exception as e:
                logger.warning(f"[ChatbotAgent] MCP Manager 初始化失败: {e}")
        
        if global_mcp_manager.is_connected("playwright"):
            self._mcp_tools = global_mcp_manager.get_tools("playwright")
            self._mcp_initialized = True
            logger.info(f"[ChatbotAgent] Playwright MCP 已连接（应用级），提供 {len(self._mcp_tools)} 个工具")
        else:
            self._mcp_tools = []
            self._mcp_initialized = False
            logger.warning("[ChatbotAgent] Playwright MCP 未连接，浏览器功能可能不可用")

        self.update_state("ready")
        logger.info("ChatbotAgent initialization complete")

    def _register_chatbot_tools(self):
        """注册 ChatBot 可用的工具"""
        from core.tools.chatbot import (
            GenerateAPITestTool,
            GenerateUITestTool,
            ExecuteTestTool,
            ExecutePendingTestsTool,
            QueryKnowledgeTool,
            QueryTestScriptsTool,
            InstallSkillTool,
            RunSkillTool
        )

        api_test_tool = GenerateAPITestTool(llm_service=self.llm_service)
        self.tool_orchestrator.register_tool(api_test_tool)
        logger.info(f"Registered tool: {api_test_tool.name}")

        ui_test_tool = GenerateUITestTool(llm_service=self.llm_service)
        self.tool_orchestrator.register_tool(ui_test_tool)
        logger.info(f"Registered tool: {ui_test_tool.name}")

        execute_tool = ExecuteTestTool()
        self.tool_orchestrator.register_tool(execute_tool)
        logger.info(f"Registered tool: {execute_tool.name}")

        execute_pending_tool = ExecutePendingTestsTool()
        self.tool_orchestrator.register_tool(execute_pending_tool)
        logger.info(f"Registered tool: {execute_pending_tool.name}")

        knowledge_tool = QueryKnowledgeTool(knowledge_rag_agent=self.knowledge_rag_agent)
        self.tool_orchestrator.register_tool(knowledge_tool)
        logger.info(f"Registered tool: {knowledge_tool.name}")

        query_test_scripts_tool = QueryTestScriptsTool()
        self.tool_orchestrator.register_tool(query_test_scripts_tool)
        logger.info(f"Registered tool: {query_test_scripts_tool.name}")

        install_skill_tool = InstallSkillTool()
        self.tool_orchestrator.register_tool(install_skill_tool)
        logger.info(f"Registered tool: {install_skill_tool.name}")

        run_skill_tool = RunSkillTool(llm_service=self.llm_service)
        self.tool_orchestrator.register_tool(run_skill_tool)
        logger.info(f"Registered tool: {run_skill_tool.name}")

    def _register_capabilities(self):
        """注册已加载的能力（工具）"""
        for tool in self.tool_orchestrator.get_available_tools():
            self.capability_registry.register_tool(
                name=tool["name"],
                description=tool["description"],
                version=tool.get("version", "1.0.0"),
                parameters=tool.get("schema", {}).get("properties", {})
            )

        logger.info(
            f"Registered capabilities: "
            f"{len(self.capability_registry.get_all_skills())} skills, "
            f"{len(self.capability_registry.get_all_tools())} tools"
        )

    def _register_skills(self):
        """注册技能到能力系统"""
        try:
            from core.agents.skill_loader import SkillLoader
            loader = SkillLoader()
            available = loader.scan_skills()

            for skill_name in available:
                skill_path = loader.skill_dir / skill_name
                if skill_path.is_symlink():
                    continue

                skill = loader.load_skill(skill_name)
                if skill:
                    self.capability_registry.register_skill(skill)

            logger.info(
                f"Registered skills: {len(self.capability_registry.get_all_skills())}"
            )
        except Exception as e:
            logger.warning(f"Failed to load skills for capability registry: {e}")

    def _get_installed_skill_names(self) -> List[str]:
        """获取已安装的 skill 名称列表"""
        try:
            from core.agents.skill_loader import SkillLoader
            loader = SkillLoader()
            return loader.scan_skills()
        except Exception as e:
            logger.warning(f"Failed to get installed skills: {e}")
            return []

    def _get_all_tool_definitions(self) -> List[Dict]:
        """
        生成 OpenAI function calling 格式的 tool definitions。

        - 内置 tools 从 tool_orchestrator 获取（排除 run_skill，skill 单独注册）
        - Skills 从 capability_registry 获取，每个生成 run_skill__<name>

        Returns:
            List[Dict]: OpenAI function calling 格式的 tool definitions
        """
        definitions = []

        # 内置 tools（排除 run_skill，因为 skill 会单独注册）
        for tool in self.tool_orchestrator.get_available_tools():
            if tool["name"] == "run_skill":
                continue
            # tool["schema"] 是完整的 OpenAI function 格式，需要提取 parameters
            schema = tool.get("schema", {})
            parameters = schema.get("function", {}).get("parameters", {}) if "function" in schema else schema
            definitions.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": parameters
                }
            })

        # Skills：每个 skill 生成一个 run_skill__<name> 的 function definition
        for skill in self.capability_registry.get_all_skills():
            safe_name = skill.name.replace("-", "_")
            
            # Skill 描述优化（添加适用场景提示）
            skill_descriptions = {
                "agent-browser": "浏览器自动化（备选方案）。当 MCP 浏览器工具未连接或执行失败时自动使用。MCP 工具优先级更高，此 Skill 作为 fallback。",
                "cmd-executor": "命令执行 Skill。适用于保存文件、下载内容、执行本地命令。",
                "testcase-generator": "测试用例生成 Skill。适用于生成测试用例、测试点分析。",
            }
            
            description = skill_descriptions.get(skill.name, skill.description)
            
            definitions.append({
                "type": "function",
                "function": {
                    "name": f"run_skill__{safe_name}",
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_input": {
                                "type": "string",
                                "description": "用户的任务需求"
                            }
                        },
                        "required": ["user_input"]
                    }
                }
            })
        
        # MCP Tools：添加 Playwright MCP 工具（优先级：浏览器操作首选）
        if self._mcp_initialized and hasattr(self, '_mcp_tools') and self._mcp_tools:
            # MCP 工具描述模板（强调优先级）
            mcp_tool_descriptions = {
                "browser_navigate": "打开指定网页并导航到该地址。\n\n参数：\n- url（必需）：目标网页地址。接受完整URL或可识别的网站名称。\n\n功能：\n- 导航到指定网页\n- 返回页面基本信息（标题、URL）\n\n前提：\n- 需要明确的导航目标",
                "browser_snapshot": "提取当前页面的可访问性快照。\n\n功能：\n- 返回页面的结构化内容（元素、文本、布局）\n- 用于分析页面结构或定位元素\n\n前提：\n- 已打开网页（先调用 browser_navigate）\n\n参数：无必需参数",
                "browser_click": "点击页面上的指定元素。\n\n参数：\n- element（必需）：目标元素定位器\n\n前提：\n- 已打开网页\n- 已定位目标元素",
                "browser_type": "在页面输入框中输入文本。\n\n参数：\n- element（必需）：目标输入框定位器\n- text（必需）：要输入的文本内容\n\n前提：\n- 已打开网页\n- 已定位目标输入框",
            }
            
            for tool in self._mcp_tools:
                tool_name = tool.get("name", "")
                description = mcp_tool_descriptions.get(tool_name, tool.get("description", ""))
                
                definitions.append({
                    "type": "function",
                    "function": {
                        "name": f"mcp__playwright__{tool_name}",
                        "description": description,
                        "parameters": tool.get("input_schema", {})
                    }
                })

        return definitions

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the chatbot agent (Native Function Calling)

        流程：
        1. 构建 tool definitions
        2. 构建 prompt（system prompt + 对话历史）
        3. LLM + function calling（一次调用）
        4. 处理结果：tool_calls → 执行工具；否则直接返回文本

        Args:
            input_data: Input data containing message, context, etc.

        Returns:
            Response dictionary with success, message, tool_used, tool_result
        """
        import time
        start_time = time.time()

        self._internal_logs = []

        from core.services.chatbot_execution_logger import get_chatbot_logger
        conversation_id = input_data.get("conversation_id") or input_data.get("context", {}).get("conversation_id")
        if conversation_id:
            self._execution_logger = get_chatbot_logger(conversation_id)
        else:
            self._execution_logger = None

        if "message" not in input_data:
            raise ValueError("Input must contain 'message' field")

        message = input_data["message"]
        project_id = input_data.get("project_id")
        context = input_data.get("context", {})
        conversation_id = input_data.get("conversation_id") or context.get("conversation_id")
        user_id = context.get("user_id")
        conversation_history = input_data.get("conversation_history") or context.get("conversation_history", [])

        logger.info(f"[ChatBot] ========== 开始处理消息 ==========")
        logger.info(f"[ChatBot] 用户消息: {message}")
        logger.info(f"[ChatBot] 会话ID: {conversation_id}")

        # Step 1: 构建 tool definitions
        tool_definitions = self._get_all_tool_definitions()
        logger.info(f"[ChatBot] Tool definitions: {len(tool_definitions)} 个")

        # Step 2: 构建 prompt（含对话历史）
        # 获取对话历史（从 ContextStore 分层压缩）
        history_messages = []
        if self.context_store and conversation_id and user_id:
            try:
                history_messages = self.context_store.get_messages_for_llm(
                    session_id=str(conversation_id),
                    user_id=str(user_id)
                )
                logger.info(f"[ChatBot] 对话历史: {len(history_messages)} 条（ContextStore）")
            except Exception as e:
                logger.warning(f"[ChatBot] ContextStore 获取失败: {e}")

        if not history_messages and conversation_history:
            history_messages = conversation_history[-10:]  # fallback: 最近10条
            logger.info(f"[ChatBot] 对话历史: {len(history_messages)} 条（fallback）")

        # 构建 system prompt
        system_prompt, sys_tokens = self.prompt_builder.build_system_prompt({})
        logger.info(f"[ChatBot] System prompt: {sys_tokens} tokens")

        # Step 3: LLM + function calling（一次调用）
        llm_start = time.time()
        logger.info(f"[ChatBot] 调用 LLM + function calling...")
        logger.info(f"[ChatBot] Tool names: {[t['function']['name'] for t in tool_definitions]}")
        logger.info(f"[ChatBot] History messages: {len(history_messages)} 条")

        try:
            result = await self.llm_service.generate_with_tools(
                prompt=message,
                tools=tool_definitions,
                system_message=system_prompt,
                conversation_history=history_messages,
            )
            logger.info(f"[ChatBot] LLM 调用完成，耗时: {time.time() - llm_start:.2f}s")
        except Exception as e:
            logger.error(f"[ChatBot] LLM 调用失败: {e}", exc_info=True)
            # 降级：不带 tools 重试一次普通调用
            try:
                logger.info(f"[ChatBot] 降级为普通 LLM 调用（不带 tools）...")
                fallback_response = await self.llm_service.generate(
                    prompt=message,
                    system_message=system_prompt,
                )
                return {
                    "success": True,
                    "message": fallback_response if isinstance(fallback_response, str) else str(fallback_response),
                    "tool_used": False,
                    "tool_result": None,
                    "conversation_id": conversation_id,
                }
            except Exception as e2:
                logger.error(f"[ChatBot] 降级调用也失败: {e2}", exc_info=True)
                return {
                    "success": False,
                    "message": f"LLM 调用失败，请稍后重试",
                    "error": f"LLM 调用失败: {str(e2)}",
                    "tool_used": False,
                    "tool_result": None,
                }

        # Step 4: 处理结果
        tool_calls = result.get("tool_calls")

        if tool_calls:
            logger.info(f"[ChatBot] LLM 决定调用 {len(tool_calls)} 个工具")
            tool_names = [self._extract_tool_call_info(tc)['name'] for tc in tool_calls]
            response = await self._handle_tool_calls(tool_calls, message, user_id=user_id)
        else:
            response_text = result.get("response", "")
            logger.info(f"[ChatBot] LLM 直接回复，长度: {len(response_text)} 字符")
            response = {
                "text": response_text,
                "tool_used": False,
                "tool_result": None,
            }

        # 构建返回结果
        self._state["execution_count"] = self._state.get("execution_count", 0) + 1

        final_result = {
            "success": True,
            "message": response.get("text", ""),
            "tool_used": response.get("tool_used", False),
        }

        tool_result = response.get("tool_result")
        if tool_result:
            final_result["tool_result"] = str(tool_result)

        if self._execution_logger:
            final_result["execution_log_ids"] = self._execution_logger.get_log_ids()

        if conversation_id:
            final_result["conversation_id"] = conversation_id

        logger.info(f"[ChatBot] ========== 处理完成 ==========")
        logger.info(f"[ChatBot] 总耗时: {time.time() - start_time:.2f}s")
        text = response.get('text', '')[:100].replace('\n', ' ').replace('\r', '')
        logger.info(f"[ChatBot] 响应摘要: {text}...")

        return final_result

    def _extract_tool_call_info(self, tc) -> Dict[str, Any]:
        """
        统一提取 tool_call 信息，适配不同 LLM SDK 的返回格式
        
        支持:
        - OpenAI/zhipu/deepseek/qwen: Pydantic 对象 (tc.function.name, tc.function.arguments)
        - Anthropic: 字典格式 (tc['name'], tc['input'])
        
        Args:
            tc: tool_call 对象
        
        Returns:
            dict: {'name': str, 'arguments': dict}
        """
        if hasattr(tc, 'function'):
            func_name = tc.function.name
            func_args_str = tc.function.arguments if hasattr(tc.function, 'arguments') else '{}'
            try:
                func_args = json.loads(func_args_str) if isinstance(func_args_str, str) else func_args_str
            except (json.JSONDecodeError, TypeError):
                func_args = {}
        elif isinstance(tc, dict):
            func_name = tc.get('name', 'unknown')
            func_args = tc.get('input', {})
        else:
            func_name = getattr(tc, 'name', 'unknown')
            func_args = getattr(tc, 'input', {})
        
        return {'name': func_name, 'arguments': func_args if isinstance(func_args, dict) else {}}

    async def _handle_tool_calls(self, tool_calls, message: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        处理 LLM 返回的 tool_calls。

        - run_skill__xxx 格式映射到 run_skill 工具
        - 其他工具直接执行

        Args:
            tool_calls: LLM 返回的 tool_calls 列表
            message: 用户原始消息
            user_id: 用户ID（用于创建执行记录）

        Returns:
            Response dictionary with text, tool_used, tool_result
        """
        all_results = []

        for tc in tool_calls:
            tc_info = self._extract_tool_call_info(tc)
            func_name = tc_info['name']
            func_args = tc_info['arguments']

            logger.info(f"[ToolExec] 执行工具: {func_name}, 参数: {func_args}")

            # 如果是 run_skill__xxx 格式，映射到 run_skill
            if func_name.startswith("run_skill__"):
                skill_name = func_name[len("run_skill__"):].replace("_", "-")
                actual_tool = "run_skill"
                actual_args = {"skill_name": skill_name, "user_input": func_args.get("user_input", message)}
                logger.info(f"[ToolExec] Skill映射: {func_name} -> run_skill(skill_name={skill_name})")
            
            # 如果是 mcp__xxx__yyy 格式，调用 MCP 工具
            elif func_name.startswith("mcp__"):
                parts = func_name.split("__")
                server_name = parts[1]
                tool_name = parts[2]
                
                from core.agents.capability.mcp_lifespan import global_mcp_manager
                
                try:
                    result = await global_mcp_manager.call_tool(server_name, tool_name, func_args)
                    all_results.append({
                        "tool": func_name, 
                        "result": {"success": True, "data": result}
                    })
                    logger.info(f"[ToolExec] MCP 工具执行成功: {func_name}")
                    continue
                except Exception as mcp_error:
                    logger.warning(f"[ToolExec] MCP 工具执行失败: {mcp_error}，尝试 fallback 到 skill")
                    
                    if server_name == "playwright":
                        logger.info(f"[ToolExec] Fallback: 使用 agent-browser skill")
                        fallback_args = {"skill_name": "agent-browser", "user_input": message}
                        if user_id:
                            fallback_args['user_id'] = user_id
                        
                        try:
                            tool_result = await self.tool_orchestrator.execute(
                                "run_skill",
                                execution_logger=self._execution_logger,
                                **fallback_args
                            )
                            all_results.append({"tool": "run_skill__agent_browser (fallback)", "result": tool_result})
                            logger.info(f"[ToolExec] Fallback 成功")
                            continue
                        except Exception as fallback_error:
                            logger.error(f"[ToolExec] Fallback 也失败: {fallback_error}")
                            all_results.append({"tool": func_name, "result": {"success": False, "error": f"MCP 失败: {mcp_error}, Fallback 也失败: {fallback_error}"}})
                            continue
                    
                    all_results.append({"tool": func_name, "result": {"success": False, "error": str(mcp_error)}})
                    continue
            
            else:
                actual_tool = func_name
                actual_args = func_args

            try:
                if user_id and 'user_id' not in actual_args:
                    actual_args['user_id'] = user_id
                tool_result = await self.tool_orchestrator.execute(
                    actual_tool, 
                    execution_logger=self._execution_logger,
                    **actual_args
                )
                logger.info(f"[ToolExec] 工具结果: success={tool_result.get('success')}, error={tool_result.get('error')}, data_keys={list(tool_result.get('data', {}).keys()) if isinstance(tool_result.get('data'), dict) else type(tool_result.get('data'))}")
                all_results.append({"tool": func_name, "result": tool_result})
            except Exception as e:
                logger.error(f"[ToolExec] 工具执行失败: {e}", exc_info=True)
                all_results.append({"tool": func_name, "result": {"success": False, "error": str(e)}})

        # 格式化响应
        if len(all_results) == 1:
            result = all_results[0]["result"]
            tool_name = all_results[0]["tool"]
            if result.get("success"):
                data = result.get("data", {})
                if isinstance(data, dict):
                    # 处理 query_test_scripts 等返回完整结构的数据
                    if "suggestion" in data or "scripts" in data:
                        parts = []
                        if data.get("message"):
                            parts.append(data["message"])
                        if data.get("scripts"):
                            scripts_info = "\n".join([
                                f"  - ID: {s.get('id')}, 类型: {s.get('test_type', 'api')}, 名称: {s.get('name')}"
                                for s in data["scripts"]
                            ])
                            parts.append(f"脚本列表:\n{scripts_info}")
                        if data.get("suggestion"):
                            parts.append(f"建议: {data['suggestion']}")
                        text = "\n\n".join(parts)
                    # 处理 execute_test 返回的执行结果
                    elif "execution_id" in data or ("logs" in data and "script_name" in data):
                        parts = []
                        status_icon = "✅" if data.get("success") else "❌"
                        
                        execution_id = data.get("execution_id")
                        if execution_id:
                            parts.append(f"{status_icon} 测试脚本执行完成: **{data.get('script_name')}**")
                            parts.append(f"- 执行记录ID: `{execution_id}`")
                        else:
                            parts.append(f"{status_icon} 测试脚本执行完成: **{data.get('script_name')}**")
                        
                        parts.append(f"- 脚本类型: `{data.get('script_type', 'unknown')}`")
                        status_text = data.get("status", "success" if data.get("success") else "failed")
                        parts.append(f"- 执行状态: `{status_text}`")
                        
                        if data.get("message"):
                            parts.append(f"- {data.get('message')}")
                        
                        results = data.get("results", [])
                        if results:
                            passed = sum(1 for r in results if r.get("success"))
                            failed = len(results) - passed
                            parts.append(f"- 步骤统计: 共 {len(results)} 步, 通过 {passed}, 失败 {failed}")
                        elif data.get("passed_count") and data.get("failed_count"):
                            parts.append(f"- 步骤统计: 通过 {data.get('passed_count')}, 失败 {data.get('failed_count')}")
                        
                        logs = data.get("logs", "")
                        if logs:
                            logs_preview = logs[:2000] if len(logs) > 2000 else logs
                            parts.append(f"\n**执行日志:**")
                            parts.append(f"```")
                            parts.append(logs_preview)
                            parts.append(f"```")
                            if len(logs) > 2000:
                                parts.append(f"\n_（日志已截取，完整长度: {len(logs)} 字符）_")
                        
                        if data.get("error"):
                            parts.append(f"\n**错误信息:** {data['error']}")
                        
                        text = "\n".join(parts)
                    else:
                        text = data.get("result") or data.get("message") or str(data)
                else:
                    text = str(data)
                
                logger.info(f"[ChatBot] 工具返回文本长度: {len(text)}, tool_name: {tool_name}")
                
                # 智能总结：如果内容过长，调用 LLM 提炼关键信息
                if len(text) > 1500 and "agent-browser" in tool_name:
                    logger.info(f"[ChatBot] 内容过长({len(text)}字符)，调用 LLM 总结...")
                    try:
                        summary = await self.llm_service.generate(
                            prompt=f"用户任务：{message}\n\n页面内容：\n{text[:6000]}\n\n请简要总结关键信息，不超过300字。",
                            system_message="你是信息提取助手，从页面内容中提取用户关心的关键信息。",
                            temperature=0.3,
                            max_tokens=500
                        )
                        text = summary if isinstance(summary, str) else str(summary)
                        logger.info(f"[ChatBot] 总结完成，长度: {len(text)}")
                    except Exception as e:
                        logger.warning(f"[ChatBot] 总结失败: {e}，返回原始内容")
            else:
                text = f"工具 '{tool_name}' 执行失败。\n错误: {result.get('error', '未知错误')}"
        else:
            parts = []
            for r in all_results:
                status = "✓" if r["result"].get("success") else "✗"
                parts.append(f"{status} {r['tool']}")
            text = "\n".join(parts)

        return {
            "text": text,
            "tool_used": True,
            "tool_result": text,
        }

    async def _retrieve_knowledge(
        self,
        query: str,
        project_id: Optional[int] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve knowledge from RAG

        Args:
            query: Search query
            project_id: Project ID for filtering
            top_k: Number of results to retrieve

        Returns:
            List of retrieved knowledge entries
        """
        try:
            from core.agents.rag.knowledge_retriever import KnowledgeRetriever
            from asgiref.sync import sync_to_async

            retriever = KnowledgeRetriever()

            if project_id:
                logger.info(f"[ChatBot] Retrieving knowledge for project {project_id}")
            else:
                logger.info(f"[ChatBot] Retrieving knowledge globally (no project_id)")

            results = await sync_to_async(retriever.search)(
                query, top_k=top_k, project_id=project_id, boost_project=True
            )

            knowledge = []
            for r in results:
                knowledge.append({
                    "content": r.get("content", ""),
                    "document": r.get("content", ""),
                    "metadata": r.get("metadata", {}),
                    "distance": r.get("distance"),
                    "score": 1.0 - (r.get("distance") or 0.0),
                    "_retrieval_metadata": {
                        "retrieved_at": datetime.now().isoformat(),
                        "query": query
                    }
                })

            logger.info(f"Retrieved {len(knowledge)} knowledge entries" + (f" for project {project_id}" if project_id else " globally"))
            return knowledge

        except Exception as e:
            logger.error(f"Failed to retrieve knowledge: {e}", exc_info=True)
            return []

    def _extract_skill_url(self, message: str) -> Optional[Dict[str, str]]:
        """
        Extract skill URL from message and parse into skill_id and skill_name

        Supports formats:
        1. https://skills.sh/owner/repo/skill-name
        2. https://github.com/owner/repo (requires --skill or skill name in message)
        3. skills.sh/owner/repo/skill-name
        4. owner/repo/skill-name (without URL prefix)

        Also extracts skill_name if specified with patterns like:
        - "...安装 xxx skill"
        - "...安装名为 xxx 的 skill"
        - "--skill xxx"

        Args:
            message: User's message

        Returns:
            Dict with skill_id, skill_name (optional), url (optional)
            None if no skill URL found
        """
        skill_id = None
        skill_name = None
        url = None
        is_github = False

        github_pattern = r'(https?://github\.com/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+)'
        github_match = re.search(github_pattern, message)
        if github_match:
            url = github_match.group(1)
            skill_id = url
            is_github = True
            logger.info(f"[ExtractSkillURL] Found GitHub URL: {url}")

        if not skill_id:
            skills_sh_pattern = r'(?:https?://)?skills\.sh/([a-zA-Z0-9_\-/]+)'
            match = re.search(skills_sh_pattern, message)
            if match:
                skill_id = match.group(1).rstrip('/')
                url = f"https://skills.sh/{skill_id}"
                parts = skill_id.split('/')
                if len(parts) >= 3:
                    skill_name = parts[-1]
                logger.info(f"[ExtractSkillURL] Found skills.sh URL: skill_id={skill_id}")

        if not skill_id:
            standalone_pattern = r'([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+(?:/[a-zA-Z0-9_\-]+)?)'
            match = re.search(standalone_pattern, message)
            if match:
                potential_id = match.group(1)
                parts = potential_id.split('/')
                if len(parts) >= 2:
                    install_keywords = ['安装', '下载', 'install', 'skill', '技能', '工具']
                    has_install_intent = any(kw in message.lower() for kw in install_keywords)

                    if not has_install_intent:
                        logger.info(f"[ExtractSkillURL] Found '{potential_id}' but no install intent, skipping")
                        return None

                    skill_id = potential_id
                    if len(parts) >= 3:
                        skill_name = parts[-1]
                    logger.info(f"[ExtractSkillURL] Found standalone skill_id: {skill_id}")

        if skill_id:
            skill_name_patterns = [
                r'--skill\s+([a-zA-Z0-9_\-]+)',
                r'(?:安装|下载|使用)\s*([a-zA-Z0-9_\-]+)\s*(?:skill|技能)',
                r'(?:名为|叫做|叫)\s*([a-zA-Z0-9_\-]+)\s*(?:的skill|的技能)?',
                r'skill[：:]\s*([a-zA-Z0-9_\-]+)',
            ]

            for pattern in skill_name_patterns:
                name_match = re.search(pattern, message, re.IGNORECASE)
                if name_match:
                    extracted_name = name_match.group(1)
                    if extracted_name.lower() not in ['skill', '技能', 'the', 'a', 'an']:
                        skill_name = extracted_name
                        logger.info(f"[ExtractSkillURL] Extracted skill_name from message: {skill_name}")
                        break

            if is_github and not skill_name:
                logger.warning(f"[ExtractSkillURL] GitHub URL found but no skill_name specified. Will try to infer.")

            result = {
                'skill_id': skill_id,
                'skill_name': skill_name
            }
            if url:
                result['url'] = url

            return result

        return None

    async def cleanup_mcp(self) -> None:
        """
        MCP 连接清理（应用级管理，不再由 Agent 管理）
        
        此方法现在只重置 Agent 内部状态，不真正断开连接。
        连接由 ASGI lifespan 管理，应用关闭时统一清理。
        """
        self._mcp_initialized = False
        logger.info("[ChatbotAgent] MCP 状态已重置（连接由应用级管理）")

    async def cleanup(self) -> None:
        """Cleanup agent resources"""
        logger.info("Cleaning up ChatbotAgent")

        self._mcp_initialized = False

        if hasattr(self.llm_service, 'cleanup'):
            await self.llm_service.cleanup()

        self.update_state("cleanup")
        logger.info("ChatbotAgent cleanup complete")
