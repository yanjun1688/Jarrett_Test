"""
报告相关视图
包含：TestReportViewSet, TestReportDataView
"""
# pyright: reportAttributeAccessIssue=false, reportOptionalSubscript=false, reportIndexIssue=false, reportArgumentType=false

import logging
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User

from core.models import Project, TestExecution
from testmanager_app.models import TestReport, ScriptExecution
from testmanager_app.serializers import (
    TestReportSerializer, GenerateReportSerializer,
    UserListSerializer, TestExecutionListSerializer, ScriptExecutionSerializer
)
from testmanager_app.viewsets import BaseViewSet, QueryOptimizerMixin, CommonFilterMixin
from testmanager_app.utils.api_exceptions import api_exception_handler
from testmanager_app.services import ReportService

logger = logging.getLogger(__name__)


class TestReportViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """测试报告API

    继承的Mixin提供：
    - BaseViewSet: 权限控制和created_by自动填充
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理project参数过滤

    支持的查询参数：
    - ?project=1: 按项目ID过滤
    """
    queryset = TestReport.objects.all()
    serializer_class = TestReportSerializer

    # 查询优化配置
    select_related_fields = ['project', 'created_by']

    # 过滤器配置
    filter_int_fields = ['project']

    @api_exception_handler
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def generate_report(self, request):
        """
        生成测试报告（使用 Serializer 验证，带事务保护）

        验证流程：
        1. Serializer 自动验证字段存在性和类型
        2. Serializer 业务规则验证（日期范围）
        3. 通过验证后，validated_data 包含已转换的对象

        优化：
        - 使用@api_exception_handler统一异常处理
        - 移除重复的try-except块
        - 代码从45行减少到25行
        """
        serializer = GenerateReportSerializer(data=request.data)

        # 统一验证（包含字段验证、类型转换、业务规则）
        if not serializer.is_valid():
            logger.warning(f"报告参数验证失败: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 直接获取验证后的数据（已转换类型）
        # - project 已是 Project 对象
        # - start_date 和 end_date 已是 datetime 对象
        project = serializer.validated_data['project_id']  # 已验证并转换为 Project 对象
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        created_by = request.user if request.user.is_authenticated else None

        # 生成报告
        report_data = ReportService.generate_report(
            project=project,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by  # type: ignore[arg-type]
        )

        return Response(report_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def api_test_logs(self, request):
        """获取API测试日志列表（分页）"""
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        queryset = TestExecution.objects.filter(test_type='api').select_related(
            'api_request', 'executed_by'
        ).order_by('-executed_at')
        
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        results = queryset[start:end]
        
        serializer = TestExecutionListSerializer(results, many=True)
        return Response({
            'results': serializer.data,
            'count': total
        })

    @action(detail=False, methods=['get'])
    def ui_test_logs(self, request):
        """获取UI测试日志列表（分页）"""
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        queryset = ScriptExecution.objects.all().select_related(
            'script', 'executor'
        ).order_by('-started_at')
        
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        results = queryset[start:end]
        
        serializer = ScriptExecutionSerializer(results, many=True)
        return Response({
            'results': serializer.data,
            'count': total
        })


class TestReportDataView(APIView):
    """测试报告数据API（独立视图，不继承ViewSet）"""

    permission_classes = []  # 临时开放，生产环境需要权限控制

    def get(self, request):
        """获取测试报告数据（支持多种查询参数）"""
        try:
            project_id = request.query_params.get('project')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            created_by = request.query_params.get('created_by')

            if project_id:
                try:
                    project = Project.objects.get(id=project_id)
                except Project.DoesNotExist:
                    return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)
            else:
                project = None

            report_data = ReportService.get_report_data(
                project=project,
                start_date=start_date,
                end_date=end_date,
                created_by=created_by
            )

            return Response(report_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"获取报告数据失败: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)