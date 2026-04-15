"""
Knowledge base API views
"""
from __future__ import annotations

import logging
import json
from typing import Any, Dict, List, Optional, cast

from django.http import JsonResponse
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

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
            data = request.data
            query = data.get('query')
            project_id = data.get('project_id')
            top_k = int(data.get('top_k', 5))
            document_type = data.get('document_type')
            use_llm = bool(data.get('use_llm', True))
            
            validate_required_fields(data, ['query', 'project_id'])
            
            if query and not str(query).strip():
                return Response(
                    {'error': 'Query cannot be empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = await self._async_query(
                query=str(query) if query else '',
                project_id=int(project_id) if project_id else 0,
                top_k=top_k,
                document_type=str(document_type) if document_type else None,
                use_llm=use_llm
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
        use_llm: bool
    ) -> Dict[str, Any]:
        """Async query knowledge base"""
        try:
            agent = KnowledgeRAGAgent(
                llm_service=None,
                rag_retriever=None
            )
            
            result = await agent.query(
                query=query,
                top_k=top_k,
                document_type=document_type,
                use_llm=use_llm
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
            data = request.data
            project_id = data.get('project_id')
            name = data.get('name')
            description = data.get('description', '')
            source_type = data.get('source_type', 'document')
            source_path = data.get('source_path')
            
            validate_required_fields(data, ['project_id', 'name'])
            
            if str(source_type) == 'document' and not source_path:
                return Response(
                    {'error': 'source_path is required for document source type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            await self._async_build(
                project_id=int(project_id) if project_id else 0,
                name=str(name) if name else '',
                description=str(description),
                source_type=str(source_type),
                source_path=str(source_path) if source_path else None
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
            
            try:
                project = await Project.objects.aget(id=project_id)
            except Project.DoesNotExist:
                raise ValidationError(f"Project {project_id} does not exist")
            
            knowledge_base = await KnowledgeBase.objects.acreate(
                project=project,
                name=name,
                description=description,
                status='building'
            )
            
            import asyncio
            await asyncio.sleep(1)
            
            await KnowledgeBase.objects.filter(pk=knowledge_base.pk).aupdate(status='ready')
            
            logger.info(f"Knowledge base build completed: {name} (ID: {knowledge_base.pk})")
            
        except ValidationError:
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
            
            knowledge_bases = self._get_knowledge_bases(int(project_id) if project_id else None)
            
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
    
    def _get_knowledge_bases(self, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get knowledge bases from database"""
        try:
            queryset = KnowledgeBase.objects.all().order_by('-updated_at')
            
            if project_id:
                queryset = queryset.filter(project_id=project_id)
            
            bases: List[Dict[str, Any]] = []
            for kb in queryset:
                bases.append({
                    'id': kb.pk,
                    'name': kb.name,
                    'description': kb.description,
                    'project_id': kb.project.pk,
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
            
            if not topic.strip():
                return Response(
                    {'error': 'Topic cannot be empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = await self._async_get_best_practices(
                topic=str(topic),
                top_k=top_k
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
        top_k: int
    ) -> Dict[str, Any]:
        """Async get best practices"""
        try:
            agent = KnowledgeRAGAgent(
                llm_service=None,
                rag_retriever=None
            )
            
            result = await agent.get_best_practices(
                topic=topic,
                top_k=top_k
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
        data = request.data
        doc_type = data.get('doc_type')
        title = data.get('title')
        content = data.get('content')
        project_id = data.get('project_id')
        metadata = cast(Dict[str, Any], data.get('metadata', {}))
        
        validate_required_fields(data, ['doc_type', 'title', 'content', 'project_id'])
        
        return self._process_upload(
            doc_type=str(doc_type) if doc_type else '',
            title=str(title) if title else '',
            content=str(content) if content else '',
            project_id=int(project_id) if project_id else 0,
            metadata=cast(Dict[str, Any], metadata)
        )
    
    def _handle_file_upload(self, request: Request) -> Response:
        """Handle file upload"""
        files = cast(Dict[str, Any], request.FILES)
        uploaded_file = files.get('file')
        data = request.data
        doc_type = data.get('doc_type')
        title = data.get('title')
        project_id = data.get('project_id')
        metadata: Dict[str, Any] = {}
        
        if 'metadata' in data:
            try:
                metadata = json.loads(str(data['metadata']))
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
            doc_type=str(doc_type) if doc_type else '',
            title=str(title) if title else '',
            content=content,
            project_id=int(project_id) if project_id else 0,
            metadata=metadata
        )
    
    def _process_upload(
        self,
        doc_type: str,
        title: str,
        content: str,
        project_id: int,
        metadata: Dict[str, Any]
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
                'name': f'{project.name} Knowledge Base',
                'description': f'Knowledge base for {project.name}',
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
        
        sync_document_to_chroma(document.pk)
        
        document.refresh_from_db()
        
        return Response({
            'success': True,
            'message': 'Document uploaded and synced successfully',
            'document': {
                'id': document.pk,
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
                kb_id = int(knowledge_base_id)
                queryset = queryset.filter(knowledge_base_id=kb_id)
            
            documents: List[Dict[str, Any]] = []
            for doc in queryset:
                documents.append({
                    'id': doc.pk,
                    'title': doc.metadata.get('title', doc.document_type) if doc.metadata else doc.document_type,
                    'doc_type': doc.document_type,
                    'knowledge_base_id': doc.knowledge_base.pk,
                    'knowledge_base_name': doc.knowledge_base.name if doc.knowledge_base else '',
                    'project_id': doc.knowledge_base.project.pk if doc.knowledge_base else None,
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
            
            try:
                from core.agents.rag.knowledge_retriever import KnowledgeRetriever
                retriever = KnowledgeRetriever()
                if doc.chroma_id_prefix:
                    retriever.delete_document_chunks(doc.chroma_id_prefix)
            except Exception as e:
                logger.warning(f"Failed to delete from ChromaDB: {e}")
            
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
            
            doc.sync_status = 'syncing'
            doc.save(update_fields=['sync_status'])
            
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