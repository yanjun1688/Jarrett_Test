"""
知识检索Agent
专门用于查询和检索测试知识库
"""
from typing import Optional, Dict, Any, List
import logging
from asgiref.sync import sync_to_async

from ..llm.base_llm import BaseLLMService, LLMProvider
from ..rag.rag_retriever_service import RAGRetriever, DjangoORMRAGRetriever

logger = logging.getLogger(__name__)


class KnowledgeRAGAgent:
    """知识检索Agent"""

    def __init__(
        self,
        llm_service: Optional[BaseLLMService] = None,
        rag_retriever: Optional[RAGRetriever] = None
    ):
        """
        初始化知识检索Agent

        Args:
            llm_service: LLM服务（可选）
            rag_retriever: RAG检索器（可选）
        """
        if llm_service is None:
            llm_service = BaseLLMService(provider=LLMProvider.OPENAI)

        self.llm_service = llm_service
        self.rag_retriever = rag_retriever
    
    async def initialize(self) -> None:
        """
        初始化KnowledgeRAGAgent
        """
        logger.info("Initializing KnowledgeRAGAgent")
        
        # 初始化LLM服务（如果存在且支持初始化）
        if self.llm_service and hasattr(self.llm_service, 'initialize'):
            await self.llm_service.initialize()
        
        # 初始化RAG检索器（如果存在且支持初始化）
        if self.rag_retriever and hasattr(self.rag_retriever, 'initialize'):
            await self.rag_retriever.initialize()
        
        logger.info("KnowledgeRAGAgent initialization complete")
    
    async def cleanup(self) -> None:
        """
        清理KnowledgeRAGAgent资源
        """
        logger.info("Cleaning up KnowledgeRAGAgent")
        
        # 清理RAG检索器（如果存在且支持清理）
        if self.rag_retriever and hasattr(self.rag_retriever, 'cleanup'):
            await self.rag_retriever.cleanup()
        
        # 清理LLM服务（如果存在且支持清理）
        if self.llm_service and hasattr(self.llm_service, 'cleanup'):
            await self.llm_service.cleanup()
        
        logger.info("KnowledgeRAGAgent cleanup complete")
    
    async def query(
        self,
        query: str,
        top_k: int = 5,
        document_type: Optional[str] = None,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        查询知识库

        Args:
            query: 查询文本
            top_k: 返回结果数量
            document_type: 文档类型过滤
            use_llm: 是否使用LLM生成回答

        Returns:
            查询结果
            {
                "success": bool,
                "answer": str,  # LLM生成的答案
                "documents": List[Dict],  # 检索到的文档
                "error": Optional[str]
            }
        """
        if not self.rag_retriever:
            return {
                "success": False,
                "answer": "",
                "documents": [],
                "error": "Knowledge retriever not available"
            }

        try:
            # 检索文档
            if document_type:
                documents = await self.rag_retriever.retrieve_by_type(query, document_type, top_k)
            else:
                documents = await self.rag_retriever.retrieve(query, top_k)

            if not documents:
                return {
                    "success": True,
                    "answer": "未找到相关文档",
                    "documents": [],
                    "metadata": {"retrieved_count": 0}
                }

            # 如果不需要LLM，直接返回文档
            if not use_llm:
                return {
                    "success": True,
                    "answer": "",
                    "documents": documents,
                    "metadata": {"retrieved_count": len(documents)}
                }

            # 使用LLM生成答案
            answer = await self._generate_answer(query, documents)

            return {
                "success": True,
                "answer": answer,
                "documents": documents,
                "metadata": {
                    "retrieved_count": len(documents),
                    "query_length": len(query)
                }
            }

        except Exception as e:
            logger.error(f"Failed to query knowledge base: {e}")
            return {
                "success": False,
                "answer": "",
                "documents": [],
                "error": str(e)
            }
    
    async def _generate_answer(
        self,
        query: str,
        documents: List[Dict[str, Any]]
    ) -> str:
        """
        使用LLM生成答案
        
        Args:
            query: 查询文本
            documents: 检索到的文档
            
        Returns:
            生成的答案
        """
        # 构建上下文
        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc.get('document', '')
            metadata = doc.get('metadata', {})
            source = metadata.get('file_path', f'Document {i}')
            kb_name = metadata.get('knowledge_base_name', '未知知识库')
            score = doc.get('combined_score', doc.get('distance', 0.0))
            
            context_parts.append(f"[Document {i} - {source}] (知识库: {kb_name}, Score: {score:.3f})")
            context_parts.append(content)
            context_parts.append("")
        
        context_text = "\n".join(context_parts)
        
        # 构建提示
        prompt = f"""请基于以下文档内容回答问题：

---

文档内容：
{context_text}
---

用户问题：
{query}

请提供准确、详细的回答。如果文档中没有相关信息，请说明。引用具体的文档和内容。"""
        
        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system_message="你是一个知识检索助手，负责基于提供的文档回答用户问题。请保持准确、客观。"
            )
            
            return response
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return "生成答案时出错，请查看检索到的文档。"
    
    async def get_best_practices(
        self,
        topic: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        获取测试最佳实践

        Args:
            topic: 主题（如 "API testing", "UI testing"）
            top_k: 返回结果数量

        Returns:
            最佳实践结果
        """
        if not self.rag_retriever:
            return {
                "success": False,
                "answer": "",
                "documents": [],
                "error": "Knowledge retriever not available"
            }
        query = f"best practices for {topic} testing"
        return await self.query(
            query=query,
            top_k=top_k,
            document_type="best_practice"
        )
    
    async def get_code_examples(
        self,
        description: str,
        language: Optional[str] = None,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        获取代码示例

        Args:
            description: 代码描述
            language: 编程语言
            top_k: 返回结果数量

        Returns:
            代码示例结果
        """
        query = f"code example for {description}"

        if not self.rag_retriever:
            return {
                "success": False,
                "examples": [],
                "error": "Knowledge retriever not available"
            }

        try:
            documents = await self.rag_retriever.retrieve_code_examples(query, language, top_k)

            return {
                "success": True,
                "examples": documents,
                "metadata": {"retrieved_count": len(documents)}
            }

        except Exception as e:
            logger.error(f"Failed to get code examples: {e}")
            return {
                "success": False,
                "examples": [],
                "error": str(e)
            }
    
    async def get_test_patterns(
        self,
        scenario: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        获取测试模式

        Args:
            scenario: 测试场景
            top_k: 返回结果数量

        Returns:
            测试模式结果
        """
        if not self.rag_retriever:
            return {
                "success": False,
                "answer": "",
                "documents": [],
                "error": "Knowledge retriever not available"
            }
        query = f"test patterns for {scenario}"
        return await self.query(
            query=query,
            top_k=top_k,
            document_type="test_pattern"
        )
    
    async def get_api_test_cases(
        self,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        获取API历史测试用例

        检索与指定API端点相关的历史测试用例，用于：
        - 避免重复生成相似的测试用例
        - 复用已有的测试逻辑
        - 保持测试风格一致性

        Args:
            endpoint: API端点路径（如 /api/users）
            method: HTTP方法（GET, POST, PUT, DELETE等）
            top_k: 返回结果数量

        Returns:
            历史测试用例结果
        {
            "success": bool,
            "test_cases": List[Dict],  # 历史测试用例
            "similar_count": int,      # 相似用例数量
            "recommendations": List[str]  # 建议
        }
        """
        if not self.rag_retriever:
            return {
                "success": False,
                "test_cases": [],
                "similar_count": 0,
                "error": "Knowledge retriever not available"
            }
        
        # 如果没有endpoint，进行通用API测试用例检索
        if not endpoint:
            query = "API test case"
        else:
            query_parts = [f"API test case for {endpoint}"]
            if method:
                query_parts.insert(0, method)
            query = " ".join(query_parts)
        
        try:
            # 检索API测试用例
            documents = await self.rag_retriever.retrieve(
                query=query,
                top_k=top_k,
                filters={"type": "api_test_case"}
            )
            
            # 如果没有特定类型的结果，尝试通用检索
            if not documents and self.rag_retriever:
                documents = await self.rag_retriever.retrieve(
                    query=query,
                    top_k=top_k
                )
            
            # 提取测试用例信息
            test_cases = []
            for doc in documents:
                test_case = {
                    "content": doc.get("document", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": doc.get("combined_score", doc.get("distance", 0.0))
                }
                test_cases.append(test_case)
            
            # 生成建议
            recommendations = self._generate_test_recommendations(test_cases, endpoint, method)
            
            return {
                "success": True,
                "test_cases": test_cases,
                "similar_count": len(test_cases),
                "recommendations": recommendations,
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Failed to get API test cases: {e}")
            return {
                "success": False,
                "test_cases": [],
                "similar_count": 0,
                "error": str(e)
            }
    
    def _generate_test_recommendations(
        self,
        test_cases: List[Dict[str, Any]],
        endpoint: Optional[str] = None,
        method: Optional[str] = None
    ) -> List[str]:
        """生成测试建议"""
        recommendations = []
        
        if not test_cases:
            recommendations.append(f"未找到{endpoint}的历史测试用例，将生成新的测试用例")
            return recommendations
        
        recommendations.append(f"找到{len(test_cases)}个相似历史测试用例")
        
        # 分析历史用例
        methods_found = set()
        has_auth = False
        has_validation = False
        
        for tc in test_cases:
            content = tc.get("content", "").lower()
            metadata = tc.get("metadata", {})
            
            if metadata.get("method"):
                methods_found.add(metadata.get("method").upper())
            
            if "auth" in content or "token" in content:
                has_auth = True
            if "validate" in content or "assert" in content:
                has_validation = True
        
        # 生成具体建议
        if method and method.upper() not in methods_found:
            recommendations.append(f"注意：当前请求方法{method}与历史用例中的{methods_found}不同")
        
        if has_auth:
            recommendations.append("历史用例包含认证逻辑，建议保留")
        
        if has_validation:
            recommendations.append("历史用例包含响应验证，建议复用")
        
        return recommendations
    
    async def get_ui_test_cases(
        self,
        page_url: Optional[str] = None,
        page_element: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        获取UI历史测试用例

        检索与指定页面或元素相关的历史UI测试用例

        Args:
            page_url: 页面URL
            page_element: 页面元素（如登录按钮）
            top_k: 返回结果数量

        Returns:
            历史UI测试用例结果
        """
        if not self.rag_retriever:
            return {
                "success": False,
                "test_cases": [],
                "similar_count": 0,
                "error": "Knowledge retriever not available"
            }
        
        query_parts = ["UI test case"]
        if page_url:
            query_parts.append(f"for {page_url}")
        if page_element:
            query_parts.append(f"with {page_element}")
        query = " ".join(query_parts)
        
        try:
            documents = await self.rag_retriever.retrieve(
                query=query,
                top_k=top_k
            )
            
            test_cases = []
            for doc in documents:
                test_case = {
                    "content": doc.get("document", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": doc.get("combined_score", doc.get("distance", 0.0))
                }
                test_cases.append(test_case)
            
            return {
                "success": True,
                "test_cases": test_cases,
                "similar_count": len(test_cases),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Failed to get UI test cases: {e}")
            return {
                "success": False,
                "test_cases": [],
                "similar_count": 0,
                "error": str(e)
            }
    
    async def store_ui_elements(
        self,
        page_url: str,
        elements: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        存储UI页面元素到知识库

        提取页面元素后，将元素信息存储到知识库中，供后续测试生成使用。
        元素信息包括：选择器、标签类型、文本、可交互属性等。

        Args:
            page_url: 页面URL
            elements: 页面元素列表
            metadata: 额外元数据（如页面标题、提取时间等）

        Returns:
            存储结果
        {
            "success": bool,
            "stored_count": int,
            "element_ids": List[str],
            "error": Optional[str]
        }
        """
        if not self.rag_retriever:
            return {
                "success": False,
                "stored_count": 0,
                "error": "Knowledge retriever not available"
            }
        
        try:
            # 构建元素文档
            documents = []
            element_ids = []
            
            for element in elements:
                element_id = element.get("id", f"elem_{len(element_ids)}")
                element_ids.append(element_id)
                
                # 构建元素描述
                selector = element.get("selector", "")
                tag = element.get("tag", "")
                text = element.get("text", "")
                attributes = element.get("attributes", {})
                
                doc_content = f"""UI Element for {page_url}
Element ID: {element_id}
Tag: {tag}
Selector: {selector}
Text: {text}
Attributes: {attributes}
Type: {element.get('type', 'unknown')}
Interactive: {element.get('is_interactive', False)}
"""
                doc_metadata = {
                    "type": "ui_element",
                    "page_url": page_url,
                    "element_id": element_id,
                    "tag": tag,
                    "selector_type": element.get("selector_type", "css"),
                    **(metadata or {})
                }
                
                documents.append({
                    "content": doc_content,
                    "metadata": doc_metadata
                })
            
            # 存储到向量数据库
            if hasattr(self.rag_retriever, 'add_documents'):
                await self.rag_retriever.add_documents(documents)
            
            return {
                "success": True,
                "stored_count": len(documents),
                "element_ids": element_ids,
                "page_url": page_url
            }
            
        except Exception as e:
            logger.error(f"Failed to store UI elements: {e}")
            return {
                "success": False,
                "stored_count": 0,
                "error": str(e)
            }
    
    async def query_ui_elements(
        self,
        page_url: Optional[str] = None,
        element_type: Optional[str] = None,
        is_interactive: Optional[bool] = None,
        top_k: int = 20
    ) -> Dict[str, Any]:
        """
        查询UI元素

        根据条件查询知识库中存储的UI元素。

        Args:
            page_url: 页面URL过滤
            element_type: 元素类型（button, input, link等）
            is_interactive: 是否可交互
            top_k: 返回数量

        Returns:
            查询结果
        """
        if not self.rag_retriever:
            return {
                "success": False,
                "elements": [],
                "error": "Knowledge retriever not available"
            }
        
        # 构建查询字符串
        query_parts = ["UI element"]
        if page_url:
            query_parts.append(f"for {page_url}")
        if element_type:
            query_parts.append(f"type {element_type}")
        if is_interactive is not None:
            query_parts.append("interactive" if is_interactive else "non-interactive")
        
        query = " ".join(query_parts)
        
        try:
            # 构建过滤条件
            filters = {"type": "ui_element"}
            if page_url:
                filters["page_url"] = page_url
            if element_type:
                filters["tag"] = element_type
            
            documents = await self.rag_retriever.retrieve(
                query=query,
                top_k=top_k,
                filters=filters if filters != {"type": "ui_element"} else None
            )
            
            # 解析元素
            elements = []
            for doc in documents:
                content = doc.get("document", "")
                meta = doc.get("metadata", {})
                
                # 解析元素信息
                element_info = self._parse_element_from_doc(content, meta)
                elements.append(element_info)
            
            return {
                "success": True,
                "elements": elements,
                "count": len(elements),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Failed to query UI elements: {e}")
            return {
                "success": False,
                "elements": [],
                "error": str(e)
            }
    
    def _parse_element_from_doc(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """从文档内容解析元素信息"""
        element = {
            "id": metadata.get("element_id"),
            "page_url": metadata.get("page_url"),
            "tag": metadata.get("tag"),
            "selector": metadata.get("selector"),
            "selector_type": metadata.get("selector_type"),
            "metadata": metadata
        }
        
        # 从内容中解析
        lines = content.split("\n")
        for line in lines:
            if ": " in line:
                key, value = line.split(": ", 1)
                key = key.strip().lower().replace(" ", "_")
                if key not in element:
                    element[key] = value.strip()
        
        return element
