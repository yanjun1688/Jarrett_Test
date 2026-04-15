"""
RAG Retriever Service - Abstraction for dependency injection

This module provides a clean abstraction for RAG retrieval that can be
injected into agents, avoiding tight coupling with Django ORM.
"""
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class RAGRetriever(ABC):
    """
    Abstract base class for RAG retrieval
    """

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents

        Args:
            query: Search query
            top_k: Number of results to return
            **kwargs: Additional parameters

        Returns:
            List of retrieved documents with metadata
        """
        pass

    @abstractmethod
    async def retrieve_by_type(
        self,
        query: str,
        document_type: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents by type

        Args:
            query: Search query
            document_type: Document type filter
            top_k: Number of results to return

        Returns:
            List of retrieved documents
        """
        pass

    @abstractmethod
    async def retrieve_code_examples(
        self,
        query: str,
        language: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve code examples

        Args:
            query: Search query
            language: Programming language filter
            top_k: Number of results to return

        Returns:
            List of code examples
        """
        pass
    
    @abstractmethod
    async def add_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Add documents to the knowledge base
        
        Args:
            documents: List of documents to add
                    Each document should have 'content' and 'metadata' keys
            
        Returns:
            Result of the operation
        """
        pass
    
    async def initialize(self) -> None:
        """Initialize RAG retriever"""
        logger.info("Initializing RAG retriever")
    
    async def cleanup(self) -> None:
        """Cleanup RAG retriever resources"""
        logger.info("Cleanup RAG retriever")


class DjangoORMRAGRetriever(RAGRetriever):
    """
    Django ORM-based RAG retriever implementation

    This implementation integrates MySQL metadata storage and ChromaDB vector retrieval.
    Uses the new KnowledgeRetriever for vector operations.
    """

    def __init__(
        self,
        project_id: Optional[int] = None,
        knowledge_base_id: Optional[int] = None
    ):
        """
        Initialize Django ORM RAG retriever

        Args:
            project_id: Project ID (preferred)
            knowledge_base_id: Knowledge base ID (fallback)
        """
        self.project_id = project_id
        self.knowledge_base_id = knowledge_base_id
        self._retriever = None

    def _get_project_id(self) -> Optional[int]:
        """Get project_id from knowledge_base if needed"""
        if self.project_id:
            return self.project_id
        
        if self.knowledge_base_id:
            from core.models.knowledge import KnowledgeBase
            try:
                kb = KnowledgeBase.objects.get(id=self.knowledge_base_id)
                return kb.project_id
            except KnowledgeBase.DoesNotExist:
                return None
        return None

    @property
    def retriever(self):
        """Lazy initialize ChromaDB retriever"""
        if self._retriever is None:
            from core.agents.rag.knowledge_retriever import KnowledgeRetriever
            self._retriever = KnowledgeRetriever()
        return self._retriever

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents

        Args:
            query: Search query
            top_k: Number of results to return
            **kwargs: Additional parameters

        Returns:
            List of retrieved documents
        """
        if not self.retriever:
            logger.warning("Retriever not initialized")
            return []

        try:
            results = self.retriever.search(
                query,
                top_k=top_k,
                project_id=self.project_id,
                hybrid_search=True
            )
            
            return [
                {
                    'document': r.get('content', ''),
                    'metadata': r.get('metadata', {}),
                    'distance': r.get('distance'),
                    'combined_score': r.get('combined_score', 1.0 - (r.get('distance') or 0.0)),
                    'keyword_score': r.get('keyword_score', 0.0),
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Failed to retrieve: {e}")
            return []

    async def retrieve_by_type(
        self,
        query: str,
        document_type: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents by type

        Args:
            query: Search query
            document_type: Document type filter
            top_k: Number of results to return

        Returns:
            List of retrieved documents
        """
        return await self.retrieve(query, top_k, filters={'type': document_type})

    async def retrieve_code_examples(
        self,
        query: str,
        language: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve code examples

        Args:
            query: Search query
            language: Programming language filter
            top_k: Number of results to return

        Returns:
            List of code examples
        """
        if not self.retriever:
            logger.warning("Retriever not initialized")
            return []

        try:
            results = self.retriever.search(
                query,
                top_k=top_k,
                doc_types=['code'],
                project_id=self.project_id,
                hybrid_search=True
            )
            
            filtered = results
            if language:
                filtered = [r for r in results if r.get('metadata', {}).get('language') == language]
            
            return [
                {
                    'document': r.get('content', ''),
                    'metadata': r.get('metadata', {}),
                    'distance': r.get('distance'),
                    'combined_score': r.get('combined_score', 1.0 - (r.get('distance') or 0.0)),
                }
                for r in filtered
            ]
        except Exception as e:
            logger.error(f"Failed to retrieve code examples: {e}")
            return []

    async def add_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Add documents to the knowledge base

        Args:
            documents: List of documents to add
                    Each document should have 'content' and 'metadata' keys

        Returns:
            Result of the operation
        """
        if not self.retriever:
            return {"success": False, "error": "Retriever not initialized"}
        
        try:
            contents = [doc.get('content', '') for doc in documents]
            metadatas = [doc.get('metadata', {}) for doc in documents]
            
            import uuid
            doc_ids = [f"doc_{uuid.uuid4().hex[:8]}" for _ in documents]
            
            self.retriever.add_documents_batch(contents, metadatas, doc_ids)
            
            return {"success": True, "added_count": len(documents)}
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return {"success": False, "error": str(e)}


class MockRAGRetriever(RAGRetriever):
    """
    Mock RAG retriever for testing purposes

    Returns predefined results without requiring a real knowledge base.
    """

    def __init__(self, mock_results: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize mock retriever

        Args:
            mock_results: Predefined results to return
        """
        self.mock_results = mock_results or []

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Return mock results

        Args:
            query: Search query (ignored)
            top_k: Number of results to return
            **kwargs: Additional parameters (ignored)

        Returns:
            List of mock documents
        """
        return self.mock_results[:top_k]

    async def retrieve_by_type(
        self,
        query: str,
        document_type: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Return mock results filtered by type

        Args:
            query: Search query (ignored)
            document_type: Document type filter
            top_k: Number of results to return

        Returns:
            List of mock documents
        """
        filtered = [
            r for r in self.mock_results
            if r.get('metadata', {}).get('type') == document_type
        ]
        return filtered[:top_k]

    async def retrieve_code_examples(
        self,
        query: str,
        language: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Return mock code examples

        Args:
            query: Search query (ignored)
            language: Programming language filter
            top_k: Number of results to return

        Returns:
            List of mock code examples
        """
        filtered = [
            r for r in self.mock_results
            if r.get('metadata', {}).get('language') == language or language is None
        ]
        return filtered[:top_k]

    async def add_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Add documents to the knowledge base

        Args:
            documents: List of documents to add
                    Each document should have 'content' and 'metadata' keys

        Returns:
            Result of the operation
        """
        return {
            "success": True,
            "added_count": len(documents),
            "status": "documents saved in mock retriever"
        }