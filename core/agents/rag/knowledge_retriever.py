"""
Knowledge Retriever - Core retrieval component

Combines EmbeddingService and ChromaVectorStore for knowledge retrieval.
Uses global collection with metadata-based filtering.
"""
from typing import List, Dict, Any, Optional

from core.agents.rag.embedding_service import EmbeddingService
from core.agents.rag.vector_store import ChromaVectorStore


class KnowledgeRetriever:
    """
    Knowledge Retriever
    
    Combines EmbeddingService and ChromaVectorStore.
    Uses global collection with metadata-based filtering.
    
    Retrieval modes:
    1. search: Global semantic search with optional filters
       - doc_types: Filter by document type
       - project_id: Filter by project
       - boost_project: Prioritize results from specified project
    """
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = ChromaVectorStore()
    
    def add_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        doc_id: str
    ) -> None:
        """Add a single document"""
        embedding = self.embedding_service.embed_query(content)
        self.vector_store.add_documents(
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[doc_id]
        )
    
    def add_documents_batch(
        self,
        contents: List[str],
        metadatas: List[Dict[str, Any]],
        doc_ids: List[str]
    ) -> None:
        """Add multiple documents in batch"""
        embeddings = self.embedding_service.embed_texts(contents)
        self.vector_store.add_documents(
            documents=contents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=doc_ids
        )
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        doc_types: Optional[List[str]] = None,
        project_id: Optional[int] = None,
        boost_project: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Semantic search with optional filters
        
        Args:
            query: Search query
            top_k: Number of results
            doc_types: Filter by document types
            project_id: Filter by project ID
            boost_project: If True, prioritize results from project_id
            
        Returns:
            List of matching documents
        """
        query_embedding = self.embedding_service.embed_query(query)
        
        where = self._build_where_clause(doc_types, project_id)
        
        n_results = top_k * 2 if boost_project and project_id else top_k
        
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where if where else None
        )
        
        formatted = self._format_results(results)
        
        if boost_project and project_id:
            formatted = self._boost_project_results(formatted, project_id, top_k)
        
        return formatted[:top_k]
    
    def semantic_search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Pure semantic search (backward compatibility)
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            List of matching documents
        """
        return self.search(query, top_k=top_k)
    
    def search_tests(
        self,
        query: str,
        source_types: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Test case search (backward compatibility)
        
        Args:
            query: Search query
            source_types: List of source types to filter
            top_k: Number of results
            
        Returns:
            List of matching test cases
        """
        return self.search(query, top_k=top_k, doc_types=source_types)
    
    def search_documents(
        self,
        query: str,
        document_types: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Document search (backward compatibility)
        
        Args:
            query: Search query
            document_types: List of document types to filter
            top_k: Number of results
            
        Returns:
            List of matching documents
        """
        return self.search(query, top_k=top_k, doc_types=document_types)
    
    def delete_document(self, doc_id: str) -> None:
        """Delete a single document"""
        self.vector_store.delete(ids=[doc_id])
    
    def delete_document_chunks(self, id_prefix: str) -> int:
        """
        Delete all chunks of a document
        
        Args:
            id_prefix: Document ID prefix, e.g., "doc_123_"
            
        Returns:
            Number of deleted chunks
        """
        return self.vector_store.delete_by_prefix(id_prefix)
    
    def _build_where_clause(
        self,
        doc_types: Optional[List[str]],
        project_id: Optional[int]
    ) -> Optional[Dict]:
        """Build ChromaDB where clause from filters"""
        conditions = []
        
        if doc_types and len(doc_types) == 1:
            conditions.append({"doc_type": doc_types[0]})
        elif doc_types and len(doc_types) > 1:
            conditions.append({"doc_type": {"$in": doc_types}})
        
        if project_id is not None:
            conditions.append({"project_id": project_id})
        
        if not conditions:
            return None
        
        if len(conditions) == 1:
            return conditions[0]
        
        return {"$and": conditions}
    
    def _boost_project_results(
        self,
        results: List[Dict[str, Any]],
        project_id: int,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Boost results from specified project
        
        Sorts results so that documents from the specified project
        appear first, while maintaining relative order within each group.
        """
        project_results = []
        other_results = []
        
        for r in results:
            if r.get('metadata', {}).get('project_id') == project_id:
                project_results.append(r)
            else:
                other_results.append(r)
        
        boosted = project_results + other_results
        return boosted
    
    def _format_results(self, results: Dict) -> List[Dict[str, Any]]:
        """Format query results"""
        formatted = []
        if not results['ids'] or not results['ids'][0]:
            return formatted
        
        for i, doc_id in enumerate(results['ids'][0]):
            formatted.append({
                'id': doc_id,
                'content': results['documents'][0][i] if results['documents'] else None,
                'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                'distance': results['distances'][0][i] if results['distances'] else None
            })
        return formatted