"""
Anthropic Claude LLM 服务实现
提供基于 Anthropic API 的 LLM 服务
"""
from typing import Optional, Dict, Any, List
from .base_llm import BaseLLMService
import logging

logger = logging.getLogger(__name__)


class AnthropicLLMService(BaseLLMService):
    """Anthropic Claude LLM 服务实现"""
    
    def _initialize_client(self) -> None:
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
            raw_messages: List[Dict[str, Any]] = []
            if conversation_history:
                raw_messages = list(conversation_history)
            raw_messages.append({"role": "user", "content": prompt})
            messages = self._convert_to_anthropic(raw_messages)
            
            # 调用 Anthropic API
            response = await self.client.messages.create(
                model=self.config.model_name,
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature),
                system=system_message,
                messages=messages,
            )

            # 提取生成的文本 - 只处理 TextBlock 类型
            generated_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    generated_text += block.text
            
            logger.debug(f"Generated {len(generated_text)} characters")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}", exc_info=True)
            raise
    
    @staticmethod
    def _convert_to_anthropic(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将 canonical 格式消息列表转换为 Anthropic API 格式。

        Canonical 格式（内部通用）：
          {"role": "tool", "tool_call_id": "x", "content": "结果"}
          {"role": "assistant", "tool_calls": [{"id": "x", "name": "n", "arguments": {}}]}

        Anthropic API 格式：
          {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": "结果"}]}
          {"role": "assistant", "content": [{"type": "text", "text": "..."}, {"type": "tool_use", "id": "x", "name": "n", "input": {}}]}
        """
        anthropic_messages: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls")
            tool_call_id = msg.get("tool_call_id")

            if role == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_call_id or "",
                        "content": content or "",
                    }],
                })

            elif role == "assistant" and tool_calls:
                blocks: List[Dict[str, Any]] = []
                if content:
                    blocks.append({"type": "text", "text": content})
                for tc in tool_calls:
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": tc.get("name", ""),
                        "input": tc.get("arguments", {}),
                    })
                anthropic_messages.append({"role": "assistant", "content": blocks})

            else:
                anthropic_messages.append(msg)

        return anthropic_messages

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
            # Canonical → Anthropic block 格式
            raw_messages: List[Dict[str, Any]] = []
            if conversation_history:
                raw_messages = list(conversation_history)
            if prompt:
                raw_messages.append({"role": "user", "content": prompt})
            messages = self._convert_to_anthropic(raw_messages)
            
            # 调用 Anthropic API with tools
            response = await self.client.messages.create(
                model=self.config.model_name,
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature),
                system=system_message,
                messages=messages,
                tools=tools,
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
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
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
