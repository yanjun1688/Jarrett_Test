"""
基础LLM服务
支持多模型提供商：OpenAI、Claude、DeepSeek
"""
import os
import asyncio
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()


class LLMProvider(Enum):
    """LLM提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    ZHIPU = "zhipu"
    QWEN = "qwen"


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider
    model_name: str
    api_key: str
    temperature: float = 0.3
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # 额外参数
    extra_params: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        if self.extra_params is None:
            self.extra_params = {}


class BaseLLMService:
    """基础LLM服务类"""
    
    def __init__(self, config: Optional[LLMConfig] = None, provider: Optional[LLMProvider] = None) -> None:
        """
        初始化LLM服务
        
        Args:
            config: LLMConfig配置对象
            provider: LLM提供商（如果不提供config，从环境变量加载）
        """
        if config:
            self.config = config
        else:
            self.config = self._load_config_from_env(provider)
        
        self._initialize_client()
        logger.info(f"Initialized {self.config.provider.value} LLM with model: {self.config.model_name}")
    
    def _load_config_from_env(self, provider: Optional[LLMProvider] = None) -> LLMConfig:
        """从环境变量加载配置"""
        if provider is None:
            # 默认使用OpenAI
            provider = LLMProvider.OPENAI
        
        if provider == LLMProvider.OPENAI:
            api_key = os.getenv("OPENAI_API_KEY")
            model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4")
        elif provider == LLMProvider.ANTHROPIC:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            model_name = os.getenv("ANTHROPIC_MODEL_NAME", "claude-3-5-sonnet-20241022")
        elif provider == LLMProvider.DEEPSEEK:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            model_name = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")
        elif provider == LLMProvider.ZHIPU:
            api_key = os.getenv("ZHIPU_API_KEY")
            model_name = os.getenv("ZHIPU_MODEL_NAME", "glm-4.7-flash")
        elif provider == LLMProvider.QWEN:
            api_key = os.getenv("DASHSCOPE_API_KEY")
            model_name = os.getenv("QWEN_MODEL_NAME", "qwen3-coder-plus")
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        if not api_key:
            raise ValueError(f"{provider.value.upper()}_API_KEY not found in environment variables")
        
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))
        
        return LLMConfig(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def _initialize_client(self) -> None:
        """初始化LLM客户端（子类实现）"""
        raise NotImplementedError("Subclasses must implement _initialize_client")
    
    async def initialize(self) -> None:
        """Initialize LLM service"""
        logger.info(f"Initializing LLM service: {self.config.model_name}")
    
    async def cleanup(self) -> None:
        """Cleanup LLM service resources"""
        logger.info(f"Cleaning up LLM service: {self.config.model_name}")

    # ==================== 统一的消息和响应处理辅助方法 ====================

    def _build_standard_messages(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        filter_system_from_history: bool = False
    ) -> List[Dict[str, str]]:
        """
        构建标准 OpenAI 格式的消息列表

        Args:
            prompt: 用户提示
            system_message: 系统消息
            conversation_history: 对话历史
            filter_system_from_history: 是否过滤历史中的 system 消息

        Returns:
            消息列表
        """
        messages = []

        # 添加系统消息
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })

        # 添加对话历史
        if conversation_history:
            for msg in conversation_history:
                if filter_system_from_history and msg.get('role') == 'system':
                    continue
                # 过滤掉 content 为空的消息（某些 API 不接受空 content）
                content = msg.get('content')
                if not content:
                    continue
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": content
                })

        # 添加当前提示
        messages.append({
            "role": "user",
            "content": prompt
        })

        return messages

    def _extract_standard_response(self, response: Any) -> str:
        """
        从 OpenAI 格式的响应中提取内容

        Args:
            response: API 响应对象

        Returns:
            生成的文本
        """
        if hasattr(response, 'choices') and len(response.choices) > 0:
            message = response.choices[0].message
            # 优先取 content
            if hasattr(message, 'content') and message.content:
                return str(message.content)
            # 兼容 thinking 模式（GLM-5 等），内容在 reasoning_content 中
            if hasattr(message, 'reasoning_content') and message.reasoning_content:
                return str(message.reasoning_content)
            # 工具调用
            if hasattr(message, 'tool_calls') and message.tool_calls:
                import json
                return json.dumps({
                    "tool_calls": message.tool_calls
                }, ensure_ascii=False)
        return str(response)

    def _extract_standard_usage(self, response: Any) -> Optional[Dict[str, int]]:
        """
        从响应中提取 usage 信息

        Args:
            response: API 响应对象

        Returns:
            usage 字典或 None
        """
        if hasattr(response, 'usage'):
            return {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        return None

    def _extract_standard_finish_reason(self, response: Any) -> str:
        """
        从响应中提取 finish_reason

        Args:
            response: API 响应对象

        Returns:
            finish_reason 或 "stop"
        """
        if hasattr(response, 'choices') and len(response.choices) > 0:
            choice = response.choices[0]
            if hasattr(choice, 'finish_reason'):
                return str(choice.finish_reason)
        return "stop"
    
    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any
    ) -> str:
        """
        生成文本

        Args:
            prompt: 用户提示
            system_message: 系统消息
            conversation_history: 对话历史
            **kwargs: 额外参数

        Returns:
            生成的文本
        """
        raise NotImplementedError("Subclasses must implement generate")

    async def generate_response(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate response from context

        Args:
            context: Context containing message, intent, knowledge, etc.

        Returns:
            Response dictionary with text and metadata
        """
        raise NotImplementedError("Subclasses must implement generate_response")

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_message: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        使用工具生成文本（支持ReAct模式）

        Args:
            prompt: 用户提示
            tools: 可用工具列表
            system_message: 系统消息
            conversation_history: 对话历史
            **kwargs: 额外参数

        Returns:
            包含response、tool_calls等信息的字典
        """
        raise NotImplementedError("Subclasses must implement generate_with_tools")

    def count_tokens(self, text: str) -> int:
        """
        计算文本的Token数量
        
        Args:
            text: 输入文本
            
        Returns:
            Token数量
        """
        try:
            import tiktoken
            if self.config.provider == LLMProvider.OPENAI:
                encoding = tiktoken.encoding_for_model(self.config.model_name)
            else:
                # 对于非OpenAI模型，使用cl100k_base作为近似
                encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            # 如果没有tiktoken，粗略估算（1 token ≈ 4字符）
            return len(text) // 4
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        估算成本
        
        Args:
            input_tokens: 输入Token数
            output_tokens: 输出Token数
            
        Returns:
            估算成本（美元）
        """
        # 简化的定价表（需要根据实际价格更新）
        pricing = {
            LLMProvider.OPENAI: {
                "gpt-4": (0.03, 0.06),  # (input, output) per 1K tokens
                "gpt-4-turbo": (0.01, 0.03),
                "gpt-3.5-turbo": (0.0005, 0.0015),
            },
            LLMProvider.ANTHROPIC: {
                "claude-3-5-sonnet-20241022": (0.003, 0.015),
                "claude-3-opus-20240229": (0.015, 0.075),
                "claude-3-sonnet-20240229": (0.003, 0.015),
            },
            LLMProvider.DEEPSEEK: {
                "deepseek-chat": (0.0001, 0.0002),  # 非常便宜
            },
            LLMProvider.QWEN: {
                "qwen3-coder-plus": (0.0003, 0.0006),
                "qwen-plus": (0.0002, 0.0004),
            },
            LLMProvider.ZHIPU: {
                "glm-5": (0.0, 0.0),  # 免费！
                "glm-4": (0.0001, 0.0001),
                "glm-4-flash": (0.00001, 0.00001),
                "glm-4.7-flash": (0.00001, 0.00001),
                "glm-4-plus": (0.00005, 0.00005),
            }
        }
        
        provider_pricing = pricing.get(self.config.provider, {})
        model_pricing = provider_pricing.get(self.config.model_name, (0.001, 0.002))
        
        input_cost = (input_tokens / 1000) * model_pricing[0]
        output_cost = (output_tokens / 1000) * model_pricing[1]
        
        return input_cost + output_cost


class OpenAICompatibleService(BaseLLMService):
    """
    OpenAI 兼容 API 服务基类
    适用于 OpenAI、DeepSeek、千问、KIMI、智谱（兼容模式）等
    """

    def _initialize_client(self) -> None:
        """
        初始化 OpenAI 兼容客户端
        子类可重写此方法以设置自定义 base_url
        """
        import openai

        # 子类可以通过设置 self.base_url 来自定义端点
        base_url = getattr(self, 'base_url', None)

        # 使用同步客户端
        self.client = openai.OpenAI(
            api_key=self.config.api_key,
            base_url=base_url
        )

        provider_name = self.config.provider.value
        base_url_str = f" (base_url={base_url})" if base_url else ""
        logger.info(f"OpenAI compatible client initialized: {provider_name}{base_url_str}, model: {self.config.model_name}")

    def _call_create(self, **kwargs: Any) -> Any:
        """同步调用 OpenAI create 方法的 wrapper"""
        return self.client.chat.completions.create(**kwargs)

    def _format_request_params(
        self,
        messages: List[Dict[str, str]],
        system_message: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        格式化请求参数，子类可重写以添加特殊参数

        Args:
            messages: 消息列表
            system_message: 系统消息
            tools: 工具列表
            **kwargs: 其他参数

        Returns:
            请求参数字典
        """
        params = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.config.temperature),
        }

        max_tokens = kwargs.get('max_tokens', self.config.max_tokens)
        if max_tokens is not None:
            params['max_tokens'] = max_tokens

        if 'top_p' in kwargs:
            params['top_p'] = kwargs['top_p']

        if tools:
            params['tools'] = tools

        if kwargs.get('response_format'):
            params['response_format'] = kwargs['response_format']

        return params

    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any
    ) -> str:
        """
        生成文本

        Args:
            prompt: 用户提示
            system_message: 系统消息
            conversation_history: 对话历史
            **kwargs: 额外参数

        Returns:
            生成的文本
        """
        try:
            # 构建消息列表
            messages = self._build_standard_messages(
                prompt=prompt,
                system_message=system_message,
                conversation_history=conversation_history
            )

            # 格式化请求参数
            request_params = self._format_request_params(
                messages=messages,
                system_message=system_message,
                **kwargs
            )

            logger.info(f"Sending request to {self.config.provider.value}: {self.config.model_name}")
            logger.debug(f"Messages count: {len(messages)}")

            response = await asyncio.to_thread(self._call_create, **request_params)

            # 提取生成的文本
            generated_text = self._extract_standard_response(response)

            logger.debug(f"Generated {len(generated_text)} characters")

            return generated_text

        except Exception as e:
            logger.error(f"{self.config.provider.value} API error: {e}", exc_info=True)
            raise

    async def generate_response(
        self,
        context: Any
    ) -> Dict[str, Any]:
        """
        Generate response from context
        
        支持两种调用方式：
        1. 传入字符串 prompt（当前 response_generator.py 的调用方式）
        2. 传入字典 context（基类定义的原始方式）
        
        Args:
            context: 可以是字符串 prompt 或包含 message/intent/knowledge 的字典
            
        Returns:
            响应字典，包含 text 字段
        """
        try:
            # 如果是字符串，直接作为 prompt 使用
            if isinstance(context, str):
                prompt = context
            elif isinstance(context, dict):
                # 从字典中提取信息构建 prompt
                message = context.get("message", "")
                intent = context.get("intent", "chat")
                knowledge = context.get("knowledge", [])
                additional_context = context.get("context", {})
                
                # 构建 prompt
                prompt = self._build_response_prompt(message, intent, knowledge, additional_context)
            else:
                prompt = str(context)
            
            # 调用已有的 generate 方法获取响应
            response_text = await self.generate(prompt=prompt)
            
            return {"text": response_text}
            
        except Exception as e:
            logger.error(f"generate_response error: {e}", exc_info=True)
            raise

    def _build_response_prompt(
        self,
        message: str,
        intent: str,
        knowledge: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """
        Build prompt for response generation
        
        Args:
            message: User's message
            intent: Detected intent
            knowledge: Retrieved knowledge entries
            context: Additional execution context
            
        Returns:
            Formatted prompt string
        """
        knowledge_context = ""
        if knowledge:
            knowledge_context = "\n\n### 知识库信息\n"
            for i, entry in enumerate(knowledge[:3], 1):
                content = entry.get("content", "")
                score = entry.get("metadata", {}).get("score", 0)
                knowledge_context += f"{i}. [_similarity: {score:.2f}]\n{content}\n"
        
        context_info = ""
        if context:
            context_info = "\n\n### 执行上下文\n"
            for key, value in context.items():
                context_info += f"{key}: {value}\n"
        
        prompt = f"""你是一个智能测试助手，帮助用户生成和执行测试。

## 用户消息
{message}

## 意图识别
意图类型: {intent}

## 指令
请根据用户的消息和意图，提供合适的回复。

{knowledge_context}
{context_info}

## 回复要求
1. 如果需要执行操作，请明确说明
2. 如果有相关的知识库信息，请引用
3. 保持回复简洁明了
4. 如有建议操作，请列出

请直接回复：
"""
        return prompt

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_message: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        使用工具生成文本（支持 ReAct 模式）

        Args:
            prompt: 用户提示
            tools: 可用工具列表
            system_message: 系统消息
            conversation_history: 对话历史
            **kwargs: 额外参数

        Returns:
            包含response、tool_calls等信息的字典
        """
        try:
            # 构建消息列表
            messages = self._build_standard_messages(
                prompt=prompt,
                system_message=system_message,
                conversation_history=conversation_history
            )

# 格式化请求参数
            request_params = self._format_request_params(
                messages=messages,
                system_message=system_message,
                tools=tools,
                **kwargs
            )

            response = await asyncio.to_thread(self._call_create, **request_params)

            # 揄取响应信息
            message = response.choices[0].message

            result: Dict[str, Any] = {
                "response": message.content if hasattr(message, 'content') and message.content else "",
                "tool_calls": getattr(message, 'tool_calls', None),
                "finish_reason": self._extract_standard_finish_reason(response)
            }

            # 添加使用信息
            usage = self._extract_standard_usage(response)
            if usage:
                result['usage'] = usage

            return result

        except Exception as e:
            logger.error(f"{self.config.provider.value} API error with tools: {e}", exc_info=True)
            raise


# 便捷工厂函数
def create_llm_service(
    provider: str = "openai",
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs: Any
) -> BaseLLMService:
    """
    创建LLM服务实例

    Args:
        provider: 提供商名称 (openai/anthropic/deepseek/zhipu/qwen)
        model_name: 模型名称
        api_key: API密钥
        **kwargs: 其他配置参数

    Returns:
        LLM服务实例
    """
    provider_enum = LLMProvider(provider.lower())

    # 根据提供商选择具体的服务类
    service_class: type[BaseLLMService]
    if provider_enum == LLMProvider.OPENAI:
        from .openai_llm import OpenAILLMService
        service_class = OpenAILLMService
    elif provider_enum == LLMProvider.ANTHROPIC:
        from .anthropic_llm import AnthropicLLMService
        service_class = AnthropicLLMService
    elif provider_enum == LLMProvider.DEEPSEEK:
        from .deepseek_llm import DeepSeekLLMService
        service_class = DeepSeekLLMService
    elif provider_enum == LLMProvider.ZHIPU:
        from .zhipu_llm import ZhipuLLMService
        service_class = ZhipuLLMService
    elif provider_enum == LLMProvider.QWEN:
        from .qwen_llm import QwenLLMService
        service_class = QwenLLMService
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    if model_name or api_key:
        # 如果提供了model_name或api_key，创建自定义配置
        if not api_key:
            if provider_enum == LLMProvider.OPENAI:
                api_key = os.getenv("OPENAI_API_KEY")
            elif provider_enum == LLMProvider.ANTHROPIC:
                api_key = os.getenv("ANTHROPIC_API_KEY")
            elif provider_enum == LLMProvider.DEEPSEEK:
                api_key = os.getenv("DEEPSEEK_API_KEY")
            elif provider_enum == LLMProvider.ZHIPU:
                api_key = os.getenv("ZHIPU_API_KEY")
            elif provider_enum == LLMProvider.QWEN:
                api_key = os.getenv("DASHSCOPE_API_KEY")

        if not model_name:
            if provider_enum == LLMProvider.OPENAI:
                model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4")
            elif provider_enum == LLMProvider.ANTHROPIC:
                model_name = os.getenv("ANTHROPIC_MODEL_NAME", "claude-3-5-sonnet-20241022")
            elif provider_enum == LLMProvider.DEEPSEEK:
                model_name = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")
            elif provider_enum == LLMProvider.ZHIPU:
                model_name = os.getenv("ZHIPU_MODEL_NAME", "glm-4.7-flash")
            elif provider_enum == LLMProvider.QWEN:
                model_name = os.getenv("QWEN_MODEL_NAME", "qwen3-coder-plus")

        config = LLMConfig(
            provider=provider_enum,
            model_name=model_name or "",
            api_key=api_key or "",
            **kwargs
        )
        return service_class(config)
    else:
        return service_class(provider=provider_enum)
