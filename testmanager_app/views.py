import json
import logging
import os
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from testmanager_app.models import AuthToken
from rest_framework.exceptions import ValidationError
from testmanager_app.permissions import RoleBasedPermission
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
import asyncio
from asgiref.sync import sync_to_async
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.contrib.auth.models import User
from django.views import View
from testmanager_app.models import (
    Project, Module, TestCase, TestExecution, TestReport, TestScript,
    ScriptExecution, ApiRequest, ApiAssertion, RequestCollection,
    CollectionRequest, CollectionExecution, FeatureTestCase, TestResult, Role, UserRole
)


# 配置日志记录器
logger = logging.getLogger(__name__)

# 导入统一的异常处理和日志记录工具
from testmanager_app.utils.api_exceptions import (
    api_exception_handler,
    async_api_exception_handler,
    BusinessException,
    ResourceNotFoundException,
    ValidationFailedException
)
from testmanager_app.utils.api_logger import (
    log_api_request,
    log_async_api_request,
    RequestLogger,
    ExecutionLogger
)

from .serializers import (
    ProjectSerializer, ModuleSerializer, TestCaseSerializer, TestCaseCreateSerializer,
    TestExecutionSerializer, TestExecutionCreateSerializer, TestReportSerializer,
    GenerateReportSerializer, ProjectStatisticsSerializer, TestScriptSerializer, TestScriptCreateSerializer,
    ScriptExecutionSerializer, ScriptExecutionCreateSerializer, ApiRequestSerializer,
    ApiRequestCreateSerializer, ApiAssertionSerializer, ApiAssertionCreateSerializer,
    RequestCollectionSerializer, RequestCollectionCreateSerializer, CollectionExecutionSerializer,
    CollectionExecutionCreateSerializer, FeatureTestCaseSerializer, TestResultSerializer,
    RoleSerializer, UserRoleSerializer, UserListSerializer
)


from testmanager_app.viewsets import BaseViewSet, QueryOptimizerMixin, CommonFilterMixin
from testmanager_app.viewsets.cache_mixin import CacheMixin


# 导入服务
from testmanager_app.services import (
    get_project_statistics,
    TestExecutionService,
    ReportService
)

# 导入异步执行器
from testmanager_app.async_utils import (
    execute_single_request_async,
    validate_assertion_common
)




def _safe_get_int_param(request, param_name):
    """安全获取整数查询参数"""
    value = request.query_params.get(param_name, None)
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_get_str_param(request, param_name):
    """安全获取字符串查询参数并进行简单验证"""
    value = request.query_params.get(param_name, None)
    if value is None:
        return None

    import re
    # 只允许字母、数字、空格、下划线、连字符、点和基本字符
    # 阻止SQL注入和XSS攻击
    if re.match(r'^[a-zA-Z0-9\s\-_\.\u4e00-\u9fa5]{0,200}$', str(value)):
        return value
    return None


def _safe_get_choice_param(request, param_name, choices):
    """安全获取选项查询参数"""
    value = request.query_params.get(param_name, None)
    if value is None or value not in choices:
        return None
    return value


class ProjectViewSet(BaseViewSet):
    """项目管理API

    继承BaseViewSet实现：
    - 自动设置 permission_classes = [RoleBasedPermission]
    - 自动填充 created_by (Project模型有这个字段)
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """获取项目统计信息"""
        data = get_project_statistics(pk)
        if data is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = ProjectStatisticsSerializer(data)
        return Response(serializer.data)


class ModuleViewSet(BaseViewSet, QueryOptimizerMixin, CommonFilterMixin):
    """模块管理API

    继承的Mixin提供：
    - BaseViewSet: 权限控制和created_by自动填充
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理project参数过滤
    """
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer

    # 查询优化配置
    select_related_fields = ['project', 'created_by']

    # 过滤器配置
    filter_int_fields = ['project']


class TestCaseViewSet(BaseViewSet, QueryOptimizerMixin, CommonFilterMixin):
    """测试用例管理API

    继承的Mixin提供：
    - BaseViewSet: 权限控制和created_by自动填充
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理多个查询参数

    支持的查询参数：
    - ?project=1: 项目ID过滤
    - ?module=2: 模块ID过滤
    - ?priority=high: 优先级过滤
    - ?project__name__icontains=xxx: 项目名称模糊搜索（URL中写作 ?project__name__icontains=xxx）
    - ?module__name__icontains=yyy: 模块名称模糊搜索（URL中写作 ?module__name__icontains=yyy）
    """
    queryset = TestCase.objects.all()
    serializer_class = TestCaseSerializer

    # 查询优化配置
    select_related_fields = ['project', 'module', 'created_by']

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """批量删除测试用例"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'ids is required'}, status=status.HTTP_400_BAD_REQUEST)

        # 限制批量删除数量
        if len(ids) > 50:
            return Response({'error': '批量删除最多支持50条记录'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            deleted_count, _ = TestCase.objects.filter(id__in=ids).delete()
            return Response({'deleted_count': deleted_count}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 过滤器配置 - 声明式定义，自动处理
    filter_int_fields = ['project', 'module']
    filter_choice_fields = {'priority': ['low', 'medium', 'high']}
    filter_related_icontains = ['project__name', 'module__name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TestCaseCreateSerializer
        return TestCaseSerializer


class TestExecutionViewSet(BaseViewSet, QueryOptimizerMixin, CommonFilterMixin):
    """测试执行记录API

    继承的Mixin提供：
    - BaseViewSet: 权限控制
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理多个查询参数

    支持的查询参数：
    - ?testcase=1: 测试用例ID过滤
    - ?api_request=2: API请求ID过滤
    - ?status=pending: 状态过滤
    - ?testcase__project=3: 项目ID过滤
    """
    queryset = TestExecution.objects.all()
    serializer_class = TestExecutionSerializer

    # 查询优化配置
    select_related_fields = ['testcase', 'api_request', 'executor']

    # 过滤器配置
    filter_int_fields = ['testcase', 'api_request', 'testcase__project']
    filter_choice_fields = {
        'status': ['pending', 'passed', 'failed', 'blocked', 'skipped']
    }

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TestExecutionCreateSerializer
        return TestExecutionSerializer



    @api_exception_handler
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        执行已保存的API测试用例（优化版）

        职责分离：
        - 调用TestExecutionService处理核心业务逻辑
        - 统一异常处理
        - 格式化的响应

        优化：
        - 使用@api_exception_handler统一异常处理
        - 移除重复的try-except块
        - 代码从29行减少到8行
        """
        execution = self.get_object()

        # 调用服务层处理执行逻辑
        result = TestExecutionService.execute_api_test(execution, request.user)
        return Response(result)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """
        获取执行记录的实时日志（支持缓存）
        
        执行记录创建后不会变化，可以缓存以提高性能
        缓存时间：1小时（执行记录不会变化）
        """
        from django.core.cache import cache
        from testmanager_app.utils.cache_helper import get_cache_key
        
        execution = self.get_object()

        # 生成缓存键（基于执行记录ID和更新时间）
        cache_key = get_cache_key('execution_logs', execution.id, updated_at=str(execution.executed_at))
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Execution logs cache hit: execution_id={execution.id}")
            return Response(cached_data)
        
        # 计算执行耗时（毫秒）
        execution_duration_ms = None
        if execution.execution_duration:
            execution_duration_ms = execution.execution_duration.total_seconds() * 1000

        data = {
            'execution_id': execution.id,
            'status': execution.status,
            'logs': execution.api_logs.split('\n') if execution.api_logs else [],
            'api_response_data': execution.api_response_data,
            'execution_duration_ms': execution_duration_ms
        }
        
        # 存入缓存（1小时，执行记录不会变化）
        cache.set(cache_key, data, timeout=3600)
        logger.debug(f"Execution logs cached: execution_id={execution.id}")
        
        return Response(data)


class TestReportViewSet(BaseViewSet, QueryOptimizerMixin, CommonFilterMixin):
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
        start_date = serializer.validated_data['start_date']  # 已转换为 datetime
        end_date = serializer.validated_data['end_date']  # 已转换为 datetime

        # 调用服务生成报告
        report = ReportService.generate_report(
            project=project,
            start_date=start_date,
            end_date=end_date,
            created_by=request.user if request.user.is_authenticated else None
        )

        # 返回结果
        result_serializer = TestReportSerializer(report)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)

    @api_exception_handler
    @action(detail=False, methods=['get'], url_path='api-test-logs')
    def api_test_logs(self, request):
        """
        获取API测试执行日志列表（分页查询，性能优化）
        
        查询参数：
        - page: 页码（默认1）
        - page_size: 每页数量（默认20，最大100）
        - project: 项目ID过滤（可选）
        - status: 状态过滤（可选：passed, failed, pending等）
        
        性能优化：
        - 使用轻量级序列化器，只返回必要字段
        - 使用select_related避免N+1查询
        - 只查询test_type='api'的记录
        - 不返回api_logs和api_response_data等大字段
        """
        from rest_framework.pagination import PageNumberPagination
        from testmanager_app.serializers import TestExecutionListSerializer
        
        # 获取查询参数
        project_id = request.query_params.get('project')
        status_filter = request.query_params.get('status')
        page_size = min(int(request.query_params.get('page_size', 20)), 100)  # 最大100
        
        # 构建查询集，只查询API测试类型
        queryset = TestExecution.objects.filter(test_type='api')
        
        # 应用过滤器
        if project_id:
            queryset = queryset.filter(api_request__project_id=project_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 使用select_related优化查询，避免N+1问题
        queryset = queryset.select_related('api_request', 'executor').order_by('-executed_at')
        
        # 分页
        paginator = PageNumberPagination()
        paginator.page_size = page_size
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        
        # 序列化
        serializer = TestExecutionListSerializer(paginated_queryset, many=True)
        
        # 返回分页结果
        return paginator.get_paginated_response(serializer.data)
    
    @api_exception_handler
    @action(detail=False, methods=['get'], url_path='ui-test-logs')
    def ui_test_logs(self, request):
        """
        获取UI测试执行日志列表（分页查询，性能优化）
        
        查询参数：
        - page: 页码（默认1）
        - page_size: 每页数量（默认20，最大100）
        - project: 项目ID过滤（可选）
        - status: 状态过滤（可选：passed, failed, pending, running等）
        
        性能优化：
        - 使用轻量级序列化器，只返回必要字段
        - 使用select_related避免N+1查询
        - 不返回execution_log等大字段
        """
        from rest_framework.pagination import PageNumberPagination
        from test_ui_app.models import UITestExecution
        from test_ui_app.serializers import UITestExecutionListSerializer
        
        # 获取查询参数
        project_id = request.query_params.get('project')
        status_filter = request.query_params.get('status')
        page_size = min(int(request.query_params.get('page_size', 20)), 100)  # 最大100
        
        # 构建查询集
        queryset = UITestExecution.objects.all()
        
        # 应用过滤器
        if project_id:
            queryset = queryset.filter(script__project_id=project_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 使用select_related优化查询，避免N+1问题
        queryset = queryset.select_related('script', 'executed_by').order_by('-created_at')
        
        # 分页
        paginator = PageNumberPagination()
        paginator.page_size = page_size
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        
        # 序列化
        serializer = UITestExecutionListSerializer(paginated_queryset, many=True)
        
        # 返回分页结果
        return paginator.get_paginated_response(serializer.data)


class TestReportDataView(APIView):
    """
    API view to get combined data for the test report page.
    支持缓存优化，报告数据生成后不会变化
    """
    permission_classes = [RoleBasedPermission]
    
    def get(self, request, format=None):
        """
        Return a list of all reports and statistics for the first project.
        支持缓存，缓存时间：5分钟（报告可能新增，但已有报告不会变化）
        """
        from django.core.cache import cache
        from testmanager_app.utils.cache_helper import get_cache_key
        
        # 生成缓存键（基于最新的报告创建时间）
        latest_report = TestReport.objects.first()
        cache_key = get_cache_key(
            'report_data',
            latest_id=latest_report.id if latest_report else 0,
            latest_created=str(latest_report.created_at) if latest_report else 'none'
        )
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug("Report data cache hit")
            return Response(cached_data)
        
        # Get reports
        reports = TestReport.objects.all().order_by('-created_at')
        reports_serializer = TestReportSerializer(reports, many=True)

        # Get statistics for the first project
        statistics_data = None
        project = Project.objects.first()
        if project:
            stats = get_project_statistics(project.id)
            if stats:
                statistics_serializer = ProjectStatisticsSerializer(stats)
                statistics_data = statistics_serializer.data

        data = {
            'reports': reports_serializer.data,
            'statistics': [statistics_data] if statistics_data else []
        }
        
        # 存入缓存（5分钟，报告可能新增）
        cache.set(cache_key, data, timeout=300)
        logger.debug("Report data cached")
        
        return Response(data)


class TestScriptViewSet(CacheMixin, BaseViewSet, QueryOptimizerMixin, CommonFilterMixin):
    """测试脚本管理API

    继承的Mixin提供：
    - CacheMixin: 列表和详情查询缓存支持
    - BaseViewSet: 权限控制和created_by自动填充
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理project参数过滤

    支持的查询参数：
    - ?project=1: 按项目ID过滤

    特殊功能：
    - execute action: 执行测试脚本（支持api/json/yaml/selenium类型）
    
    缓存策略：
    - 列表查询：缓存2分钟（脚本配置变化不频繁）
    - 详情查询：缓存5分钟（脚本配置变化不频繁）
    """
    queryset = TestScript.objects.all()
    serializer_class = TestScriptSerializer

    # 查询优化配置
    select_related_fields = ['project', 'created_by']

    # 过滤器配置
    filter_int_fields = ['project']
    
    # 缓存配置
    cache_timeout = 120  # 列表查询缓存2分钟
    cache_list = True
    cache_retrieve = True
    
    def retrieve(self, request, *args, **kwargs):
        """
        详情查询（缓存5分钟）
        """
        # 临时设置更长的缓存时间用于详情查询
        original_timeout = self.cache_timeout
        self.cache_timeout = 300  # 5分钟
        try:
            return super().retrieve(request, *args, **kwargs)
        finally:
            self.cache_timeout = original_timeout

    # 以下脚本执行逻辑完整保留
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TestScriptCreateSerializer
        return TestScriptSerializer

    def _create_script_execution_record(self, script, request_user):
        """创建脚本执行记录"""
        return ScriptExecution.objects.create(
            script=script,
            executor=request_user if request_user.is_authenticated else None,
            status='running',
            started_at=timezone.now()
        )

 

    def _process_script_result(self, execution, result_status, error_message=None, output=None):
        """处理脚本执行结果并更新记录"""
        execution.status = result_status
        if error_message:
            execution.error_message = error_message
        if output:
            execution.output = output
        execution.finished_at = timezone.now()
        execution.duration = execution.finished_at - execution.started_at
        execution.save()

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        执行测试脚本（使用策略模式重构）

        职责分离：
        - 本方法：协调执行流程、异常处理、记录日志
        - 策略工厂：创建合适的执行策略
        - 具体策略：执行脚本并返回结果

        遵循开闭原则：新增脚本类型只需添加新的策略类，无需修改此核心代码
        """
        script = self.get_object()
        execution = self._create_script_execution_record(script, request.user)

        try:
            # 使用策略工厂获取合适的执行策略
            from testmanager_app.execution_strategies import ScriptExecutionStrategyFactory

            strategy = ScriptExecutionStrategyFactory.get_strategy(script)

            # 执行脚本（策略负责具体执行逻辑）
            execution = strategy.execute(script, execution)

            # 保存执行结果
            self._process_script_result(
                execution,
                execution.status,
                error_message=execution.error_message,
                output=execution.output
            )

        except Exception as e:
            logger.exception(f"脚本执行失败: script_id={script.id}, error={str(e)}")
            self._process_script_result(execution, 'failed', error_message=str(e))
            serializer = ScriptExecutionSerializer(execution)
            return Response(serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 返回执行结果
        serializer = ScriptExecutionSerializer(execution)
        return Response(serializer.data)


class ScriptExecutionViewSet(CacheMixin, BaseViewSet, QueryOptimizerMixin, CommonFilterMixin):
    """脚本执行记录API

    继承的Mixin提供：
    - CacheMixin: 列表和详情查询缓存支持
    - BaseViewSet: 权限控制和executor自动填充
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理查询参数过滤

    支持的查询参数：
    - ?script=1: 按脚本ID过滤
    - ?status=success: 按状态过滤
    
    缓存策略：
    - 列表查询：缓存2分钟（执行记录可能新增）
    - 详情查询：缓存1小时（执行完成后不会变化）
    """
    queryset = ScriptExecution.objects.all()
    serializer_class = ScriptExecutionSerializer

    # 查询优化配置
    select_related_fields = ['script', 'executor']

    # 过滤器配置
    filter_int_fields = ['script']
    filter_choice_fields = {
        'status': ['pending', 'running', 'success', 'failed', 'timeout', 'error']
    }
    
    # 缓存配置
    cache_timeout = 120  # 列表查询缓存2分钟
    cache_list = True
    cache_retrieve = True
    
    def retrieve(self, request, *args, **kwargs):
        """
        详情查询（执行完成后缓存1小时）
        """
        # 临时设置更长的缓存时间用于详情查询
        original_timeout = self.cache_timeout
        self.cache_timeout = 3600  # 1小时
        try:
            return super().retrieve(request, *args, **kwargs)
        finally:
            self.cache_timeout = original_timeout

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ScriptExecutionCreateSerializer
        return ScriptExecutionSerializer







class ApiRequestViewSet(CacheMixin, BaseViewSet, QueryOptimizerMixin, CommonFilterMixin):
    """
    API请求管理API

    继承的Mixin提供：
    - CacheMixin: 列表和详情查询缓存支持
    - BaseViewSet: 权限控制和created_by自动填充
    - QueryOptimizerMixin: 自动select_related和prefetch_related优化
    - CommonFilterMixin: 自动处理project参数过滤

    支持的查询参数：
    - ?project=1: 按项目ID过滤

    特殊功能：
    - execute action: 执行单个API请求（同步版本）
    - execute_batch action: 批量异步执行API请求（行为统一版本）
    
    缓存策略：
    - 列表查询：缓存2分钟（API请求配置变化不频繁）
    - 详情查询：缓存5分钟（API请求配置变化不频繁）

    执行接口行为一致性：
    ========================================
    execute() 和 execute_batch() 都满足以下行为：

    1. 创建 TestExecution 记录
       - 保存执行状态（passed/failed）
       - 保存实际结果和响应数据
       - 保存详细日志（开始、请求、响应、断言、完成）
       - 保存执行时长和执行者信息

    2. 记录详细执行日志
       - 请求发送和响应接收
       - 响应体解析（JSON/文本）
       - 断言验证结果（通过/失败）
       - 断言统计（通过数量/总数）

    3. 执行断言验证
       - 支持 status_code、response_time、response_body、response_header 断言
       - 支持多种比较方式（equals、contains、not_contains、greater_than、less_than）
       - 验证结果会保存到数据库

    4. 返回执行结果
       - status_code: HTTP状态码
       - response_time: 响应时间（秒）
       - response_body: 响应体内容
       - assertions: 断言结果列表
       - passed_count: 通过的断言数量
       - total_assertions: 断言总数
       - error: 错误信息（如果有）
       - success: 是否成功（无错误且所有断言通过）

    两个接口的差异：
    ========================================
    - execute(): 同步执行，适合单个请求测试
      * 使用事件循环同步执行异步请求
      * 返回单个结果对象

    - execute_batch(): 异步并发执行，适合批量测试场景
      * 使用 async/await 实现并发执行
      * 返回结果列表（按 request_ids 顺序）
      * 单个请求失败不影响其他请求继续执行
      * 限制最大批量数：1000个请求

    使用建议：
    ========================================
    - 调试单个API时使用 execute()
    - 需要批量验证多个API时使用 execute_batch()
    - 所有执行历史都可以在 TestExecution 记录中查看
    - 日志和结果数据会永久保存，便于后续分析
    """
    queryset = ApiRequest.objects.all()
    serializer_class = ApiRequestSerializer

    # 查询优化配置
    select_related_fields = ['project', 'created_by']
    prefetch_related_fields = ['assertions']

    # 过滤器配置
    filter_int_fields = ['project']
    
    # 缓存配置
    cache_timeout = 120  # 列表查询缓存2分钟
    cache_list = True
    cache_retrieve = True
    
    def retrieve(self, request, *args, **kwargs):
        """
        详情查询（缓存5分钟）
        """
        # 临时设置更长的缓存时间用于详情查询
        original_timeout = self.cache_timeout
        self.cache_timeout = 300  # 5分钟
        try:
            return super().retrieve(request, *args, **kwargs)
        finally:
            self.cache_timeout = original_timeout

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ApiRequestCreateSerializer
        return ApiRequestSerializer

    # execute 和 execute_batch action 保持原样（在下面）

    @action(detail=True, methods=['post'])
    @api_exception_handler
    def execute(self, request, pk=None):
        """
        执行单个API请求（异步 Celery 模式）

        架构优化：
        - 先创建 TestExecution 记录（status=pending）
        - 提交 Celery 任务异步执行
        - 立即返回 execution_id，前端可轮询结果
        - 避免在 Web 请求中阻塞等待外部 HTTP 调用
        """
        from testmanager_app.tasks import execute_api_request_task
        from testmanager_app.models import TestExecution
        
        api_request = self.get_object()
        
        # 1. 创建 TestExecution 记录（status=pending）
        execution = TestExecution.objects.create(
            test_type='api',
            api_request=api_request,
            executor=request.user if request.user.is_authenticated else None,
            status='pending',
            executed_at=timezone.now()
        )
        
        # 2. 提交 Celery 任务
        user_id = request.user.id if request.user.is_authenticated else None
        task = execute_api_request_task.delay(
            api_request_id=api_request.id,
            execution_id=execution.id,
            user_id=user_id
        )
        
        logger.info(f"API request execution submitted: api_request_id={api_request.id}, "
                    f"execution_id={execution.id}, task_id={task.id}")
        
        # 3. 返回 execution_id，前端轮询结果
        return Response({
            'success': True,
            'execution_id': execution.id,
            'task_id': task.id,
            'status': 'pending',
            'message': '任务已提交，正在执行中'
        })

    @action(detail=False, methods=['post'], url_path='execute-batch')
    @async_api_exception_handler
    async def execute_batch(self, request):
        """
        批量异步执行API请求（优化版 - 行为统一）

        行为一致性（与 execute() 一致）：
        - 每个请求都会创建 TestExecution 记录，保存执行历史
        - 记录详细执行日志（开始、请求、响应、断言、完成）
        - 执行断言验证
        - 返回执行结果列表

        特点：
        - 异步并发执行，适合批量测试场景
        - 自动跳过不存在的请求，继续执行后续请求
        - 限制最大批量数：1000个请求

        返回:
            list: 包含每个请求的执行结果，格式与 execute() 相同

        异常处理:
            - request_ids 为空：返回 400 错误
            - request_ids 超过 1000 个：返回 400 错误
            - 单个请求失败：记录错误日志，继续执行其他请求

        优化：
        - 使用@async_api_exception_handler统一异常处理
        - 移除重复的try-except块
        - 代码从44行减少到14行
        """
        # 调用服务层批量执行
        results = await TestExecutionService.execute_batch_api_requests(
            request.data.get('request_ids', []),
            request.user
        )
        return Response(results)

    def _validate_assertion(self, response, assertion):
        """
        验证单个断言（异步版本）

        Args:
            response: HTTP响应对象
            assertion: 断言对象

        Returns:
            bool: 验证是否通过
        """
        if response is None:
            logger.warning("Cannot validate assertion: response is None")
            return False

        # 创建getter函数以适配公共验证逻辑
        def get_actual_value():
            if assertion.assertion_type == 'status_code':
                return response.status_code
            elif assertion.assertion_type == 'response_time':
                return response.elapsed.total_seconds()
            elif assertion.assertion_type == 'response_body':
                return response.text
            elif assertion.assertion_type == 'response_header':
                return response.headers.get(assertion.field, '')
            else:
                return None

        return validate_assertion_common(
            assertion.assertion_type,
            get_actual_value,
            assertion.comparison,
            assertion.expected_value
        )

    def _validate_assertion_sync(self, response, assertion, status_code, response_time, response_body):
        """
        同步版本的断言验证（用于 requests）

        Args:
            response: HTTP响应对象（可能为None）
            assertion: 断言对象
            status_code: 状态码
            response_time: 响应时间
            response_body: 响应体

        Returns:
            bool: 验证是否通过
        """
        if response is None and status_code is None:
            logger.warning("Cannot validate assertion: both response and status_code are None")
            return False

        # 创建getter函数以适配公共验证逻辑
        def get_actual_value():
            if assertion.assertion_type == 'status_code':
                return status_code
            elif assertion.assertion_type == 'response_time':
                return response_time
            elif assertion.assertion_type == 'response_body':
                return response_body
            elif assertion.assertion_type == 'response_header':
                return response.headers.get(assertion.field, '') if response else ''
            else:
                return None

        return validate_assertion_common(
            assertion.assertion_type,
            get_actual_value,
            assertion.comparison,
            assertion.expected_value
        )




class ApiAssertionViewSet(BaseViewSet, QueryOptimizerMixin, CommonFilterMixin):
    """API断言管理API

    继承的Mixin提供：
    - BaseViewSet: 权限控制和created_by自动填充
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理api_request参数过滤

    支持的查询参数：
    - ?api_request=1: 按API请求ID过滤
    """
    queryset = ApiAssertion.objects.all()
    serializer_class = ApiAssertionSerializer

    # 查询优化配置
    select_related_fields = ['api_request']

    # 过滤器配置
    filter_int_fields = ['api_request']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ApiAssertionCreateSerializer
        return ApiAssertionSerializer




class RequestCollectionViewSet(CacheMixin, BaseViewSet, QueryOptimizerMixin, CommonFilterMixin):
    """请求集合管理API

    继承的Mixin提供：
    - CacheMixin: 列表和详情查询缓存支持
    - BaseViewSet: 权限控制和created_by自动填充
    - QueryOptimizerMixin: 自动select_related和prefetch_related优化
    - CommonFilterMixin: 自动处理project参数过滤

    支持的查询参数：
    - ?project=1: 按项目ID过滤

    特殊功能：
    - execute action: 执行请求集合 - 支持三种模式（concurrent/sequential/chain）
    
    缓存策略：
    - 列表查询：缓存2分钟（集合配置变化不频繁）
    - 详情查询：缓存5分钟（集合配置变化不频繁）
    """
    queryset = RequestCollection.objects.all()
    serializer_class = RequestCollectionSerializer

    # 查询优化配置
    select_related_fields = ['project', 'created_by']
    prefetch_related_fields = ['collection_requests__api_request']

    # 过滤器配置
    filter_int_fields = ['project']
    
    # 缓存配置
    cache_timeout = 120  # 列表查询缓存2分钟
    cache_list = True
    cache_retrieve = True
    
    def retrieve(self, request, *args, **kwargs):
        """
        详情查询（缓存5分钟）
        """
        # 临时设置更长的缓存时间用于详情查询
        original_timeout = self.cache_timeout
        self.cache_timeout = 300  # 5分钟
        try:
            return super().retrieve(request, *args, **kwargs)
        finally:
            self.cache_timeout = original_timeout

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RequestCollectionCreateSerializer
        return RequestCollectionSerializer

    

    @api_exception_handler
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        执行请求集合 - 统一使用 Celery 异步模式

        架构优化：
        - 统一使用 Celery 任务执行，避免事件循环冲突
        - 立即返回 execution_id，前端轮询获取结果
        - 支持三种执行模式：并发、顺序、链式
        - 每个请求创建 TestExecution 记录
        - CollectionExecution 作为聚合根
        """
        from testmanager_app.tasks import execute_collection_task

        # 获取集合对象
        try:
            collection = RequestCollection.objects.prefetch_related(
                'collection_requests__api_request'
            ).get(pk=pk)
        except RequestCollection.DoesNotExist:
            raise ResourceNotFoundException("RequestCollection", pk)

        # 获取请求列表并验证
        collection_requests = list(
            collection.collection_requests.select_related('api_request')
            .order_by('order_index')
        )

        if len(collection_requests) > 1000:
            logger.warning(f"Too many requests in collection: {len(collection_requests)}")
            raise ValidationError("Cannot execute collection with more than 1000 requests")

        if len(collection_requests) == 0:
            raise ValidationError("Collection has no requests to execute")

        # 创建 CollectionExecution 记录（状态为 pending）
        collection_exec = CollectionExecution.objects.create(
            collection=collection,
            executor=request.user if request.user.is_authenticated else None,
            status='pending',
            started_at=timezone.now(),
            total_requests=len(collection_requests),
            passed_requests=0,
            failed_requests=0
        )

        # 提交 Celery 任务
        user_id = request.user.id if request.user.is_authenticated else None
        task = execute_collection_task.delay(
            collection_id=pk,
            execution_id=collection_exec.id,
            user_id=user_id
        )

        logger.info(
            f"Collection execution task submitted: "
            f"collection_id={pk}, execution_id={collection_exec.id}, task_id={task.id}"
        )

        return Response({
            'success': True,
            'message': '任务已提交，正在执行中',
            'task_id': task.id,
            'execution_id': collection_exec.id,
            'collection_id': int(pk),
            'collection_name': collection.name,
            'execution_mode': collection.execution_mode,
            'total_requests': len(collection_requests),
        }, status=status.HTTP_202_ACCEPTED)

    @api_exception_handler
    @action(detail=True, methods=['post'])
    def execute_async(self, request, pk=None):
        """
        异步执行请求集合 - 提交到 Celery 后台执行
        
        优点：
        - 立即返回，不阻塞 HTTP 连接
        - 支持大批量请求执行（不会 HTTP 超时）
        - 可通过 task_status 端点查询执行进度
        
        Returns:
            dict: 包含 task_id 和 execution_id，用于后续查询
        """
        from testmanager_app.tasks import execute_collection_task
        
        # 获取集合对象
        try:
            collection = RequestCollection.objects.prefetch_related(
                'collection_requests__api_request'
            ).get(pk=pk)
        except RequestCollection.DoesNotExist:
            raise ResourceNotFoundException("RequestCollection", pk)
        
        # 获取请求列表并验证
        collection_requests = list(
            collection.collection_requests.select_related('api_request')
            .order_by('order_index')
        )
        
        if len(collection_requests) > 1000:
            logger.warning(f"Too many requests in collection: {len(collection_requests)}")
            raise ValidationError("Cannot execute collection with more than 1000 requests")
        
        if len(collection_requests) == 0:
            raise ValidationError("Collection has no requests to execute")
        
        # 创建 CollectionExecution 记录（状态为 pending）
        collection_exec = CollectionExecution.objects.create(
            collection=collection,
            executor=request.user if request.user.is_authenticated else None,
            status='pending',
            started_at=timezone.now(),
            total_requests=len(collection_requests),
            passed_requests=0,
            failed_requests=0
        )
        
        # 提交 Celery 任务
        user_id = request.user.id if request.user.is_authenticated else None
        task = execute_collection_task.delay(
            collection_id=pk,
            execution_id=collection_exec.id,
            user_id=user_id
        )
        
        logger.info(
            f"Collection execution task submitted: "
            f"collection_id={pk}, execution_id={collection_exec.id}, task_id={task.id}"
        )
        
        return Response({
            'message': '任务已提交，正在后台执行',
            'task_id': task.id,
            'execution_id': collection_exec.id,
            'collection_id': pk,
            'collection_name': collection.name,
            'execution_mode': collection.execution_mode,
            'total_requests': len(collection_requests),
        }, status=status.HTTP_202_ACCEPTED)

    @api_exception_handler
    @action(detail=False, methods=['get'], url_path='task-status/(?P<task_id>[^/.]+)')
    def task_status(self, request, task_id=None):
        """
        查询 Celery 任务状态
        
        Args:
            task_id: Celery 任务 ID（从 execute_async 返回）
        
        Returns:
            dict: 任务状态信息
        """
        from testmanager_app.tasks import get_task_status
        
        if not task_id:
            raise ValidationError("task_id is required")
        
        status_info = get_task_status(task_id)
        
        # 如果任务完成且有 execution_id，获取详细执行结果
        if status_info.get('ready') and status_info.get('successful'):
            result = status_info.get('result', {})
            execution_id = result.get('execution_id')
            if execution_id:
                try:
                    collection_exec = CollectionExecution.objects.get(pk=execution_id)
                    status_info['execution'] = CollectionExecutionSerializer(collection_exec).data
                except CollectionExecution.DoesNotExist:
                    pass
        
        return Response(status_info)

    @api_exception_handler
    @action(detail=True, methods=['get'], url_path='execution-status/(?P<execution_id>[0-9]+)')
    def execution_status(self, request, pk=None, execution_id=None):
        """
        查询集合执行状态（通过 execution_id）
        
        Args:
            pk: 集合 ID
            execution_id: CollectionExecution 记录 ID
        
        Returns:
            dict: 执行状态详情
        """
        try:
            collection_exec = CollectionExecution.objects.get(
                pk=execution_id,
                collection_id=pk
            )
        except CollectionExecution.DoesNotExist:
            raise ResourceNotFoundException("CollectionExecution", execution_id)
        
        return Response(CollectionExecutionSerializer(collection_exec).data)

    async def _execute_concurrent(self, collection_requests):
        """并发执行模式"""
        tasks = []
        for coll_req in collection_requests:
            try:
                task = execute_single_request_async(coll_req.api_request)
                tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to prepare request {coll_req.id}: {e}")
                tasks.append(asyncio.create_task(self._mock_error_task(e)))

        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_sequential(self, collection_requests):
        """顺序执行模式"""
        results = []
        for coll_req in collection_requests:
            try:
                result = await execute_single_request_async(coll_req.api_request)
                results.append(result)

                if coll_req.stop_on_failure and not result.get('success'):
                    logger.info(f"Request {coll_req.id} failed, stopping execution")
                    break
            except Exception as e:
                logger.error(f"Failed to execute request {coll_req.id}: {e}")
                results.append({'request_id': coll_req.api_request.id, 'error': str(e), 'success': False})

                if coll_req.stop_on_failure:
                    break
        return results

    async def _execute_chain(self, collection_requests):
        """链式执行模式（支持变量传递）"""
        from jsonpath_ng import parse as jsonpath_parse
        import json

        context = {}
        results = []

        for coll_req in collection_requests:
            try:
                # 渲染请求（替换模板变量）
                rendered_request = self._render_request_with_context(coll_req.api_request, context)

                # 执行请求
                result = await execute_single_request_async(rendered_request)
                logger.info(f"Request {coll_req.id} executed, success={result.get('success')}, error={result.get('error')}")
                results.append(result)

                # 成功处理：提取变量到上下文
                if result.get('success') and not result.get('error'):
                    if coll_req.extract_rules:
                        context = self._extract_variables(result, coll_req.extract_rules, context)
                else:
                    # 失败处理：记录日志并可能停止执行
                    logger.warning(f"Request {coll_req.id} failed in chain mode")
                    if coll_req.stop_on_failure:
                        logger.info(f"Stopping chain execution due to failure")
                        break
            except Exception as e:
                logger.error(f"Failed to execute request in chain mode {coll_req.id}: {e}")
                results.append({'request_id': coll_req.api_request.id, 'error': str(e), 'success': False})

                if coll_req.stop_on_failure:
                    break

        return results

    def _render_request_with_context(self, api_request, context):
        """渲染请求中的模板变量（使用统一模板引擎）"""
       

        from testmanager_app.utils.template_renderer import TemplateRenderer

        # 从模型实例创建数据字典
        if hasattr(api_request, 'id'):
            # 是模型实例
            return {
                'id': api_request.id,
                'method': api_request.method,
                'url': TemplateRenderer.render(api_request.url, context),
                'headers': TemplateRenderer.render(api_request.headers, context),
                'body': TemplateRenderer.render(api_request.body, context),
            }
        else:
            # 已经是字典
            return {
                'id': api_request.get('id'),
                'method': api_request.get('method'),
                'url': TemplateRenderer.render(api_request.get('url', ''), context),
                'headers': TemplateRenderer.render(api_request.get('headers', '{}'), context),
                'body': TemplateRenderer.render(api_request.get('body', ''), context),
            }

    def _extract_variables(self, result, extract_rules, context):
        """从响应中提取变量到上下文（优化异常处理）"""
        from jsonpath_ng import parse as jsonpath_parse
        from jsonpath_ng.exceptions import JsonPathParserError
        import json

        if not extract_rules or result.get('error'):
            return context

        # 精确捕获 JSONDecodeError
        try:
            response_body = result.get('response_body', '{}') or '{}'
            response_json = json.loads(response_body)
        except json.JSONDecodeError as e:
            logger.error(f"响应体JSON解析失败: {str(e)}, body: {response_body[:200]}")
            return context
        except Exception as e:
            logger.error(f"解析响应体时发生未知错误: {str(e)}")
            return context

        new_context = context.copy()

        for rule in extract_rules:
            # 验证输入（提前发现问题）
            try:
                name = rule.get('name')
                jsonpath_expr = rule.get('jsonpath')

                if not name or not jsonpath_expr:
                    logger.warning(f"提取规则缺少必要字段: name={name}, jsonpath={jsonpath_expr}")
                    continue
            except AttributeError:
                logger.error(f"提取规则格式无效（不是字典）: {rule}")
                continue
            except Exception as e:
                logger.error(f"验证提取规则时发生未知错误 {rule}: {str(e)}")
                continue

            # 精确捕获不同类型的异常
            try:
                expr = jsonpath_parse(jsonpath_expr)
                matches = [match.value for match in expr.find(response_json)]

                if matches:
                    new_context[name] = matches[0]
                    logger.info(f"提取变量成功: {name} = {matches[0]}")
                else:
                    logger.warning(f"JSONPath未找到匹配值: '{jsonpath_expr}'")

            except JsonPathParserError as e:
                logger.error(f"JSONPath语法错误 '{jsonpath_expr}': {str(e)}")
            except KeyError as e:
                logger.error(f"访问响应数据时键不存在: {str(e)}")
            except IndexError as e:
                logger.error(f"访问响应数据时索引越界: {str(e)}")
            except TypeError as e:
                logger.error(f"类型错误（可能rule不是字典）: {str(e)}, rule类型: {type(rule)}")
            except Exception as e:
                logger.error(f"提取变量时发生未知错误 {name}: {str(e)}")

        return new_context

    async def _mock_error_task(self, error):
        """创建错误任务（用于concurrent模式）"""
        return {'error': str(error), 'success': False}


class CollectionExecutionViewSet(BaseViewSet, QueryOptimizerMixin, CommonFilterMixin):
    """集合执行记录API

    继承的Mixin提供：
    - BaseViewSet: 权限控制
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理查询参数过滤

    支持的查询参数：
    - ?collection=1: 按集合ID过滤
    - ?status=success: 按状态过滤

    优化收益：
    - 移除冗余的get_queryset()方法（-20行）
    - 声明式过滤器配置
    - 自动查询优化
    """
    queryset = CollectionExecution.objects.all()
    serializer_class = CollectionExecutionSerializer

    # 查询优化配置
    select_related_fields = ['collection', 'executor']

    # 过滤器配置
    filter_int_fields = ['collection']
    filter_choice_fields = {
        'status': ['pending', 'running', 'success', 'failed', 'timeout', 'error']
    }

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CollectionExecutionCreateSerializer
        return CollectionExecutionSerializer


class FeatureTestCaseViewSet(BaseViewSet):
    """功能测试用例API（MVP）

    继承BaseViewSet提供：
    - 自动权限控制
    - 自动填充 created_by 字段
    """
    queryset = FeatureTestCase.objects.all()
    serializer_class = FeatureTestCaseSerializer



class IsAdminUser(permissions.BasePermission):
    """
    自定义权限 - 只有管理员可以访问
    
    设计理念：admin用户自动拥有管理员权限，其他用户通过角色控制
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # admin用户自动拥有管理员权限
        if request.user.username == 'admin':
            return True
        
        # 其他用户检查是否有crud权限的角色
        from testmanager_app.utils.user_utils import get_user_roles_qs
        user_roles_qs = get_user_roles_qs(request.user, use_cache=True)
        has_crud_permission = user_roles_qs.filter(permission='crud').exists()
        
        return has_crud_permission


class RoleViewSet(BaseViewSet):
    """角色管理API

    继承BaseViewSet提供：
    - 自动权限控制
    - 自动填充 created_by 字段
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

    @action(detail=False, methods=['get'], url_path='permissions')
    def get_permissions_list(self, request):
        """
        获取权限类型列表（支持缓存）
        
        权限类型是静态数据，可以长期缓存
        缓存时间：24小时
        """
        from django.core.cache import cache
        from testmanager_app.utils.cache_helper import get_cache_key
        
        cache_key = get_cache_key('permissions_list')
        
        # 尝试从缓存获取
        cached_permissions = cache.get(cache_key)
        if cached_permissions is not None:
            logger.debug("Permissions list cache hit")
            return Response(cached_permissions)
        
        permissions = [
            {'value': 'view', 'label': '仅查看'},
            {'value': 'crud', 'label': '增删改查'}
        ]
        
        # 存入缓存（24小时，静态数据）
        cache.set(cache_key, permissions, timeout=86400)
        logger.debug("Permissions list cached")
        
        return Response(permissions)


class UserRoleViewSet(BaseViewSet, QueryOptimizerMixin, CommonFilterMixin):
    """用户角色管理API

    继承的Mixin提供：
    - BaseViewSet: 权限控制
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理user参数过滤

    支持的查询参数：
    - ?user=1: 按用户ID过滤

    优化收益：
    - 移除冗余的get_queryset()方法（-7行）
    - 声明式过滤器配置
    - 自动查询优化
    """
    queryset = UserRole.objects.select_related('user', 'role').all()
    serializer_class = UserRoleSerializer

    # 查询优化配置（在queryset中已定义，这里使用Mixin的优化）
    select_related_fields = ['user', 'role']

    # 过滤器配置
    filter_int_fields = ['user']





class UserViewSet(viewsets.ModelViewSet):
    """用户管理API
    
    功能：
    - 创建用户：POST /users/ (支持 role_ids 参数分配角色)
    - 获取用户列表：GET /users/ (包含 roles 信息)
    - 更新用户：PUT/PATCH /users/{id}/ (支持 role_ids 参数更新角色)
    - 删除用户：DELETE /users/{id}/
    - 分配角色：POST /users/{id}/assign-role/
    - 移除角色：DELETE /users/{id}/remove-role/{role_id}/
    - 获取用户角色：GET /users/{id}/roles/
    
    注意：
    - superuser 自动拥有所有权限，不需要分配角色
    - 但允许为 superuser 分配角色（仅用于记录，不影响权限）
    """
    queryset = User.objects.prefetch_related('role_links__role').all()
    serializer_class = UserListSerializer
    permission_classes = [RoleBasedPermission, IsAdminUser]
    
    def get_queryset(self):
        """优化查询，预加载角色信息"""
        return User.objects.prefetch_related('role_links__role').all()
    
    @action(detail=True, methods=['get'], url_path='roles')
    def get_user_roles(self, request, pk=None):
        """获取用户的角色列表
        
        注意：superuser 返回虚拟角色信息
        """
        user = self.get_object()
        
        # superuser 自动拥有所有权限，返回虚拟角色
        if user.is_superuser:
            return Response([{
                'id': 0,
                'name': 'superuser',
                'permission': 'crud',
                'description': '超级管理员角色，拥有所有权限'
            }])
        
        # 普通用户返回实际分配的角色
        roles = UserRole.get_user_roles(user)
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='assign-role')
    def assign_role(self, request, pk=None):
        """为用户分配角色
        
        注意：superuser 可以分配角色，但不会影响其权限（superuser 自动拥有所有权限）
        """
        user = self.get_object()
        role_id = request.data.get('role_id')
        
        if not role_id:
            return Response({'error': 'role_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            role = Role.objects.get(id=role_id)
            user_role, created = UserRole.objects.get_or_create(user=user, role=role)
            
            if not created:
                return Response({'message': 'Role already assigned'}, status=status.HTTP_200_OK)
            
            serializer = UserRoleSerializer(user_role)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['delete'], url_path=r'remove-role/(?P<role_id>\d+)')
    def remove_role(self, request, pk=None, role_id=None):
        """移除用户的角色
        
        注意：superuser 可以移除角色，但不会影响其权限（superuser 自动拥有所有权限）
        """
        user = self.get_object()
        
        try:
            user_role = UserRole.objects.get(user=user, role_id=role_id)
            user_role.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except UserRole.DoesNotExist:
            return Response({'error': 'Role not found for this user'}, status=status.HTTP_404_NOT_FOUND)


class LoginView(ObtainAuthToken):
    """用户登录视图"""
    permission_classes = [permissions.AllowAny]  # 登录接口允许任何人访问

    def post(self, request, *args, **kwargs):
        """处理登录请求"""
        from django.contrib.auth import authenticate
        from testmanager_app.utils.user_utils import get_user_roles_data

        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': '用户名和密码不能为空'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if user:
            # 创建新token（支持多端点登录，每次登录都创建新token）
            # 默认7天过期
            auth_token = AuthToken.create_token(user, expires_in_days=7)

            # 获取用户的角色（使用工具函数，内部会处理superuser的情况）
            role_data = get_user_roles_data(user)

            # 构建用户信息，包含角色和权限信息
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_superuser': user.is_superuser,
                'is_staff': user.is_staff,
                'roles': role_data,  # 将角色信息直接放在user对象中，方便前端使用
                'token_expires_at': auth_token.expires_at.isoformat()  # 返回token过期时间
            }
            
            return Response({
                'token': auth_token.key,
                'user': user_data
            })
        else:
            return Response(
                {'error': '用户名或密码错误'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class RefreshTokenView(APIView):
    """刷新Token视图 - 延长token过期时间"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """刷新当前用户的token"""
        # 从请求头获取token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Token '):
            return Response(
                {'error': 'Invalid authorization header'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        token_key = auth_header.replace('Token ', '')
        
        # 刷新token
        token = AuthToken.refresh_token(token_key)
        
        if not token:
            return Response(
                {'error': 'Token not found or expired'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return Response({
            'token': token.key,
            'expires_at': token.expires_at.isoformat(),
            'message': 'Token refreshed successfully'
        })


class DebugAuthView(APIView):
    """调试验证视图 - 只返回当前认证用户信息"""
    permission_classes = []  # 临时移除权限限制，便于调试

    def get(self, request):
        """返回当前用户的信息"""
        user = request.user

        # 处理匿名用户 - 不要查询数据库
        if not user.is_authenticated:
            return Response({
                'user': {
                    'id': None,
                    'username': 'Anonymous',
                    'email': None,
                    'is_superuser': False,
                    'is_authenticated': False,
                    'is_anonymous': True,
                },
                'auth_type': 'None',
                'token': None,
                'roles': [],
                'role_count': 0,
                'has_crud': False,
                'has_view': False,
                'can_access_permission_check': False,
                'request_method': request.method,
                'debug': 'User is not authenticated - Please login first',
                'authentication_classes': [str(cls) for cls in self.authentication_classes] if hasattr(self, 'authentication_classes') else 'Not defined'
            })

        # 获取用户的角色（使用工具函数）
        from testmanager_app.utils.user_utils import get_user_roles_qs, check_user_permissions

        roles_qs = get_user_roles_qs(user)
        role_data = RoleSerializer(roles_qs, many=True).data
        permissions = check_user_permissions(user, request.method)

        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_superuser': user.is_superuser,
                'is_authenticated': user.is_authenticated,
                'is_anonymous': user.is_anonymous,
            },
            'auth_type': str(request.auth) if request.auth else 'None',
            'token': getattr(request.auth, 'key', None) if request.auth else None,
            'roles': role_data,
            'role_count': permissions['role_count'],
            'has_crud': permissions['has_crud'],
            'has_view': permissions['has_view'],
            'can_access_permission_check': permissions['can_access'],
            'request_method': request.method,
            'debug': 'This endpoint temporarily has no permission restrictions for debugging'
        })


class MeView(APIView):
    """获取当前登录用户信息"""
    permission_classes = [RoleBasedPermission]

    def get(self, request):
        """返回当前用户的详细信息"""
        user = request.user

        # 获取用户的角色（使用工具函数）
        from testmanager_app.utils.user_utils import get_user_roles_data

        role_data = get_user_roles_data(user)

        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_superuser': user.is_superuser,
            'roles': role_data
        })


async def execute_api_request_async(request, api_request_id):
    """
    Django 原生异步视图 - 执行单个 API 请求并验证断言

    参数:
        request: Django 请求对象
        api_request_id: API 请求 ID

    返回:
        JsonResponse: 包含执行结果的 JSON 响应
    """
    # 权限检查 - 使用 sync_to_async 包装同步权限检查
    from asgiref.sync import sync_to_async

    permission = RoleBasedPermission()
    has_perm = await sync_to_async(permission.has_permission, thread_sensitive=True)(request, None)

    if not has_perm:
        return JsonResponse({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    # 获取 API 请求对象及其所有字段数据（避免在异步函数中访问模型字段）
    try:
        get_api_request = sync_to_async(lambda: ApiRequest.objects.get(pk=api_request_id), thread_sensitive=True)
        api_request = await get_api_request()

        if not api_request:
            return JsonResponse({'error': 'API request not found'}, status=status.HTTP_404_NOT_FOUND)

        # 创建数据字典
        api_request_data = {
            'id': api_request.id,
            'method': api_request.method,
            'url': api_request.url,
            'headers': api_request.headers,
            'body': api_request.body,
        }
    except ApiRequest.DoesNotExist:
        return JsonResponse({'error': 'API request not found'}, status=status.HTTP_404_NOT_FOUND)

    # 执行请求（使用纯异步函数）
    # 传入模型实例以支持断言验证
    result = await execute_single_request_async(api_request)

    return JsonResponse(result)


# ==================== YAML配置工具API ====================

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from testmanager_app.services.yaml_converter import YamlToCollectionConverter


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def yaml_to_collection(request, project_id):
    """
    将YAML配置转换为RequestCollection

    POST /api/v1/projects/{project_id}/yaml-to-collection

    Request Body:
        {
            "name": "测试集合名称",
            "description": "描述信息",
            "yaml_content": "Base64编码的YAML内容",
            "execution_mode": "chain|sequential|concurrent",
            "validate_only": false
        }

    Response:
        {
            "code": 201,
            "message": "转换成功",
            "data": {
                "collection_id": 123,
                "name": "测试集合名称",
                "preview": { ... },
                "created_at": "2025-12-12T10:30:00Z"
            }
        }
    """
    try:
        data = request.data
        name = data.get('name')
        description = data.get('description', '')
        base64_content = data.get('yaml_content')
        execution_mode = data.get('execution_mode', 'chain')
        validate_only = data.get('validate_only', False)

        if not name:
            return Response({'code': 400, 'message': 'name参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        if not base64_content:
            return Response({'code': 400, 'message': 'yaml_content参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        converter = YamlToCollectionConverter(
            project_id=project_id,
            created_by_id=request.user.id
        )

        success, result = converter.convert_from_base64(
            base64_content=base64_content,
            name=name,
            description=description,
            execution_mode=execution_mode,
            validate_only=validate_only
        )

        if success:
            status_code = status.HTTP_200_OK if validate_only else status.HTTP_201_CREATED
            return Response({
                'code': status_code,
                'message': '验证成功' if validate_only else '转换成功',
                'data': result
            }, status=status_code)
        else:
            # 转换失败，返回错误详情
            if 'errors' in result:
                return Response({
                    'code': 422,
                    'message': 'YAML验证失败',
                    'errors': result['errors'],
                    'warnings': result.get('warnings', [])
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            else:
                return Response({
                    'code': 500,
                    'message': f"转换失败: {result.get('error', '未知错误')}",
                    'detail': result.get('detail', '')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"yaml_to_collection error: {str(e)}", exc_info=True)
        return Response({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_yaml_config(request, project_id):
    """
    仅验证YAML配置，不保存到数据库

    POST /api/v1/projects/{project_id}/yaml/validate

    Request Body:
        {
            "yaml_content": "Base64编码的YAML内容",
            "check_variables": true,
            "check_jsonpath": true
        }

    Response:
        {
            "code": 200,
            "message": "验证通过",
            "data": {
                "valid": true,
                "stats": { ... },
                "issues": [ ... ]
            }
        }
    """
    try:
        data = request.data
        base64_content = data.get('yaml_content')
        check_variables = data.get('check_variables', True)
        check_jsonpath = data.get('check_jsonpath', True)

        if not base64_content:
            return Response({'code': 400, 'message': 'yaml_content参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 解码
        import base64
        try:
            yaml_content = base64.b64decode(base64_content.encode('utf-8')).decode('utf-8')
        except Exception as e:
            return Response({
                'code': 400,
                'message': f'Base64解码失败: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        converter = YamlToCollectionConverter(
            project_id=project_id,
            created_by_id=request.user.id
        )

        # 验证
        is_valid, errors, warnings, preview = converter.validate_only(yaml_content)

        if is_valid:
            return Response({
                'code': 200,
                'message': '验证通过',
                'data': {
                    'valid': True,
                    'stats': {
                        'total_steps': len(preview['steps_preview']),
                        'defined_variables': len(preview['variables']['defined']),
                        'undefined_variables': len(preview['variables']['undefined'])
                    },
                    'issues': warnings
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'code': 422,
                'message': '验证失败',
                'data': {
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings
                }
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    except Exception as e:
        logger.error(f"validate_yaml_config error: {str(e)}", exc_info=True)
        return Response({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
