"""
上下文感知LLM服务
集成RAG知识库，支持长上下文管理
"""
from typing import Optional, Dict, Any, List, Union
from .base_llm import BaseLLMService, LLMConfig
import logging

logger = logging.getLogger(__name__)


class ContextAwareLLMService(BaseLLMService):
    """上下文感知的LLM服务"""
    
    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        rag_retriever: Optional[Any] = None,
        max_context_length: int = 8000,
        context_compression: bool = True
    ) -> None:
        """
        初始化上下文感知LLM服务
        
        Args:
            config: LLM配置
            rag_retriever: RAG检索器实例
            max_context_length: 最大上下文长度（Token数）
            context_compression: 是否压缩上下文
        """
        super().__init__(config)
        self.rag_retriever = rag_retriever
        self.max_context_length = max_context_length
        self.context_compression = context_compression
        self.conversation_history: List[Dict[str, Any]] = []
    
    def _initialize_client(self) -> None:
        """Initialize client - ContextAwareLLMService wraps another LLM service"""
        pass
    
    async def generate_with_rag(
        self,
        query: str,
        system_message: Optional[str] = None,
        top_k: int = 3,
        use_rag: bool = True,
        **kwargs: Any
    ) -> str:
        """
        使用RAG增强生成
        
        Args:
            query: 查询文本
            system_message: 系统消息
            top_k: 检索的文档数量
            use_rag: 是否使用RAG
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        # 1. 如果启用RAG，检索相关知识
        retrieved_docs = []
        if use_rag and self.rag_retriever:
            try:
                retrieved_docs = await self.rag_retriever.retrieve(query, top_k=top_k)
                logger.info(f"Retrieved {len(retrieved_docs)} documents from RAG")
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}, proceeding without RAG")
        
        # 2. 构建增强的提示
        enhanced_prompt = self._build_rag_enhanced_prompt(query, retrieved_docs)
        
        # 3. 生成响应
        response = await self.generate(
            prompt=enhanced_prompt,
            system_message=system_message,
            conversation_history=self.conversation_history,
            **kwargs
        )
        
        # 4. 更新对话历史
        self._update_conversation_history(query, response, retrieved_docs)
        
        return response
    
    def _build_rag_enhanced_prompt(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        构建RAG增强的提示
        
        Args:
            query: 原始查询
            retrieved_docs: 检索到的文档
            
        Returns:
            增强的提示文本
        """
        if not retrieved_docs:
            return query
        
        # 构建上下文部分
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            source = metadata.get('file_path', f'Document {i}')
            
            context_parts.append(f"[Document {i} - {source}]")
            context_parts.append(content)
            context_parts.append("")
        
        context_text = "\n".join(context_parts)
        
        # 组合最终提示
        enhanced_prompt = f"""请基于以下上下文信息回答问题：

---

上下文信息：
{context_text}
---

用户问题：
{query}

请基于上下文信息给出准确、详细的回答。如果上下文中没有相关信息，请诚实说明。"""
        
        return enhanced_prompt
    
    def _update_conversation_history(
        self,
        query: str,
        response: str,
        retrieved_docs: List[Dict[str, Any]]
    ) -> None:
        """
        更新对话历史
        
        Args:
            query: 用户查询
            response: 模型响应
            retrieved_docs: 检索到的文档
        """
        # 添加用户消息
        self.conversation_history.append({
            "role": "user",
            "content": query,
            "retrieved_docs": len(retrieved_docs)
        })
        
        # 添加助手消息
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        # 管理历史长度（避免超出Token限制）
        self._trim_conversation_history()
    
    def _trim_conversation_history(self) -> None:
        """裁剪对话历史以适应Token限制"""
        if not self.conversation_history:
            return
        
        # 粗略估算Token数
        total_tokens = 0
        kept_messages: List[Dict[str, Any]] = []
        
        # 从后往前遍历，保留最近的消息
        for message in reversed(self.conversation_history):
            message_tokens = len(message['content']) // 4  # 粗略估算
            
            if total_tokens + message_tokens > self.max_context_length:
                break
            
            kept_messages.insert(0, message)
            total_tokens += message_tokens
        
        self.conversation_history = kept_messages
        logger.debug(f"Trimmed conversation history to {len(self.conversation_history)} messages (~{total_tokens} tokens)")
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def get_history_summary(self) -> Dict[str, Any]:
        """
        获取对话历史摘要
        
        Returns:
            对话历史摘要信息
        """
        return {
            "message_count": len(self.conversation_history),
            "user_messages": len([m for m in self.conversation_history if m['role'] == 'user']),
            "assistant_messages": len([m for m in self.conversation_history if m['role'] == 'assistant']),
            "estimated_tokens": sum(len(m['content']) // 4 for m in self.conversation_history)
        }
