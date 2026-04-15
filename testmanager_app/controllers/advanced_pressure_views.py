"""
高级压测API视图
基于Locust的分布式压测功能
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from testmanager_app.utils.api_exceptions import api_exception_handler
from shared.utils.logging_utils import get_logger
from testmanager_app.viewsets.base import QueryOptimizerMixin, CommonFilterMixin, BaseViewSet

from testmanager_app.models import (
    AdvancedPressureTestConfig,
    AdvancedPressureTestExecution
)
from testmanager_app.serializers import (
    AdvancedPressureTestConfigSerializer,
    AdvancedPressureTestConfigCreateSerializer,
    AdvancedPressureTestExecutionSerializer,
    AdvancedPressureTestExecutionDetailSerializer,
    AdvancedPressureTestExecuteResponseSerializer
)

logger = get_logger(__name__)


class AdvancedPressureTestConfigViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """高级压测配置API"""
    
    queryset = AdvancedPressureTestConfig.objects.all()
    serializer_class = AdvancedPressureTestConfigSerializer
    
    # 查询优化
    select_related_fields = ['project', 'created_by']
    
    # 过滤器配置
    filter_int_fields = ['project', 'user_count', 'worker_count']
    filter_choice_fields: Dict[str, List[str]] = {}
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AdvancedPressureTestConfigCreateSerializer
        return AdvancedPressureTestConfigSerializer
    
    def perform_create(self, serializer):
        """创建时设置创建人"""
        serializer.save(created_by=self.request.user)
    
    @api_exception_handler
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行高级压测"""
        config = self.get_object()
        
        logger.info(f"[AdvancedPressureTest] Execute requested - config_id={config.id}, user={request.user}")
        
        execution: AdvancedPressureTestExecution = AdvancedPressureTestExecution.objects.create(
            config=config,
            executor=request.user,
            status='pending'
        )
        
        websocket_url = f"/ws/advanced-pressure-test/{execution.id}/"
        
        web_ui_url = None
        if config.enable_web_ui:
            web_ui_url = f"http://localhost:{config.web_ui_port}"
        
        logger.info(f"[AdvancedPressureTest] Created execution - id={execution.id}, ws_url={websocket_url}")
        
        response_data = {
            'execution_id': execution.id,
            'websocket_url': websocket_url,
            'web_ui_url': web_ui_url,
            'message': '高级压测已创建，请通过WebSocket连接后开始执行'
        }
        
        serializer = AdvancedPressureTestExecuteResponseSerializer(response_data)
        return Response(serializer.data)
    
    @api_exception_handler
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """获取压测历史记录"""
        config = self.get_object()
        executions = config.executions.order_by('-started_at')[:10]
        serializer = AdvancedPressureTestExecutionSerializer(executions, many=True)
        return Response(serializer.data)


class AdvancedPressureTestExecutionViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """高级压测执行记录API"""
    
    queryset = AdvancedPressureTestExecution.objects.all()
    serializer_class = AdvancedPressureTestExecutionSerializer
    
    # 查询优化
    select_related_fields = ['config', 'executor']
    
    # 过滤器配置
    filter_int_fields = ['config']
    filter_choice_fields = {
        'status': ['pending', 'running', 'completed', 'stopped', 'failed']
    }
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AdvancedPressureTestExecutionDetailSerializer
        return AdvancedPressureTestExecutionSerializer
    
    @api_exception_handler
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止压测执行"""
        execution = self.get_object()
        
        if execution.status != 'running':
            return Response(
                {'error': '只能停止运行中的压测'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 通过WebSocket发送停止信号
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"advanced_pressure_test_{execution.id}",
                {
                    'type': 'stop_test',
                    'message': 'Stop requested from API'
                }
            )
        
        logger.info(f"[AdvancedPressureTest] Stop requested - execution_id={execution.id}")
        
        return Response({
            'message': '停止信号已发送',
            'execution_id': execution.id
        })
    
    @api_exception_handler
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """获取详细结果（分页）"""
        execution = self.get_object()
        
        if not execution.raw_results:
            return Response({'results': [], 'count': 0})
        
        # 分页参数
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 100))
        
        all_results = execution.raw_results
        total = len(all_results)
        
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = all_results[start:end]
        
        return Response({
            'results': paginated_results,
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        })
    
    @api_exception_handler
    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """获取HTML报告"""
        execution = self.get_object()
        
        if not execution.report_html:
            return Response(
                {'error': '报告尚未生成'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            'report_html': execution.report_html
        })