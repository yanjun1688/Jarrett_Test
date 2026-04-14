"""
Anthropic Claude LLM 服务实现
提供基于 Anthropic API 的 LLM 服务
"""
import os
import asyncio
from typing import Optional, Dict, Any, List
from .base_llm import BaseLLMService, LLMConfig
import logging

logger = logging.getLogger(__name__)


class AnthropicLLMService(BaseLLMService):
    """Anthropic Claude LLM 服务实现"""
    
    def _initialize_client(self):
        """初始化 Anthropic 客户端"""
        import anthropic
        self.client = anthropic.AsyncAnthropic(
            api_key=self.config.api_key
        )
        logger.info(f"Anthropic client initialized with model: {self.config.model_name}")
    
    async def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
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
            # 转换对话历史格式
            messages = []
            
            if conversation_history:
                # Anthropic 不在 history 中包含 system message
                messages = conversation_history
            
            # 添加当前用户消息
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # 调用 Anthropic API
            response = await self.client.messages.create(
                model=self.config.model_name,
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature),
                system=system_message,  # type: ignore[arg-type]
                messages=messages  # type: ignore[arg-type]
            )
            
            # 提取生成的文本
            generated_text = response.content[0].text  # type: ignore[attr-defined]
            
            logger.debug(f"Generated {len(generated_text)} characters")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}", exc_info=True)
            raise
    
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_message: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
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
            # 转换对话历史格式
            messages = []
            
            if conversation_history:
                messages = conversation_history
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # 调用 Anthropic API with tools
            response = await self.client.messages.create(
                model=self.config.model_name,
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature),
                system=system_message,  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
                tools=tools  # type: ignore[arg-type]
            )
            
            # 提取响应信息
            content_blocks = response.content
            generated_text = ""
            tool_calls = []
            
            for block in content_blocks:
                if block.type == "text":
                    generated_text += block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        "name": block.name,
                        "input": block.input
                    })
            
            return {
                "response": generated_text,
                "tool_calls": tool_calls if tool_calls else None,
                "finish_reason": response.stop_reason,
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Anthropic API error with tools: {e}", exc_info=True)
            raise
