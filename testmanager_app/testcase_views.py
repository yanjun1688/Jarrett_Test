"""
测试用例相关视图
包含：TestCaseViewSet, TestExecutionViewSet
"""

import logging
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import TestCase, TestExecution
from testmanager_app.serializers import (
    TestCaseSerializer, TestCaseCreateSerializer,
    TestExecutionSerializer, TestExecutionCreateSerializer, TestExecutionListSerializer
)
from testmanager_app.viewsets import BaseViewSet, QueryOptimizerMixin, CommonFilterMixin

logger = logging.getLogger(__name__)


class TestCaseViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """测试用例管理API

    继承BaseViewSet实现：
    - 自动设置 permission_classes = [RoleBasedPermission]
    - 自动填充 created_by (TestCase模型有这个字段)
    """
    queryset = TestCase.objects.all()
    serializer_class = TestCaseSerializer

    query_parameters = ['project', 'module', 'priority']

    select_related_fields = ['project', 'module', 'created_by']

    filter_int_fields = ['project', 'module']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TestCaseCreateSerializer
        return TestCaseSerializer

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行测试用例"""
        testcase = self.get_object()

        execution = TestExecution.objects.create(
            test_case=testcase,
            executed_by=request.user,
            status='running'
        )

        return Response({
            'id': execution.id,
            'testcase_id': testcase.id,
            'status': execution.status,
            'message': '测试用例执行已启动'
        }, status=status.HTTP_201_CREATED)


class TestExecutionViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """测试执行记录管理API

    继承的Mixin提供：
    - BaseViewSet: 权限控制和created_by自动填充
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理project参数过滤
    """
    queryset = TestExecution.objects.all()
    serializer_class = TestExecutionSerializer

    select_related_fields = ['test_case', 'api_request', 'executed_by']

    def get_serializer_class(self):
        if self.action == 'list':
            return TestExecutionListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return TestExecutionCreateSerializer
        return TestExecutionSerializer

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
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