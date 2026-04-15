"""
Execution API Views

This module contains views for page structure management.
"""
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List, Dict, cast

from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async

from shared.exceptions import ValidationError
from shared.utils.validation import validate_page_structure
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class PageStructureView(APIView):
    """
    Page structure management API
    
    Used for storing and managing page HTML structures, supporting AI to generate more accurate selectors
    
    POST /api/v1/execution/page-structure/  - Save page structure
    GET  /api/v1/execution/page-structure/?url=xxx&project_id=1  - Query page structure
    """
    permission_classes = [IsAuthenticated]
    
    async def post(self, request: Request) -> Response:
        """
        Save page structure to knowledge base
        ...
        """
        try:
            data = request.data
            project_id = data.get('project_id')
            url = data.get('url')
            title = data.get('title', '')
            elements = data.get('elements', [])
            
            if not project_id:
                raise ValidationError("Missing required parameter: project_id")
            
            if not url:
                raise ValidationError("Missing required parameter: url")
            
            if not elements:
                raise ValidationError("Page elements cannot be empty")
            
            validate_page_structure(elements)
            
            result = await self._async_save_page_structure(
                int(project_id),
                str(url),
                str(title),
                cast(List[Any], elements),
                request.user
            )
            
            return Response(result)
            
        except ValidationError as e:
            logger.warning(f"Validation error in PageStructureView: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error saving page structure: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def _async_save_page_structure(
        self,
        project_id: int,
        url: str,
        title: str,
        elements: List[Any],
        user: Any
    ) -> Dict[str, Any]:
        """Async save page structure"""
        from core.models.project import Project
        from core.models.knowledge import KnowledgeBase, KnowledgeDocument
        
        def get_project() -> Project:
            return Project.objects.get(id=project_id)
        
        try:
            project = await sync_to_async(get_project)()
        except Project.DoesNotExist:
            return {
                'success': False,
                'error': f'Project {project_id} does not exist'
            }
        
        def get_or_create_kb() -> KnowledgeBase:
            kb, created = KnowledgeBase.objects.get_or_create(
                project=project,
                defaults={
                    'name': f'{project.name} Knowledge Base',
                    'description': f'Auto-created knowledge base - Project: {project.name}',
                    'status': 'ready'
                }
            )
            return kb
        
        knowledge_base = await sync_to_async(get_or_create_kb)()
        
        url_normalized = url.rstrip('/').lower()
        
        content_lines = [
            f"Page: {url}",
            f"Title: {title}",
            "Interactive elements:",
        ]
        
        for i, elem in enumerate(elements, 1):
            elem_type = elem.get('type', 'unknown')
            elem_text = elem.get('text', '')
            elem_tag = elem.get('tag', '')
            attrs = elem.get('attributes', {})
            
            desc = f"  {i}. [{elem_type}] {elem_tag}"
            if elem_text:
                desc += f" text='{elem_text}'"
            if attrs.get('placeholder'):
                desc += f" placeholder='{attrs['placeholder']}'"
            if attrs.get('id'):
                desc += f" id='{attrs['id']}'"
            if attrs.get('name'):
                desc += f" name='{attrs['name']}'"
            
            content_lines.append(desc)
        
        content = "\n".join(content_lines)
        
        def create_or_update_doc() -> KnowledgeDocument:
            existing_doc = KnowledgeDocument.objects.filter(
                knowledge_base=knowledge_base,
                document_type='page_structure',
                metadata__url=url_normalized
            ).first()
            
            metadata = {
                'url': url_normalized,
                'title': title,
                'elements': elements,
                'element_count': len(elements),
                'saved_by': getattr(user, 'username', 'unknown'),
                'saved_at': str(datetime.now())
            }
            
            if existing_doc:
                existing_doc.content = content
                existing_doc.metadata = metadata
                existing_doc.save()
                return existing_doc
            else:
                return KnowledgeDocument.objects.create(
                    knowledge_base=knowledge_base,
                    document_type='page_structure',
                    content=content,
                    metadata=metadata,
                    sync_status='pending'
                )
        
        doc = await sync_to_async(create_or_update_doc)()
        
        logger.info(f"Page structure saved: {url_normalized}")
        
        return {
            'success': True,
            'message': 'Page structure saved successfully',
            'data': {
                'document_id': doc.pk,
                'url': url_normalized,
                'element_count': len(elements)
            }
        }
    
    async def get(self, request: Request) -> Response:
        """
        Get page structure by URL
        
        Query params:
            url: Page URL (required)
            project_id: Project ID (required)
        
        Response:
        {
            "success": true,
            "data": {
                "url": "https://www.baidu.com",
                "title": "百度一下，你就知道",
                "elements": [...],
                "element_count": 2,
                "document_id": 123
            }
        }
        """
        try:
            url = request.GET.get('url')
            project_id = request.GET.get('project_id')
            
            if not url or not project_id:
                raise ValidationError("Missing required parameters: url, project_id")
            
            from core.models.project import Project
            from core.models.knowledge import KnowledgeBase, KnowledgeDocument
            
            try:
                project = await Project.objects.aget(id=int(project_id))
            except Project.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'Project not found: {project_id}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            knowledge_base = await KnowledgeBase.objects.filter(
                project=project,
                status='ready'
            ).afirst()
            
            if not knowledge_base:
                return Response({
                    'success': False,
                    'error': f'Knowledge base not found for project: {project_id}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            doc = await KnowledgeDocument.objects.filter(
                knowledge_base=knowledge_base,
                document_type='page_structure',
                metadata__url=url.rstrip('/').lower()
            ).afirst()
            
            if not doc:
                return Response({
                    'success': False,
                    'error': f'Page structure not found: {url}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            metadata: Dict[str, Any] = cast(Dict[str, Any], doc.metadata) if doc.metadata else {}
            
            return Response({
                'success': True,
                'data': {
                    'document_id': doc.pk,
                    'url': metadata.get('url'),
                    'title': metadata.get('title', ''),
                    'elements': metadata.get('elements', []),
                    'element_count': metadata.get('element_count', 0)
                }
            })
            
        except ValidationError as e:
            logger.warning(f"Validation error in PageStructureView GET: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error getting page structure: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )