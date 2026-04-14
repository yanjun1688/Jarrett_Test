"""
Execution API Views

This module contains views for test execution and page structure management.
"""
from __future__ import annotations
from typing import Any
from rest_framework.request import Request

import json
import logging
from datetime import datetime
from typing import Optional

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async

from core.flow.flow_ir import FlowIR
from core.flow.execution_engine import ExecutionEngine
from core.flow.test_node_registry import global_node_registry
from shared.exceptions import ValidationError, ExecutionError
from shared.utils.validation import validate_flow_ir, validate_page_structure
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ExecuteFlowIRView(APIView):
    """
    Unified test execution API - using ExecutionEngine
    
    POST /api/v1/execution/execute
    Receive FlowIR, execute test and return result
    
    This is the new recommended API, using FlowIR for direct execution
    """
    permission_classes = [IsAuthenticated]

    async def post(self, request: Request) -> Response:
        """
        Execute FlowIR
        
        Request body:
        {
            "flow_ir": {...},  # Required, FlowIR object
            "context": {},     # Optional, execution context
            "timeout": 600,    # Optional, timeout in seconds
            "project_id": 123, # Optional, project ID for saving results
            "save_result": true # Optional, whether to save execution record
        }
        
        Response:
        {
            "success": true,
            "execution_id": 123,
            "node_results": {...},
            "errors": [],
            "metrics": {
                "nodes_executed": 5,
                "successful_nodes": 5,
                "failed_nodes": 0,
                "total_duration": 15.5
            },
            "context": {...}
        }
        """
        try:
            data = request.data  # type: ignore[var-assign]
            flow_ir_data = data.get('flow_ir')  # type: ignore[attr-defined]
            context = data.get('context', {})  # type: ignore[attr-defined]
            timeout = data.get('timeout', 600)  # type: ignore[attr-defined]
            project_id = data.get('project_id')  # type: ignore[attr-defined]
            save_result = data.get('save_result', True)  # type: ignore[attr-defined]

            if not flow_ir_data:
                raise ValidationError("Missing required parameter: flow_ir")

            # Validate FlowIR structure
            validate_flow_ir(flow_ir_data)  # type: ignore[arg-type]

            # Direct async execution (no async_to_sync wrapper needed)
            result = await self._async_execute(
                dict(flow_ir_data) if isinstance(flow_ir_data, dict) else {},  # type: ignore[arg-type]
                dict(context) if isinstance(context, dict) else {},  # type: ignore[arg-type]
                int(timeout) if isinstance(timeout, (int, float)) else 600,  # type: ignore[arg-type]
                int(project_id) if project_id else None,  # type: ignore[arg-type]
                bool(save_result),  # type: ignore[arg-type]
                request.user
            )

            return Response(result)

        except ValidationError as e:
            logger.warning(f"Validation error in ExecuteFlowIRView: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error executing flow: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def _async_execute(
        self,
        flow_ir_data: dict,
        context: dict,
        timeout: int,
        project_id: int,
        save_result: bool,
        user: Any
    ) -> dict:
        """Async execution of FlowIR"""
        # Load FlowIR
        flow_ir = FlowIR.from_dict(flow_ir_data)

        # Create execution engine
        executor = ExecutionEngine(
            registry=global_node_registry,
            default_timeout=timeout
        )

        # Execute flow
        result = await executor.run(flow_ir, context)

        # Save execution record (if needed)
        execution_id = None
        if save_result and project_id:
            execution_id = await self._save_execution(
                flow_ir,
                result,
                project_id,
                user
            )

        return {
            'success': result.get('success', False),
            'execution_id': execution_id,
            'node_results': result.get('node_results'),
            'errors': result.get('errors', []),
            'metrics': result.get('metrics', {}),
            'context': result.get('context', {})
        }

    async def _save_execution(
        self,
        flow_ir: FlowIR,
        result: dict,
        project_id: int,
        user: Any
    ) -> Optional[int]:
        """Save execution record to database using async ORM"""
        try:
            from core.models.project import Project
            from core.models.test_management import TestFlow, TestFlowExecution

            # Get project using async ORM (Django 5.2+)
            try:
                project = await Project.objects.aget(id=project_id)
            except Project.DoesNotExist:
                logger.warning(f"Project {project_id} not found, skipping save")
                return None

            # Create TestFlow using async ORM
            flow_name = flow_ir.metadata.get('name', 'Unnamed Flow')
            test_flow = await TestFlow.objects.acreate(
                project=project,
                user=user,
                name=flow_name,
                scenario_description=flow_ir.metadata.get('description', ''),
                flow_data=flow_ir.to_dict(),
                metadata={'flow_ir': True, 'auto_generated': True}
            )

            # Create execution record using async ORM
            execution = await TestFlowExecution.objects.acreate(
                test_flow=test_flow,
                user=user,
                status='completed' if result.get('success') else 'failed',
                execution_data=flow_ir.to_dict(),
                result=result,
                metrics=result.get('metrics', {}),
            )

            return execution.id  # type: ignore[attr-defined]

        except Exception as e:
            logger.error(f"Failed to save execution: {e}")
            return None


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
        
        Request:
        {
            "project_id": 1,
            "url": "https://www.baidu.com",
            "title": "百度一下，你就知道",
            "elements": [
                {
                    "type": "input",
                    "tag": "input",
                    "attributes": {"placeholder": "请输入搜索内容", "id": "kw"},
                    "text": null,
                    "selector_hints": ["placeholder=请输入搜索内容"]
                },
                {
                    "type": "button",
                    "tag": "button", 
                    "attributes": {},
                    "text": "百度一下",
                    "selector_hints": ["text=百度一下"]
                }
            ]
        }
        
        Response:
        {
            "success": true,
            "message": "页面结构已保存",
            "data": {
                "document_id": 123,
                "url": "https://www.baidu.com",
                "element_count": 2
            }
        }
        """
        try:
            data = request.data  # type: ignore[var-assign]
            project_id = data.get('project_id')  # type: ignore[attr-defined]
            url = data.get('url')  # type: ignore[attr-defined]
            title = data.get('title', '')  # type: ignore[attr-defined]
            elements = data.get('elements', [])  # type: ignore[attr-defined]
            
            if not project_id:
                raise ValidationError("Missing required parameter: project_id")
            
            if not url:
                raise ValidationError("Missing required parameter: url")
            
            if not elements:
                raise ValidationError("Page elements cannot be empty")
            
            # Validate page structure
            validate_page_structure(elements)  # type: ignore[arg-type]
            
            # Direct async execution
            result = await self._async_save_page_structure(
                int(project_id) if project_id else 0,  # type: ignore[arg-type]
                str(url) if url else "",
                str(title),
                list(elements) if isinstance(elements, list) else [],  # type: ignore[arg-type]
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
        elements: list,
        user: Any
    ) -> dict:
        """Async save page structure"""
        from core.models.project import Project
        from core.models.knowledge import KnowledgeBase, KnowledgeDocument
        from core.agents.rag.knowledge_rag_agent import KnowledgeRAGAgent
        
        # Get project
        def get_project():
            return Project.objects.get(id=project_id)
        
        try:
            project = await sync_to_async(get_project)()
        except Project.DoesNotExist:
            return {
                'success': False,
                'error': f'Project {project_id} does not exist'
            }
        
        # Find or create knowledge base
        def get_or_create_kb():
            kb, created = KnowledgeBase.objects.get_or_create(
                project=project,
                defaults={
                    'name': f'{project.name} Knowledge Base',
                    'description': f'Auto-created knowledge base - Project: {project.name}',
                    'status': 'ready'
                }
            )
            return kb, created
        
        knowledge_base, _ = await sync_to_async(get_or_create_kb)()
        
        # Normalize URL: remove trailing slash, convert to lowercase
        url_normalized = url.rstrip('/').lower()
        
        # Build page structure content (for vector retrieval) - keep old format for compatibility
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
        
        # Create or update knowledge document
        def create_or_update_doc():
            # Check if document already exists
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
                'saved_by': user.username,
                'saved_at': str(datetime.now())
            }
            
            if existing_doc:
                # Update existing document
                existing_doc.content = content
                existing_doc.metadata = metadata
                existing_doc.save()
                return existing_doc
            else:
                # Create new document
                return KnowledgeDocument.objects.create(
                    knowledge_base=knowledge_base,
                    document_type='page_structure',
                    content=content,
                    metadata=metadata,
                    status='ready',
                    user=user
                )
        
        doc = await sync_to_async(create_or_update_doc)()
        
        # Store elements as separate vector documents for better retrieval
        try:
            # Initialize RAG agent
            rag_agent = KnowledgeRAGAgent()
            
            # Store elements as separate vector documents
            # Note: store_page_elements method may need to be implemented
            # await rag_agent.store_page_elements(
            #     url=url_normalized,
            #     title=title,
            #     elements=elements,
            #     knowledge_base_id=knowledge_base.id
            # )
            
            logger.info(f"Page structure saved, vector storage not implemented yet")
        except Exception as e:
            logger.warning(f"Failed to store page elements as vectors: {e}")
            # Continue even if vector storage fails
        
        return {
            'success': True,
            'message': 'Page structure saved successfully',
            'data': {
                'document_id': doc.id,  # type: ignore[attr-defined]
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
            
            # Query page structure using async ORM
            from core.models.project import Project
            from core.models.knowledge import KnowledgeBase, KnowledgeDocument
            
            try:
                project = await Project.objects.aget(id=project_id)
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
            
            # Exact URL match
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
            
            metadata = doc.metadata or {}
            
            return Response({
                'success': True,
                'data': {
                    'document_id': doc.id,
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