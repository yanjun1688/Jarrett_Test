"""
Knowledge base API views
"""
from __future__ import annotations
from typing import Any, Dict
from rest_framework.request import Request

from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import logging
import json
from typing import Optional

from core.agents.rag.knowledge_rag_agent import KnowledgeRAGAgent
from core.models import Project, KnowledgeBase, KnowledgeDocument
from core.services.document_converter import DocumentConverter
from core.tasks import sync_document_to_chroma
from shared.constants import DocType
from shared.exceptions import ValidationError, ConfigurationError
from shared.utils.validation import validate_required_fields

logger = logging.getLogger(__name__)


class QueryKnowledgeView(APIView):
    """
    Query knowledge base
    POST /api/v1/knowledge/query
    """
    permission_classes = [IsAuthenticated]
    
    async def post(self, request: Request) -> Response:
        """Query knowledge base"""
        try:
            data = request.data  # type: Dict[str, Any]
            query = data.get('query')  # type: ignore[attr-defined]
            project_id = data.get('project_id')  # type: ignore[attr-defined]
            top_k = data.get('top_k', 5)  # type: ignore[attr-defined]
            document_type = data.get('document_type')  # type: ignore[attr-defined]
            use_llm = data.get('use_llm', True)  # type: ignore[attr-defined]
            filters = data.get('filters', {})  # type: ignore[attr-defined]
            
            # Validate required fields
            validate_required_fields(data, ['query', 'project_id'])
            
            if query and not query.strip():
                return Response(
                    {'error': 'Query cannot be empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Direct async execution
            result = await self._async_query(
                query=query,
                project_id=project_id,
                top_k=top_k,
                document_type=document_type,
                use_llm=use_llm,
                filters=filters
            )
            
            return Response(result)
            
        except ValidationError as e:
            logger.warning(f"Validation error in knowledge query: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error querying knowledge base: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def _async_query(
        self,
        query: str,
        project_id: int,
        top_k: int,
        document_type: Optional[str],
        use_llm: bool,
        filters: dict
    ) -> dict:
        """Async query knowledge base"""
        try:
            # Initialize knowledge agent
            # Note: In production, you would load project-specific configuration
            agent = KnowledgeRAGAgent(
                llm_service=None,  # Would be injected in production
                rag_retriever=None,  # Would be injected in production
                config={
                    'project_id': project_id,
                    'timeout': 30
                }
            )
            
            # Query knowledge base
            result = await agent.query(
                query=query,
                top_k=top_k,
                document_type=document_type,
                use_llm=use_llm,
                filters=filters
            )
            
            return result
            
        except ConfigurationError as e:
            logger.error(f"Configuration error in knowledge query: {str(e)}")
            return {
                'success': False,
                'error': 'Knowledge base not configured',
                'query': query
            }
        except Exception as e:
            logger.error(f"Async query failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query
            }


class BuildKnowledgeBaseView(APIView):
    """
    Build knowledge base
    POST /api/v1/knowledge/build
    """
    permission_classes = [IsAuthenticated]
    
    async def post(self, request: Request) -> Response:
        """Build knowledge base"""
        try:
            data = request.data  # type: Dict[str, Any]
            project_id = data.get('project_id')  # type: ignore[attr-defined]
            name = data.get('name')  # type: ignore[attr-defined]
            description = data.get('description', '')  # type: ignore[attr-defined]
            source_type = data.get('source_type', 'document')  # type: ignore[attr-defined]
            source_path = data.get('source_path')  # type: ignore[attr-defined]
            
            # Validate required fields
            validate_required_fields(data, ['project_id', 'name'])
            
            if source_type == 'document' and not source_path:
                return Response(
                    {'error': 'source_path is required for document source type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Direct async build process
            await self._async_build(
                project_id=project_id,
                name=name,
                description=description,
                source_type=source_type,
                source_path=source_path
            )
            
            return Response({
                'success': True,
                'message': 'Knowledge base build started',
                'project_id': project_id,
                'name': name,
                'status': 'building'
            })
            
        except ValidationError as e:
            logger.warning(f"Validation error in knowledge build: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error building knowledge base: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def _async_build(
        self,
        project_id: int,
        name: str,
        description: str,
        source_type: str,
        source_path: Optional[str]
    ) -> None:
        """Async build knowledge base using async ORM"""
        try:
            logger.info(f"Starting knowledge base build: {name} for project {project_id}")
            
            # Get project using async ORM (Django 5.2+)
            try:
                project = await Project.objects.aget(id=project_id)
            except Project.DoesNotExist:
                raise ValidationError(f"Project {project_id} does not exist")
            
            # Create knowledge base record using async ORM
            knowledge_base = await KnowledgeBase.objects.acreate(
                project=project,
                name=name,
                description=description,
                status='building'
            )
            
            # TODO: In a real implementation, this would:
            # 1. Process documents based on source_type
            # 2. Index documents in vector store
            # 3. Update knowledge base status to 'ready'
            
            # Simulate build process (using asyncio directly since we're in async context)
            import asyncio
            await asyncio.sleep(1)  # Simulate processing
            
            # Update status to ready using async ORM
            await KnowledgeBase.objects.filter(id=knowledge_base.id).aupdate(status='ready')  # type: ignore[attr-defined]
            knowledge_base.status = 'ready'  # type: ignore[attr-defined]
            
            logger.info(f"Knowledge base build completed: {name} (ID: {knowledge_base.id})")
            
        except ValidationError as e:
            logger.warning(f"Validation error in async build: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Async build failed: {str(e)}")
            raise


class ListKnowledgeBasesView(APIView):
    """
    List knowledge bases
    GET /api/v1/knowledge/bases
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """List knowledge bases"""
        try:
            project_id = request.query_params.get('project_id')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Query knowledge bases
            knowledge_bases = self._get_knowledge_bases(int(project_id) if project_id else None)
            
            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_bases = knowledge_bases[start_idx:end_idx]
            
            return Response({
                'success': True,
                'knowledge_bases': paginated_bases,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': len(knowledge_bases),
                    'total_pages': (len(knowledge_bases) + page_size - 1) // page_size
                }
            })
            
        except Exception as e:
            logger.error(f"Error listing knowledge bases: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_knowledge_bases(self, project_id: Optional[int] = None) -> list[dict[str, Any]]:
        """Get knowledge bases from database"""
        try:
            queryset = KnowledgeBase.objects.all().order_by('-updated_at')
            
            if project_id:
                queryset = queryset.filter(project_id=project_id)
            
            bases = []
            for kb in queryset:
                bases.append({
                    'id': kb.id,
                    'name': kb.name,
                    'description': kb.description,
                    'project_id': kb.project_id,
                    'project_name': kb.project.name if kb.project else '',
                    'status': kb.status,
                    'document_count': kb.document_count,
                    'embedding_model': kb.embedding_model,
                    'chunk_size': kb.chunk_size,
                    'chunk_overlap': kb.chunk_overlap,
                    'created_at': kb.created_at.isoformat() if kb.created_at else None,
                    'updated_at': kb.updated_at.isoformat() if kb.updated_at else None,
                })
            
            return bases
            
        except Exception as e:
            logger.error(f"Error querying knowledge bases: {str(e)}")
            return []


class GetBestPracticesView(APIView):
    """
    Get testing best practices
    GET /api/v1/knowledge/best-practices
    """
    permission_classes = [IsAuthenticated]
    
    async def get(self, request: Request) -> Response:
        """Get testing best practices"""
        try:
            topic = request.query_params.get('topic', 'general')
            top_k = int(request.query_params.get('top_k', 5))
            include_examples = request.query_params.get('include_examples', 'true').lower() == 'true'
            
            if not topic.strip():
                return Response(
                    {'error': 'Topic cannot be empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Direct async execution
            result = await self._async_get_best_practices(
                topic=topic,
                top_k=top_k,
                include_examples=include_examples
            )
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error getting best practices: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def _async_get_best_practices(
        self,
        topic: str,
        top_k: int,
        include_examples: bool
    ) -> dict:
        """Async get best practices"""
        try:
            # Initialize knowledge agent
            agent = KnowledgeRAGAgent(
                llm_service=None,  # Would be injected in production
                rag_retriever=None,  # Would be injected in production
                config={'timeout': 30}
            )
            
            # Get best practices
            result = await agent.get_best_practices(
                topic=topic,
                top_k=top_k,
                include_examples=include_examples
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Async best practices query failed: {str(e)}")
            return {
                'success': False,
                'topic': topic,
                'error': str(e)
            }


class UploadDocumentView(APIView):
    """
    Upload document to knowledge base
    POST /api/v1/knowledge/upload
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def post(self, request: Request) -> Response:
        """Upload document to knowledge base"""
        try:
            if request.content_type and 'multipart' in request.content_type:
                return self._handle_file_upload(request)
            else:
                return self._handle_json_upload(request)
                
        except ValidationError as e:
            logger.warning(f"Validation error in document upload: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_json_upload(self, request: Request) -> Response:
        """Handle JSON body upload"""
        data = request.data  # type: Dict[str, Any]
        doc_type = data.get('doc_type')  # type: ignore[attr-defined]  # type: ignore[attr-defined]
        title = data.get('title')  # type: ignore[attr-defined]  # type: ignore[attr-defined]
        content = data.get('content')  # type: ignore[attr-defined]  # type: ignore[attr-defined]
        project_id = data.get('project_id')  # type: ignore[attr-defined]  # type: ignore[attr-defined]
        metadata = data.get('metadata', {})  # type: ignore[attr-defined]  # type: ignore[attr-defined]
        
        validate_required_fields(data, ['doc_type', 'title', 'content', 'project_id'])
        
        return self._process_upload(
            doc_type=doc_type,
            title=title,
            content=content,
            project_id=project_id,
            metadata=metadata
        )
    
    def _handle_file_upload(self, request: Request) -> Response:
        """Handle file upload"""
        uploaded_file = request.FILES.get('file')
        doc_type = request.data.get('doc_type')
        title = request.data.get('title')
        project_id = request.data.get('project_id')
        metadata = {}
        
        if 'metadata' in request.data:
            try:
                metadata = json.loads(request.data['metadata'])
            except json.JSONDecodeError:
                metadata = {}
        
        if not uploaded_file:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validate_required_fields(
            {'doc_type': doc_type, 'title': title, 'project_id': project_id},
            ['doc_type', 'title', 'project_id']
        )
        
        try:
            content = uploaded_file.read().decode('utf-8')
        except UnicodeDecodeError:
            return Response(
                {'error': 'File encoding must be UTF-8'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return self._process_upload(
            doc_type=doc_type,
            title=title,
            content=content,
            project_id=int(project_id),
            metadata=metadata
        )
    
    def _process_upload(
        self,
        doc_type: str,
        title: str,
        content: str,
        project_id: int,
        metadata: dict
    ) -> Response:
        """Process document upload"""
        if doc_type not in DocType.ALL:
            return Response(
                {'error': f'Invalid doc_type: {doc_type}. Must be one of: {DocType.DOC_TYPES}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {'error': f'Project {project_id} does not exist'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        knowledge_base, _ = KnowledgeBase.objects.get_or_create(
            project=project,
            defaults={
                'name': f'{project.name} Knowledge Base',  # type: ignore[attr-defined]
                'description': f'Knowledge base for {project.name}',  # type: ignore[attr-defined]
            }
        )
        
        converted = DocumentConverter.convert_uploaded_document(
            doc_type=doc_type,
            title=title,
            content=content,
            project_id=project_id,
            metadata=metadata
        )
        
        document = KnowledgeDocument.objects.create(
            knowledge_base=knowledge_base,
            document_type=doc_type,
            content=converted['content'],
            metadata=converted['metadata'],
            sync_status='pending'
        )
        
        sync_document_to_chroma(document.id)
        
        document.refresh_from_db()
        
        return Response({
            'success': True,
            'message': 'Document uploaded and synced successfully',
            'document': {
                'id': document.id,  # type: ignore[attr-defined]
                'doc_type': doc_type,
                'title': title,
                'project_id': project_id,
                'sync_status': document.sync_status
            }
        }, status=status.HTTP_201_CREATED)


class ListKnowledgeDocumentsView(APIView):
    """
    List knowledge documents
    GET /api/v1/knowledge/documents
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """List knowledge documents"""
        try:
            project_id = request.query_params.get('project_id')
            knowledge_base_id = request.query_params.get('knowledge_base_id')
            
            queryset = KnowledgeDocument.objects.all().select_related(
                'knowledge_base', 'knowledge_base__project'
            ).order_by('-created_at')
            
            if project_id:
                queryset = queryset.filter(knowledge_base__project_id=project_id)
            if knowledge_base_id:
                queryset = queryset.filter(knowledge_base_id=knowledge_base_id)
            
            documents = []
            for doc in queryset:
                documents.append({
                    'id': doc.id,
                    'title': doc.metadata.get('title', doc.document_type),
                    'doc_type': doc.document_type,
                    'knowledge_base_id': doc.knowledge_base_id,
                    'knowledge_base_name': doc.knowledge_base.name if doc.knowledge_base else '',
                    'project_id': doc.knowledge_base.project_id if doc.knowledge_base else None,
                    'sync_status': doc.sync_status,
                    'created_at': doc.created_at.isoformat() if doc.created_at else None,
                    'file_path': doc.file_path,
                })
            
            return Response({
                'success': True,
                'documents': documents,
                'total': len(documents)
            })
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteKnowledgeDocumentView(APIView):
    """
    Delete knowledge document
    DELETE /api/v1/knowledge/documents/{id}
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request: Request, pk: int) -> Response:
        """Delete knowledge document"""
        try:
            doc = KnowledgeDocument.objects.select_related('knowledge_base').get(id=pk)
            
            # Delete from ChromaDB
            try:
                from core.agents.rag.knowledge_retriever import KnowledgeRetriever
                retriever = KnowledgeRetriever()
                if doc.chroma_id_prefix:
                    retriever.delete_document_chunks(doc.chroma_id_prefix)
            except Exception as e:
                logger.warning(f"Failed to delete from ChromaDB: {e}")
            
            # Delete from MySQL
            doc.delete()
            
            return Response({
                'success': True,
                'message': 'Document deleted successfully'
            })
            
        except KnowledgeDocument.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SyncDocumentView(APIView):
    """
    Manual sync document to vector store
    POST /api/v1/knowledge/documents/{id}/sync/
    
    Synchronous execution (no Celery).
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request: Request, pk: int) -> Response:
        try:
            doc = KnowledgeDocument.objects.select_related(
                'knowledge_base__project'
            ).get(id=pk)
            
            from core.tasks import sync_document_to_chroma
            
            # Set to syncing status first
            doc.sync_status = 'syncing'
            doc.save(update_fields=['sync_status'])
            
            # Direct synchronous execution
            try:
                sync_document_to_chroma(pk)
                doc.refresh_from_db()
                logger.info(f"Document {pk} synced successfully")
                
                return Response({
                    'success': True,
                    'sync_status': doc.sync_status,
                    'message': 'Document synced successfully'
                })
            except Exception as sync_error:
                error_msg = str(sync_error)
                logger.error(f"Failed to sync document {pk}: {sync_error}")
                doc.sync_status = 'failed'
                doc.sync_error = error_msg
                doc.save(update_fields=['sync_status', 'sync_error'])
                return Response({
                    'success': False,
                    'error': error_msg,
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except KnowledgeDocument.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error syncing document: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )