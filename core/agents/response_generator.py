"""
Response Generator - Generates responses for Chatbot

This module handles the generation of responses based on user input,
detected intent, retrieved knowledge, and LLM capabilities.
"""
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false, reportReturnType=false
from typing import Dict, Any, Optional, List
import logging

from core.agents.llm.base_llm import BaseLLMService

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generates responses for chatbot interactions
    
    This class:
    - Formats context for LLM
    - Generates natural language responses
    - Handles tool execution results
    - Provides suggested actions
    """
    
    def __init__(self, llm_service: BaseLLMService):
        """
        Initialize Response Generator
        
        Args:
            llm_service: LLM service for response generation
        """
        self.llm_service = llm_service
        self.logger = logging.getLogger(__name__)
    
    async def generate_response(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a response based on context
         
        Args:
            context: Context dictionary containing:
                - message: User's message
                - intent: Detected intent
                - context: Additional execution context
                - knowledge: Retrieved knowledge entries
                - conversation_history: Previous conversation messages
                 
        Returns:
            Response dictionary containing:
                - text: Generated response text
                - tool_used: Whether tool was used
                - tool_result: Tool execution result (if any)
                - references: Knowledge references used
        """
        message = context.get("message", "")
        intent = context.get("intent", "chat")
        additional_context = context.get("context", {})
        knowledge = context.get("knowledge", [])
        conversation_history = context.get("conversation_history", [])
        
        prompt = self._build_prompt(message, intent, knowledge, additional_context, conversation_history)
        
        # Call LLM
        try:
            # 确保 llm_service 有一个 generate_response 方法
            response = await self.llm_service.generate_response(prompt)
            
            # Parse response
            parsed_response = self._parse_llm_response(response)
            
            # Check if tool should be called
            if parsed_response.get("tool_call"):
                tool_result = await self._execute_tool(parsed_response["tool_call"])
                parsed_response["tool_result"] = tool_result
                
                # Generate follow-up response
                follow_up_prompt = self._build_tool_follow_up_prompt(
                    original_message=message,
                    tool_response=tool_result
                )
                
                follow_up_response = await self.llm_service.generate_response(follow_up_prompt)
                follow_up_parsed = self._parse_llm_response(follow_up_response)
                
                # Combine results - ensure tool_used is preserved
                parsed_response.update({
                    "text": follow_up_parsed["text"],
                    "tool_used": parsed_response.get("tool_used")  # 确保保留工具使用标识
                })
            else:
                # Explicitly set tool_used based on the parsed response
                parsed_response["tool_used"] = parsed_response.get("tool_used", False)
                
            return parsed_response
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}", exc_info=True)
            
            # Return fallback response
            return {
                "text": self._get_fallback_response(intent, message),
                "tool_used": False,
                "tool_result": None,
                "references": []
            }
    
    def _build_prompt(
        self,
        message: str,
        intent: str,
        knowledge: List[Dict[str, Any]],
        context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Build prompt for LLM with intelligent knowledge usage.
        
        Args:
            message: User's message
            intent: Detected intent
            knowledge: Retrieved knowledge
            context: Additional context
            conversation_history: Previous conversation messages
            
        Returns:
            Formatted prompt string
        """
        history_section = ""
        if conversation_history:
            history_section = "\n\n### 对话历史\n以下是之前的对话记录，请参考上下文回答用户问题：\n\n"
            for msg in conversation_history[-10:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    history_section += f"用户: {content}\n"
                else:
                    history_section += f"助手: {content}\n"
            history_section += "\n"
        
        knowledge_context = ""
        if knowledge:
            knowledge_context = "\n\n### 知识库检索结果\n"
            knowledge_context += "以下是可能相关的知识库内容。请根据相关性决定是否使用：\n\n"
            for i, entry in enumerate(knowledge[:5], 1):
                content = entry.get("content", entry.get("document", ""))
                metadata = entry.get("metadata", {})
                score = entry.get("combined_score", entry.get("distance", 0))
                source = metadata.get("file_path", metadata.get("source", "未知来源"))
                knowledge_context += f"---\n**[{i}] 来源: {source}** (相关度: {score:.2f})\n{content}\n"
            knowledge_context += "\n**重要提示**: 只有当知识库内容与用户问题直接相关时才引用。如果无关，请忽略并直接回答。\n"
        
        context_info = ""
        if context:
            context_info = "\n\n### 执行上下文\n"
            for key, value in context.items():
                if key not in ["user_id", "provider"]:
                    context_info += f"- {key}: {value}\n"
        
        prompt = f"""你是一个智能测试助手，帮助用户生成和执行测试。
{history_section}
## 用户消息
{message}

## 意图分析
意图类型: {intent}
{knowledge_context}
{context_info}
## 回复指南
1. **知识库使用**: 如果知识库内容与用户问题相关，请引用并说明来源；如果无关，请忽略并直接回答
2. **操作建议**: 如果用户需要执行操作，请明确说明需要的步骤
3. **简洁明了**: 保持回复简洁、专业、有条理
4. **后续建议**: 如有建议的后续操作，请列出

请直接回复用户：
"""
        
        return prompt
    
    def _parse_llm_response(self, response: Any) -> Dict[str, Any]:
        """
        Parse LLM response
         
        Args:
            response: Raw response from LLM
             
        Returns:
            Parsed response dictionary
        """
        # 如果是字符串，直接返回
        if isinstance(response, str):
            return {
                "text": response,
                "tool_used": None,
                "tool_call": None,
                "tool_result": None,
                "references": []
            }
        
        # 尝试获取text属性或键值
        text_value = ""
        if hasattr(response, 'text'):
            text_value = getattr(response, 'text', '')
        elif isinstance(response, dict):
            text_value = response.get("text", str(response))
        elif response is None:
            text_value = ""
        else:
            text_value = str(response)
        
        # 处理tool_used、tool_call、tool_result和references
        tool_used = None
        tool_call = None
        tool_result = None
        references = []
        
        if hasattr(response, 'tool_used'):
            tool_used = getattr(response, 'tool_used', None)
        elif isinstance(response, dict):
            if 'tool_used' in response:
                tool_used = response.get('tool_used')
        
        if hasattr(response, 'tool_call'):
            tool_call = getattr(response, 'tool_call', None)
        elif isinstance(response, dict):
            tool_call = response.get('tool_call', None)
        
        if hasattr(response, 'tool_result'):
            tool_result = getattr(response, 'tool_result', None)
        elif isinstance(response, dict):
            tool_result = response.get('tool_result', None)
        
        if hasattr(response, 'references'):
            references = getattr(response, 'references', [])
        elif isinstance(response, dict):
            references = response.get('references', [])
            
        # 尝试从response对象整体中直接获取这些属性
        if isinstance(response, dict):
            return {
                "text": text_value,
                "tool_used": response.get("tool_used") if "tool_used" in response else tool_used,
                "tool_call": response.get("tool_call") if "tool_call" in response else tool_call,
                "tool_result": response.get("tool_result") if "tool_result" in response else tool_result,
                "references": response.get("references", []) if "references" in response else references
            }
        else:
            # 对于非dict对象（如模拟对象），主要从属性获取
            return {
                "text": text_value,
                "tool_used": tool_used,
                "tool_call": tool_call,
                "tool_result": tool_result,
                "references": references
            }
    
    def _extract_text(self, response: Any) -> str:
        """Extract text from response"""
        if isinstance(response, dict):
            return response.get("text", str(response))
        return str(response)
    
    def _get_fallback_response(self, intent: str, message: str) -> str:
        """
        Get fallback response
        
        Args:
            intent: Detected intent
            message: User's message
            
        Returns:
            Fallback response text
        """
        fallback_responses = {
            "chat": "我可以帮您生成测试脚本、查询知识或执行测试。请告诉我您需要什么？",
            "generate_ui_test": "我可以帮您生成UI测试脚本。请描述您要测试的功能或提供URL。",
            "generate_api_test": "我可以帮您生成API测试脚本。请提供API的描述或OpenAPI文档。",
            "query_knowledge": "我可以帮您查找测试相关的最佳实践和示例。请告诉我您想了解什么？",
            "execute_test": "我可以帮您执行测试用例。请提供测试ID或描述。",
            "default": f"我理解您想 '{message}'。请提供更多信息，我将更好地帮助您。"
        }
        
        return fallback_responses.get(intent, fallback_responses["default"])
    
    async def _execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool
        
        Args:
            tool_call: Tool call information
            
        Returns:
            Tool execution result
        """
        # This would typically call the tool orchestrator
        # For now, return placeholder
        return {
            "success": True,
            "data": {"message": "Tool execution placeholder"},
            "execution_time": 0.0
        }
    
    def _build_tool_follow_up_prompt(
        self,
        original_message: str,
        tool_response: Dict[str, Any]
    ) -> str:
        """
        Build prompt for tool follow-up response
        
        Args:
            original_message: User's original message
            tool_response: Tool execution result
            
        Returns:
            Follow-up prompt
        """
        return f"""用户原始请求: {original_message}

工具执行结果:
{tool_response}

请根据工具执行结果，生成一个自然语言的回复总结。"""
    
    async def generate_suggested_actions(
        self,
        intent: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Generate suggested actions based on intent
        
        Args:
            intent: Detected intent
            context: Execution context
            
        Returns:
            List of suggested actions
        """
        actions = []
        
        if intent == "chat":
            actions = [
                {"type": "generate_ui_test", "label": "生成UI测试"},
                {"type": "generate_api_test", "label": "生成API测试"},
                {"type": "execute_test", "label": "执行测试"},
                {"type": "query_knowledge", "label": "查询知识"}
            ]
        elif intent == "generate_ui_test":
            actions = [
                {"type": "execute_test", "label": "执行测试"},
                {"type": "modify_test", "label": "修改测试"}
            ]
        elif intent == "generate_api_test":
            actions = [
                {"type": "execute_test", "label": "执行测试"},
                {"type": "modify_test", "label": "修改测试"}
            ]
        
        return actions
    
    async def generate(
        self,
        message: str,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成响应（简化版本）
        
        Args:
            message: 用户消息
            intent: 意图类型
            context: 上下文信息
            
        Returns:
            响应字典
        """
        context = context or {}
        
        try:
            # 构建提示
            prompt = f"用户消息: {message}\n意图: {intent}"
            if context.get("suggested_actions"):
                prompt += f"\n建议操作: {context['suggested_actions']}"
            
            # 调用LLM
            response = await self.llm_service.generate(
                prompt=prompt,
                system_message="你是一个测试助手，负责回答用户问题。"
            )
            
            return {
                "text": response,
                "intent": intent,
                "suggested_actions": context.get("suggested_actions", [])
            }
            
        except Exception as e:
            self.logger.error(f"生成响应失败: {e}")
            return {
                "text": f"处理请求时出错: {str(e)}",
                "intent": intent,
                "error": str(e)
            }


if __name__ == "__main__":
    # Simple test
    generator = ResponseGenerator(llm_service=None)
    
    context = {
        "message": "帮我生成UI测试脚本",
        "intent": "generate_ui_test",
        "context": {},
        "knowledge": []
    }
    
    print("Response generator created successfully")
