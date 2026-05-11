"""
测试执行相关视图
"""

from typing import Any
import logging
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from core.models import TestExecution
from testmanager_app.serializers import (
    TestExecutionSerializer, TestExecutionCreateSerializer, TestExecutionListSerializer
)
from testmanager_app.viewsets import BaseViewSet, QueryOptimizerMixin, CommonFilterMixin

logger = logging.getLogger(__name__)


class TestExecutionViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """测试执行记录管理API

    继承的Mixin提供：
    - BaseViewSet: 权限控制和created_by自动填充
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理project参数过滤
    """
    queryset = TestExecution.objects.all()
    serializer_class = TestExecutionSerializer
    filter_int_fields = ['api_request']

    select_related_fields = ['api_request', 'executed_by']

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action == 'list':
            return TestExecutionListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return TestExecutionCreateSerializer
        return TestExecutionSerializer

    @action(detail=True, methods=['post'])
    def update_status(self, request: Any, pk: Any = None) -> Response:
        """更新执行状态"""
        execution = self.get_object()
        new_status = request.data.get('status')
        actual_result = request.data.get('actual_result', '')

        if new_status not in dict(TestExecution.STATUS_CHOICES):
            return Response(
                {'error': f'无效的状态值: {new_status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution.status = new_status
        if actual_result:
            execution.actual_result = actual_result
        execution.save()

        return Response({
            'id': execution.id,
            'status': execution.status,
            'message': f'状态已更新为: {new_status}'
        })