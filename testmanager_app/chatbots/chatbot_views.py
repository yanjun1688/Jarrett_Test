"""
增强版ChatBot视图
支持技能检索→意图识别→工具路由→执行的完整流程

注意：已从 test_agent_framework 迁移到 core 模块

会话管理:
- 基于 AgentConversation 模型的数据库存储
- 支持多轮对话上下文保持
"""
from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rest_framework.request import Request

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
import logging
import json
from asgiref.sync import async_to_sync, sync_to_async
import time

from core.agents.llm.base_llm import create_llm_service, BaseLLMService
from core.agents.chatbot_agent import ChatbotAgent
from core.config import get_settings
from core.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)


async def direct_generate(
    llm_service: BaseLLMService,
    test_type: str,
    description: str,
    project_id: int,
    url: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
) -> Dict[str, Any]:
    """
    直接调用 LLM 生成测试代码（markdown 格式）
    
    不走 ChatBot 工具选择流程，直接返回 LLM 响应。
    前端渲染 markdown 即可。
    """
    prompts: Dict[str, str] = {
        'ui': _build_ui_prompt(description, url),  # @deprecated 描述生成功能已废弃
        'api': _build_api_prompt(description, endpoint, method),
        'prd': _build_prd_prompt(description),
    }
    
    system_messages: Dict[str, str] = {
        'ui': '你是 Playwright 测试专家，擅长生成高质量的 UI 自动化测试代码。',  # @deprecated 描述生成功能已废弃
        'api': '你是 API 测试专家，擅长生成结构化的 JSON 测试配置，必须严格遵守 JSON 对象格式。',
        'prd': '你是测试设计专家，擅长根据 PRD 文档设计全面的测试用例。',
    }
    
    prompt = prompts.get(test_type, prompts['ui'])
    system_message = system_messages.get(test_type, system_messages['ui'])
    
    try:
        response = await llm_service.generate(
            prompt=prompt,
            system_message=system_message,
            temperature=0.3,
            max_tokens=None,
        )
        
        logger.info(f'[Direct Generate] test_type={test_type}, endpoint={endpoint}, method={method}')
        logger.info(f'[Direct Generate] LLM response (first 500 chars): {response[:500] if response else "EMPTY"}')
        
        # 对于 API 测试，强制修正 URL（如果用户提供了 endpoint）
        if test_type == 'api' and endpoint and response:
            import json
            try:
                # 尝试解析 JSON
                clean_response = response.strip()
                if clean_response.startswith('```'):
                    # 去掉 markdown 代码块
                    lines = clean_response.split('\n')
                    clean_response = '\n'.join([l for l in lines if not l.startswith('```')])
                
                parsed = json.loads(clean_response)
                
                # 如果是数组，包装为对象
                if isinstance(parsed, list):
                    parsed = {'name': 'AI生成的测试', 'steps': parsed}
                
                # 强制替换所有步骤中的 URL
                if isinstance(parsed, dict) and 'steps' in parsed:
                    for step in parsed.get('steps', []):
                        if 'request' in step and isinstance(step['request'], dict):
                            step['request']['url'] = endpoint
                            if method:
                                step['request']['method'] = method
                    logger.info(f'[Direct Generate] 强制替换 URL 为: {endpoint}')
                
                # 返回修正后的 JSON
                response = json.dumps(parsed, ensure_ascii=False)
                logger.info(f'[Direct Generate] 修正后的 JSON: {response}')
                
            except json.JSONDecodeError as e:
                logger.warning(f'[Direct Generate] JSON 解析失败，返回原始响应: {e}')
        
        return {
            'success': True,
            'response': response,
        }
        
    except Exception as e:
        logger.error(f'Direct generation failed: {e}', exc_info=True)
        return {
            'success': False,
            'error': f'生成失败: {str(e)}',
            'response': '',
        }


def _build_ui_prompt(description: str, url: Optional[str]) -> str:
    """
    @deprecated 描述生成功能已废弃。
    generateUITest → direct_generate(test_type='ui') 链路已被判定为无实际意义。
    保留仅用于兼容 AiTestGenerator 中已废弃的 DescriptionForm 组件。
    替代方案：使用 _build_api_prompt（API定义）或 _build_prd_prompt（PRD文档）。
    """
    url_context = f'目标URL: {url}\n' if url else ''
    return f"""请根据以下描述生成 Playwright UI 自动化测试代码。

测试场景: {description}
{url_context}
要求：
1. 使用 Python + Playwright + pytest
2. 包含必要的 import 语句
3. 使用异步方式 (async/await)
4. 包含适当的注释说明每个步骤
5. 使用合适的定位器 (role, text, test-id 优先于 CSS selector)
6. 包含错误处理
7. 代码应完整可执行

请自我检查：
- 代码是否完整可运行？
- 是否包含所有必要的 import？
- 是否有适当的注释？
- 是否符合 Playwright 最佳实践？

直接输出 Python 代码，使用 markdown 代码块格式。"""


def _build_api_prompt(description: str, endpoint: Optional[str], method: Optional[str]) -> str:
    endpoint_ctx = f'API 端点: {endpoint}\n' if endpoint else ''
    method_ctx = f'HTTP 方法: {method}\n' if method else ''
    return f"""请根据以下信息生成结构化的API测试配置，用于测试执行引擎直接执行。

{endpoint_ctx}{method_ctx}描述: {description}

【重要】必须输出一个JSON对象，不要输出数组！

直接输出以下JSON格式（不要包裹在代码块中，不要输出任何其他内容）：
{{
  "name": "测试用例名称",
  "description": "测试场景简要描述",
  "steps": [
    {{
      "name": "执行API请求",
      "request": {{
        "method": "{method or 'GET'}",
        "url": "{endpoint or '请填写完整URL'}",
        "headers": {{}},
        "json": {{}}
      }},
      "assertions": [
        {{
          "type": "status_code",
          "expected": 200,
          "comparison": "equals"
        }}
      ]
    }}
  ]
}}

字段说明：
- name: 测试用例名称
- description: 测试场景描述
- steps: 测试步骤数组（至少包含一个步骤）
  - name: 步骤名称
  - request: 请求配置
    - method: HTTP方法（GET/POST/PUT/DELETE/PATCH）
    - url: 完整的API地址（必须使用用户提供的端点值）
    - headers: 请求头对象
    - json: 请求体对象（POST/PUT/PATCH时根据API功能填写）
  - assertions: 断言数组
    - type: status_code 或 jsonpath
    - expected: 期望值（状态码如200，或JSONPath提取的期望值）
    - comparison: equals, contains, not_equals, gt, gte, lt, lte
    - expression: JSONPath表达式（仅jsonpath类型需要，如 $.data.token）

要求：
1. 必须输出JSON对象格式，以 {{ 开头，不要输出数组 [！
2. 根据API功能设计合理的测试场景
3. 至少包含一个status_code断言
4. headers和json必须是有效的JSON对象或空对象
5. url必须使用用户提供的API端点值
6. 根据HTTP方法和API功能决定是否需要json请求体

直接输出JSON对象，不要包裹在任何代码块或markdown格式中。"""


def _build_prd_prompt(description: str) -> str:
    return f"""请根据以下 PRD 描述生成测试用例设计。

PRD 描述: {description}

要求：
1. 分析 PRD 中的功能点和业务流程
2. 设计测试用例，覆盖正常流程和异常场景
3. 输出格式：使用 markdown 表格展示测试用例
4. 每个测试用例包含：用例名称、前置条件、操作步骤、预期结果
5. 考虑边界条件和异常场景

直接输出测试用例设计文档，使用 markdown 格式。"""




# 缓存 LLM 服务实例，避免重复初始化
_llm_service_cache: Dict[str, BaseLLMService] = {}

_chatbot_agent_cache: Dict[int, ChatbotAgent] = {}


def get_llm_service(provider: str | None = None) -> BaseLLMService:
    """
    根据提供商获取LLM服务实例
    优先从 .env 配置读取默认 provider，支持缓存避免重复初始化
    """
    import time
    start_time = time.time()
    
    if provider is None:
        settings = get_settings()
        provider = settings.llm_provider
        logger.info(f"Using LLM provider from .env config: {provider}")
    
    provider = provider.lower() if provider else "qwen"
    
    if provider in _llm_service_cache:
        logger.debug(f"Using cached LLM service for provider: {provider}")
        return _llm_service_cache[provider]
    
    logger.info(f"Creating new LLM service for provider: {provider}")
    llm_service = create_llm_service(provider=provider)
    
    _llm_service_cache[provider] = llm_service
    
    logger.info(f"LLM service created in {time.time() - start_time:.2f}s")
    return llm_service


def get_chatbot_agent(llm_service: Any) -> ChatbotAgent:
    """
    获取或创建 ChatbotAgent 实例
    使用缓存避免每次请求都重新创建
    """
    import time
    start_time = time.time()
    
    cache_key = id(llm_service)
    
    if cache_key in _chatbot_agent_cache:
        logger.debug("Using cached ChatbotAgent instance")
        return _chatbot_agent_cache[cache_key]
    
    logger.info("Creating new ChatbotAgent instance")
    
    # 创建知识库 RAG agent
    knowledge_rag_agent = None
    try:
        from core.agents.rag.knowledge_rag_agent import KnowledgeRAGAgent
        from core.agents.rag.rag_retriever_service import DjangoORMRAGRetriever
        
        rag_retriever = DjangoORMRAGRetriever()
        
        knowledge_rag_agent = KnowledgeRAGAgent(
            llm_service=llm_service,
            rag_retriever=rag_retriever
        )
        logger.info("KnowledgeRAGAgent created with DjangoORMRAGRetriever")
    except Exception as e:
        logger.warning(f"Failed to create KnowledgeRAGAgent: {e}")
    
    agent = ChatbotAgent(
        llm_service=llm_service,
        knowledge_rag_agent=knowledge_rag_agent,
    )
    
    # 不在同步环境中初始化，延迟到请求异步上下文中
    # MCP连接必须在创建它的Task中使用，避免跨事件循环错误
    
    _chatbot_agent_cache[cache_key] = agent
    
    logger.info(f"ChatbotAgent created in {time.time() - start_time:.2f}s")
    return agent


class EnhancedChatBotView(APIView):
    """
    增强版AI对话接口视图
    POST /api/chatbot/chat

    支持两种请求方式：
    - JSON body: 标准 JSON 格式，message 必填
    - multipart/form-data: 上传文件时使用，自动解析文件内容作为 message

    注意：使用 @async_to_sync 装饰器将异步视图转换为同步视图，
    避免 DRF async authentication 问题，同时与 Daphne ASGI 事件循环兼容。
    DRF 没有官方 async authentication 支持，sync view 让认证流程正常工作。
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @async_to_sync
    async def post(self, request: Request) -> Response:
        """
        处理聊天消息
        """
        return await self._async_post(request)
    
    async def _async_post(self, request: Request) -> Response:
        """
        处理聊天消息

        职责边界：
        - API 层只负责 HTTP 请求/响应、会话创建/权限校验
        - 历史管理、存储、prompt 构建全部由 ChatbotAgent 内部处理

        分支逻辑：
        - source='generator': AI Test Generator 表单场景，直接调用 LLM，不走工具选择
        - source='chatbot' 或 None: ChatBot 对话场景，走 ChatBotAgent 工具选择流程
        """
        try:
            settings = get_settings()
            default_provider = settings.llm_provider
            
            data: Any = request.data
            message: str = str(data.get('message', '')).strip()

            # 如果 message 为空但有上传文件，自动解析文件内容作为 message
            if not message:
                files: Dict[str, Any] = getattr(request, 'FILES', {})
                uploaded_file = files.get('file')
                if uploaded_file:
                    from core.utils.document_loader import DocumentLoader
                    try:
                        file_bytes = uploaded_file.read()
                        filename = str(uploaded_file.name)
                        message = DocumentLoader.load_document_from_bytes(file_bytes, filename)
                    except ValueError as e:
                        return Response({
                            'success': False,
                            'error': str(e),
                        }, status=status.HTTP_400_BAD_REQUEST)
                    except Exception as e:
                        logger.error(f'Failed to parse uploaded file: {e}', exc_info=True)
                        return Response({
                            'success': False,
                            'error': f'文件解析失败: {str(e)}',
                        }, status=status.HTTP_400_BAD_REQUEST)

            if not message:
                return Response({
                    "success": False,
                    "error": "消息内容不能为空"
                }, status=status.HTTP_400_BAD_REQUEST)

            provider: str = str(data.get('provider', default_provider))
            model = data.get('model') or settings.llm_model
            temperature: float = float(data.get('temperature', settings.llm_temperature))
            max_tokens: int = int(data.get('max_tokens', settings.llm_max_tokens))
            conversation_id: Optional[str] = data.get('conversation_id')
            project_id_raw = data.get('project_id')
            project_id: Optional[int] = int(project_id_raw) if project_id_raw else None
            test_type: Optional[str] = data.get('test_type')
            source: Optional[str] = data.get('source')
            url: Optional[str] = data.get('url')
            endpoint: Optional[str] = data.get('endpoint')
            method: Optional[str] = data.get('method')

            llm_service = get_llm_service(provider)

            if source == 'generator':
                if not project_id:
                    return Response({
                        "success": False,
                        "error": "AI Generator 场景需要指定 project_id"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                if not test_type:
                    return Response({
                        "success": False,
                        "error": "AI Generator 场景需要指定 test_type (ui/api/prd)"
                    }, status=status.HTTP_400_BAD_REQUEST)

                import time
                start_time = time.time()
                
                result = await direct_generate(
                    llm_service=llm_service,
                    test_type=test_type,
                    description=message,
                    project_id=project_id,
                    url=url,
                    endpoint=endpoint,
                    method=method,
                )
                
                logger.info(f"Direct generation took {time.time() - start_time:.2f}s")
                
                return Response({
                    "success": result.get('success', False),
                    "response": result.get('response', ''),
                    "tool_result": result.get('tool_result'),
                    "model": result.get('model', provider),
                    "provider": provider,
                    "timestamp": time.time(),
                    "project_id": project_id,
                    "test_type": test_type,
                }, status=status.HTTP_200_OK)

            conversation, error, is_new = await sync_to_async(
                ConversationService.get_or_create_conversation
            )(
                user=request.user,  # type: ignore[arg-type]
                conversation_id=conversation_id,
                project_id=project_id
            )

            if error or conversation is None:
                return Response({
                    "success": False,
                    "error": error or "会话创建失败"
                }, status=status.HTTP_400_BAD_REQUEST if error and "上限" in error else status.HTTP_404_NOT_FOUND)

            conv_id_str = str(conversation.conversation_id)

            import time
            start_time = time.time()

            chatbot_agent = get_chatbot_agent(llm_service)
            await chatbot_agent.initialize()
            logger.info(f"Agent initialized in {time.time() - start_time:.2f}s")

            input_data = {
                "message": message,
                "conversation_id": conv_id_str,
                "user_id": request.user.id,
                "project_id": project_id,
                "test_type": test_type,
                "context": {
                    "provider": provider,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            }
            exec_start = time.time()
            result = await chatbot_agent.execute(input_data)
            logger.info(f"Agent execution took {time.time() - exec_start:.2f}s")

            assistant_message = result.get("message", "")

            if is_new or not conversation.title:
                conversation.title = message[:30]
                await sync_to_async(conversation.save)(update_fields=["title", "updated_at"])

            response_data = {
                "success": result.get("success", True),
                "response": assistant_message,
                "tool_used": result.get("tool_used", False),
                "iterations": result.get("iterations"),
                "stopped_reason": result.get("stopped_reason"),
                "model": provider,
                "provider": provider,
                "conversation_id": conv_id_str,
            }
            if result.get("options"):
                response_data["options"] = result["options"]

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"ChatBot API error: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "error": f"处理消息时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetModelListView(APIView):
    """
    获取支持的模型列表
    GET /api/chatbot/models
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """返回支持的 LLM 模型列表"""
        from core.config import get_settings
        current_settings = get_settings()
        
        # 当前配置的模型作为默认选项
        default_model_id = current_settings.llm_provider
        default_model_name = current_settings.llm_model
        
        models = [
            {"id": "openai", "name": "OpenAI GPT", "provider": "openai", "default": default_model_id == "openai"},
            {"id": "anthropic", "name": "Anthropic Claude", "provider": "anthropic", "default": default_model_id == "anthropic"},
            {"id": "deepseek", "name": "DeepSeek", "provider": "deepseek", "default": default_model_id == "deepseek"},
            {"id": "zhipu", "name": "Zhipu AI", "provider": "zhipu", "default": default_model_id == "zhipu"},
            {"id": "qwen", "name": "Qwen", "provider": "qwen", "default": default_model_id == "qwen"},
        ]
        
        # 按默认配置优先级调整顺序
        default_first_models: list[dict[str, Any]] = []
        others = []
        
        for model in models:
            if model.get("default"):
                # 插入到最前面
                default_first_models.insert(0, {
                    **model,
                    "active_config": {
                        "provider": current_settings.llm_provider,
                        "model": current_settings.llm_model,
                        "temperature": current_settings.llm_temperature,
                        "max_tokens": current_settings.llm_max_tokens
                    }
                })
            else:
                others.append(model)
        
        # 组合最终列表
        final_models = default_first_models + others
        
        # 添加配置信息
        config_info = {
            "configured_provider": current_settings.llm_provider,
            "configured_model": current_settings.llm_model,
            "configured_temperature": current_settings.llm_temperature,
            "configured_max_tokens": current_settings.llm_max_tokens,
            "configured_url": current_settings.llm_base_url
        }
        
        return Response({
            "models": final_models,
            "config": config_info
        })


class ConversationListView(APIView):
    """
    会话列表管理
    GET /api/chatbot/conversations - 获取会话列表
    POST /api/chatbot/conversations - 创建新会话
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """获取用户所有会话列表"""
        from core.services.conversation_service import get_markdown_store
        
        conversations = ConversationService.get_user_conversations(request.user)  # type: ignore[arg-type]
        md_store = get_markdown_store()
        
        data = []
        for conv in conversations:
            if conv.migrated_to_markdown:
                # 消息存在 markdown store 里，从那边取数量
                ctx = md_store.get_context(conv.conversation_id, str(request.user.id))
                count = len(ctx.get("messages", [])) if ctx else 0
            else:
                count = len(conv.messages) if conv.messages else 0
            
            data.append({
                "conversation_id": conv.conversation_id,
                "title": conv.title or "新对话",
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": count
            })
        
        return Response({
            "success": True,
            "conversations": data,
            "total": len(data),
            "max_allowed": 30
        })
    
    def post(self, request: Request) -> Response:
        """创建新会话"""
        data: Any = request.data
        project_id_raw = data.get('project_id')
        project_id: Optional[int] = int(project_id_raw) if project_id_raw else None
        
        conversation, error = ConversationService.create_conversation(
            user=request.user,  # type: ignore[arg-type]
            project_id=project_id
        )
        
        if error or conversation is None:
            return Response({
                "success": False,
                "error": error or "会话创建失败"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            "success": True,
            "conversation_id": conversation.conversation_id,
            "message": "会话创建成功"
        }, status=status.HTTP_201_CREATED)


class ConversationDetailView(APIView):
    """
    单个会话管理
    GET /api/chatbot/conversations/<conversation_id> - 获取会话详情
    DELETE /api/chatbot/conversations/<conversation_id> - 删除会话
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request, conversation_id: str) -> Response:
        """获取会话详情"""
        conversation = ConversationService.get_conversation(conversation_id, request.user)  # type: ignore[arg-type]
        
        if not conversation:
            return Response({
                "success": False,
                "error": "会话不存在"
            }, status=status.HTTP_404_NOT_FOUND)
        
        messages, _ = ConversationService.get_messages(conversation_id, request.user)  # type: ignore[arg-type]
        metadata, _ = ConversationService.get_metadata(conversation_id, request.user)  # type: ignore[arg-type]
        
        return Response({
            "success": True,
            "conversation": {
                "conversation_id": conversation.conversation_id,
                "title": conversation.title or "新对话",
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "messages": messages,
                "metadata": metadata
            }
        })
    
    def delete(self, request: Request, conversation_id: str) -> Response:
        """删除会话"""
        success, error = ConversationService.delete_conversation(conversation_id, request.user)  # type: ignore[arg-type]
        
        if not success:
            return Response({
                "success": False,
                "error": error
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            "success": True,
            "message": "会话已删除"
        })


class ClearConversationView(APIView):
    """
    清空对话历史（保留会话，清空消息）
    POST /api/chatbot/clear
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request: Request) -> Response:
        """清空指定会话的消息历史"""
        data: Any = request.data
        conversation_id = data.get('conversation_id')
        
        if not conversation_id:
            return Response({
                "success": False,
                "error": "缺少 conversation_id"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        conversation = ConversationService.get_conversation(conversation_id, request.user)  # type: ignore[arg-type]
        if not conversation:
            return Response({
                "success": False,
                "error": "会话不存在"
            }, status=status.HTTP_404_NOT_FOUND)
        
        conversation.messages = []
        conversation.metadata = {}
        conversation.save()
        
        return Response({
            "success": True,
            "message": "对话历史已清空"
        })


class GetAvailableToolsView(APIView):
    """
    获取可用工具列表
    GET /api/chatbot/tools
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """返回可用的工具列表"""
        tools = [
            {"id": "api_test", "name": "API Test", "description": "Test API endpoints"},
            {"id": "ui_test", "name": "UI Test", "description": "Test UI components"},
        ]
        return Response({"tools": tools})


class TestToolExecutionView(APIView):
    """
    测试工具执行
    POST /api/chatbot/test-tool
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request: Request) -> Response:
        """测试指定工具的执行"""
        return Response({
            "success": False,
            "message": "Tool execution service temporarily unavailable",
            "reason": "test_agent_framework has been removed"
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class CacheStatsView(APIView):
    """
    获取上下文缓存统计
    GET /api/chatbot/cache-stats/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """返回温区/冷区摘要缓存的命中统计"""
        # 从缓存的 ChatbotAgent 实例获取 context_store
        stats = None
        for agent in _chatbot_agent_cache.values():
            if hasattr(agent, 'context_store') and hasattr(agent.context_store, 'get_cache_stats'):
                stats = agent.context_store.get_cache_stats()
                break

        if stats is None:
            return Response({
                "success": True,
                "data": {
                    "warm_hits": 0,
                    "warm_misses": 0,
                    "warm_hit_rate": 0,
                    "cold_hits": 0,
                    "cold_misses": 0,
                    "cold_hit_rate": 0,
                    "cached_sessions": 0,
                },
                "message": "Agent 尚未初始化，暂无缓存数据"
            })

        return Response({
            "success": True,
            "data": stats
        })


class MCPStatusView(APIView):
    """
    获取 MCP 连接状态
    GET /api/chatbot/mcp-status/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """返回 MCP Server 连接状态"""
        from core.agents.capability.mcp_lifespan import global_mcp_manager
        
        states = global_mcp_manager.get_all_states()
        
        return Response({
            "success": True,
            "data": {
                "servers": states,
                "initialized": global_mcp_manager._initialized
            }
        })


class ChatBotExecutionLogListView(APIView):
    """
    获取ChatBot执行日志列表
    GET /api/chatbot/execution-logs/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """获取执行日志列表"""
        from core.models import ChatBotExecutionLog
        
        conversation_id = request.query_params.get('conversation_id')
        log_type = request.query_params.get('log_type')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        queryset = ChatBotExecutionLog.objects.all()
        
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        if log_type:
            queryset = queryset.filter(log_type=log_type)
        
        total = queryset.count()
        logs = queryset[(page - 1) * page_size:page * page_size]
        
        return Response({
            "success": True,
            "data": {
                "logs": [log.to_dict() for log in logs],
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        })


class ChatBotExecutionLogDetailView(APIView):
    """
    获取单条执行日志详情
    GET /api/chatbot/execution-logs/{id}/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request, log_id: int) -> Response:
        """获取执行日志详情"""
        from core.models import ChatBotExecutionLog
        
        try:
            log = ChatBotExecutionLog.objects.get(id=log_id)
            return Response({
                "success": True,
                "data": log.to_dict()
            })
        except ChatBotExecutionLog.DoesNotExist:
            return Response({
                "success": False,
                "message": "Log not found"
            }, status=status.HTTP_404_NOT_FOUND)
