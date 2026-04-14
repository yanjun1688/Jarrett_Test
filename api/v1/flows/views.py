"""
Test flows API views
"""
from __future__ import annotations
from typing import Any
from rest_framework.request import Request
from django.db.models import QuerySet

from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import logging
import json
from typing import Optional, Dict, Any

from core.flow.flow_ir import FlowIR
from core.flow.execution_engine import ExecutionEngine
from core.flow.test_node_registry import global_node_registry
from core.models import TestFlow, TestFlowExecution, Project
from shared.exceptions import ValidationError, ExecutionError
from shared.utils.validation import validate_required_fields

logger = logging.getLogger(__name__)


class ExecuteTestFlowView(APIView):
    """
    Execute test flow
    POST /api/v1/flows/execute
    """
    permission_classes = [IsAuthenticated]
    
    async def post(self, request: Request) -> Response:
        """Execute test flow"""
        logger.info(f"[FLOW] Execute test flow request from user: {request.user}")
        
        try:
            data = request.data  # type: ignore[var-assign]
            flow_id = data.get('flow_id')  # type: ignore[attr-defined]
            context = data.get('context', {})  # type: ignore[attr-defined]
            timeout = data.get('timeout', 600)  # type: ignore[attr-defined]
            
            # Validate required fields
            validate_required_fields(data, ['flow_id'])  # type: ignore[arg-type]
            
            logger.info(f"[FLOW] Flow ID: {flow_id}, Context keys: {list(context.keys())}")  # type: ignore[attr-defined]
            
            # Direct async execution
            result = await self._async_execute_flow(
                flow_id=int(flow_id) if flow_id else 0,  # type: ignore[arg-type]
                context=dict(context) if isinstance(context, dict) else {},  # type: ignore[arg-type]
                timeout=int(timeout) if isinstance(timeout, (int, float)) else 600,  # type: ignore[arg-type]
                user=request.user
            )
            
            logger.info(f"[FLOW] Execution completed: {result.get('success', False)}")
            return Response(result)
            
        except ValidationError as e:
            logger.warning(f"[FLOW] Validation error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"[FLOW] Failed to execute test flow: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def _async_execute_flow(
        self,
        flow_id: int,
        context: Dict[str, Any],
        timeout: int,
        user: Any
    ) -> Dict[str, Any]:
        """Async execute test flow"""
        try:
            logger.info(f"[FLOW] Starting async execution for flow: {flow_id}")
            
            # Get flow from database using async ORM (Django 5.2+)
            try:
                test_flow = await TestFlow.objects.aget(id=flow_id)
            except TestFlow.DoesNotExist:
                raise ValidationError(f"Test flow {flow_id} does not exist")
            
            # Create FlowIR object from flow data
            flow_ir = FlowIR.from_dict(test_flow.flow_data)
            
            # Initialize execution engine
            executor = ExecutionEngine(
                registry=global_node_registry,
                default_timeout=timeout
            )
            
            # Execute flow
            result = await executor.run(flow_ir, context)
            
            # Save execution record
            execution_id = await self._save_execution_record(test_flow, result, user)
            
            # Add execution metadata
            result['execution_metadata'] = {
                'flow_id': flow_id,
                'execution_id': execution_id,
                'user_id': user.id if user.is_authenticated else None,
                'execution_time': result.get('metrics', {}).get('total_time', 0)
            }
            
            return result
            
        except ExecutionError as e:
            logger.error(f"[FLOW] Execution error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'flow_id': flow_id,
                'status': 'failed'
            }
        except Exception as e:
            logger.error(f"[FLOW] Async execution failed: {str(e)}")
            return {
                'success': False,
                'error': 'Execution failed',
                'flow_id': flow_id,
                'status': 'failed'
            }
    
    async def _save_execution_record(
        self,
        test_flow: TestFlow,
        result: Dict[str, Any],
        user: Any
    ) -> int:
        """Save execution record to database using async ORM"""
        try:
            execution = await TestFlowExecution.objects.acreate(
                test_flow=test_flow,
                user=user,
                execution_data=test_flow.flow_data,
                result=result,
                metrics=result.get('metrics', {}),
                status='completed' if result.get('success') else 'failed',
                error_message=result.get('error', ''),
                started_at=result.get('metadata', {}).get('start_time'),
                completed_at=result.get('metadata', {}).get('end_time')
            )
            
            logger.info(f"[FLOW] Execution record saved: {execution.id}")  # type: ignore[attr-defined]
            return execution.id  # type: ignore[attr-defined]
            
        except Exception as e:
            logger.error(f"[FLOW] Failed to save execution record: {str(e)}")
            return 0
    
    def _get_mock_flow_data(self, flow_id: int) -> Dict[str, Any]:
        """Get mock flow data (for demonstration)"""
        return {
            'id': f'flow_{flow_id}',
            'name': f'Test Flow {flow_id}',
            'description': 'Sample test flow for demonstration',
            'version': '1.0.0',
            'nodes': [
                {
                    'id': 'node_1',
                    'type': 'test_planning',
                    'name': 'Plan Tests',
                    'config': {
                        'test_type': 'api',
                        'coverage': 'high'
                    }
                },
                {
                    'id': 'node_2',
                    'type': 'test_execution',
                    'name': 'Execute API Tests',
                    'config': {
                        'endpoints': ['/api/users', '/api/products'],
                        'timeout': 30
                    },
                    'dependencies': ['node_1']
                },
                {
                    'id': 'node_3',
                    'type': 'result_validation',
                    'name': 'Validate Results',
                    'config': {
                        'validation_rules': [
                            {'type': 'status_code', 'expected': 200},
                            {'type': 'response_time', 'value': 5.0}
                        ]
                    },
                    'dependencies': ['node_2']
                }
            ],
            'metadata': {
                'created_by': 'system',
                'created_at': '2024-01-01T00:00:00Z',
                'tags': ['api', 'test', 'automation']
            }
        }


class GetTestFlowView(APIView):
    """
    Get test flow details
    GET /api/v1/flows/{flow_id}
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request, flow_id: int) -> Response:
        """Get test flow details"""
        try:
            # Get flow from database
            try:
                test_flow = TestFlow.objects.get(id=flow_id)
            except TestFlow.DoesNotExist:
                return Response(
                    {'error': f'Test flow {flow_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get execution statistics
            executions = TestFlowExecution.objects.filter(test_flow=test_flow)
            total_executions = executions.count()
            successful_executions = executions.filter(status='completed').count()
            success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
            
            # Get latest execution
            latest_execution = executions.order_by('-created_at').first()
            
            flow_data = {
                'id': test_flow.id,
                'name': test_flow.name,
                'description': test_flow.description,
                'scenario_description': test_flow.scenario_description,
                'type': test_flow.metadata.get('type', 'general'),
                'status': 'active' if test_flow.is_active else 'inactive',
                'version': test_flow.version,
                'created_at': test_flow.created_at.isoformat() if test_flow.created_at else None,
                'updated_at': test_flow.updated_at.isoformat() if test_flow.updated_at else None,
                'created_by': test_flow.user.username if test_flow.user else 'system',
                'project_id': test_flow.project_id,
                'project_name': test_flow.project.name if test_flow.project else '',
                'tags': test_flow.metadata.get('tags', []),
                'statistics': {
                    'total_executions': total_executions,
                    'success_rate': round(success_rate, 2),
                    'successful_executions': successful_executions,
                    'failed_executions': total_executions - successful_executions,
                    'last_execution': latest_execution.created_at.isoformat() if latest_execution else None
                },
                'flow_data': test_flow.flow_data,
                'metadata': test_flow.metadata
            }
            
            return Response({
                'success': True,
                'flow': flow_data
            })
            
        except TestFlow.DoesNotExist:
            return Response(
                {'error': f'Test flow {flow_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting test flow: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetFlowExecutionView(APIView):
    """
    Get flow execution details
    GET /api/v1/flows/executions/{execution_id}
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request, execution_id: int) -> Response:
        """Get flow execution details"""
        try:
            # Get execution from database
            try:
                execution = TestFlowExecution.objects.get(id=execution_id)
            except TestFlowExecution.DoesNotExist:
                return Response(
                    {'error': f'Flow execution {execution_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            execution_data = {
                'id': execution.id,
                'flow_id': execution.test_flow_id,
                'flow_name': execution.test_flow.name,
                'status': execution.status,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'duration_seconds': execution.duration,
                'initiated_by': execution.user.username if execution.user else 'system',
                'result': execution.result,
                'metrics': execution.metrics,
                'error_message': execution.error_message,
                'execution_data': execution.execution_data,
                'created_at': execution.created_at.isoformat() if execution.created_at else None,
                'node_statistics': {
                    'nodes_executed': execution.metrics.get('nodes_executed', 0),
                    'successful_nodes': execution.metrics.get('successful_nodes', 0),
                    'failed_nodes': execution.metrics.get('failed_nodes', 0),
                    'total_duration': execution.metrics.get('total_duration', 0)
                }
            }
            
            return Response({
                'success': True,
                'execution': execution_data
            })
            
        except TestFlowExecution.DoesNotExist:
            return Response(
                {'error': f'Flow execution {execution_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting flow execution: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListTestFlowsView(APIView):
    """
    List test flows
    GET /api/v1/flows
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """List test flows from database"""
        try:
            project_id = request.query_params.get('project_id')
            flow_type = request.query_params.get('type')
            status_filter = request.query_params.get('status')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Query from database
            queryset = TestFlow.objects.all().order_by('-created_at')
            
            if project_id:
                queryset = queryset.filter(project_id=int(project_id))
            if flow_type:
                queryset = queryset.filter(metadata__type=flow_type)
            if status_filter:
                queryset = queryset.filter(metadata__status=status_filter)
            
            total = queryset.count()
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            flows_qs = queryset[start_idx:end_idx]
            
            flows = []
            for flow in flows_qs:
                flows.append({
                    'id': flow.id,
                    'name': flow.name,
                    'description': flow.scenario_description or '',
                    'type': flow.metadata.get('type', 'unknown') if flow.metadata else 'unknown',
                    'status': flow.metadata.get('status', 'active') if flow.metadata else 'active',
                    'project_id': flow.project_id,
                    'created_at': flow.created_at.isoformat() if flow.created_at else None,
                    'updated_at': flow.updated_at.isoformat() if flow.updated_at else None,
                })
            
            return Response({
                'success': True,
                'flows': flows,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': (total + page_size - 1) // page_size
                }
            })
            
        except Exception as e:
            logger.error(f"Error listing test flows: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListFlowExecutionsView(APIView):
    """
    List flow executions
    GET /api/v1/flows/executions
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """List flow executions from database"""
        try:
            flow_id = request.query_params.get('flow_id')
            status_filter = request.query_params.get('status')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Query from database
            queryset = TestFlowExecution.objects.select_related('test_flow', 'user').order_by('-started_at')
            
            if flow_id:
                queryset = queryset.filter(test_flow_id=int(flow_id))
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if start_date:
                queryset = queryset.filter(started_at__gte=start_date)
            if end_date:
                queryset = queryset.filter(started_at__lte=end_date)
            
            total = queryset.count()
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            executions_qs = queryset[start_idx:end_idx]
            
            executions = []
            for ex in executions_qs:
                executions.append({
                    'id': ex.id,
                    'flow_id': ex.test_flow_id,
                    'flow_name': ex.test_flow.name if ex.test_flow else '',
                    'status': ex.status,
                    'started_at': ex.started_at.isoformat() if ex.started_at else None,
                    'completed_at': ex.completed_at.isoformat() if ex.completed_at else None,
                    'duration_seconds': ex.duration,
                    'initiated_by': ex.user.username if ex.user else 'system',
                    'result_summary': ex.result if ex.result else None,
                })
            
            return Response({
                'success': True,
                'executions': executions,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': (total + page_size - 1) // page_size
                }
            })
            
        except Exception as e:
            logger.error(f"Error listing flow executions: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )