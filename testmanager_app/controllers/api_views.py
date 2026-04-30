"""
API测试相关视图
包含：ApiRequestViewSet, ApiAssertionViewSet, RequestCollectionViewSet, CollectionExecutionViewSet
"""
# pyright: reportAttributeAccessIssue=false

from typing import Any
import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Project, TestExecution
from testmanager_app.models import (
    ApiRequest, ApiAssertion, RequestCollection, CollectionExecution,
    PressureTestConfig, PressureTestExecution
)
from testmanager_app.serializers import (
    ApiRequestSerializer, ApiRequestCreateSerializer,
    ApiAssertionSerializer, ApiAssertionCreateSerializer,
    RequestCollectionSerializer, RequestCollectionCreateSerializer,
    CollectionExecutionSerializer, CollectionExecutionCreateSerializer,
    PressureTestConfigSerializer, PressureTestConfigCreateSerializer,
    PressureTestExecutionSerializer, PressureTestExecutionCreateSerializer,
    PressureTestExecuteResponseSerializer
)
from testmanager_app.viewsets import BaseViewSet, QueryOptimizerMixin, CommonFilterMixin, CacheMixin
from testmanager_app.utils.api_exceptions import api_exception_handler
from testmanager_app.services import TestExecutionService
from testmanager_app.tasks import execute_collection_task

logger = logging.getLogger(__name__)


class ApiRequestViewSet(CacheMixin, QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
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
    """
    queryset = ApiRequest.objects.all()
    serializer_class = ApiRequestSerializer

    # 查询优化配置
    select_related_fields = ['project', 'created_by']
    prefetch_related_fields = ['assertions']

    # 过滤器配置
    filter_int_fields = ['project']

    # 缓存配置
    cache_timeout = 120  # 2分钟
    cache_detail_timeout = 300  # 5分钟

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ApiRequestCreateSerializer
        return ApiRequestSerializer

    @api_exception_handler
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        执行单个API请求（同步版本）

        简化点：
        - 直接同步执行，无异步复杂性
        - 即时返回结果，消除事件循环冲突
        """
        from core.services.chatbot_execution_logger import get_chatbot_logger
        
        api_request = self.get_object()
        conversation_id = request.data.get('conversation_id', 'manual-api-test')
        
        logger = get_chatbot_logger(conversation_id)
        logger.start('api_test', f'执行API测试: {api_request.name}', f'正在执行 API: {api_request.method} {api_request.url}')
        
        result = TestExecutionService.execute_single_api_request(api_request, request.user)
        
        logger.finish({
            'status': 'success' if result.get('success') else 'error',
            'api_request_id': api_request.id,
            'execution_id': result.get('execution_id'),
            'response_status': result.get('response_status'),
            'duration': result.get('duration')
        })
        
        return Response({
            **result,
            'execution_log_ids': logger.get_log_ids()
        })

    @api_exception_handler
    @action(detail=True, methods=['post'], url_path='execute-async')
    def execute_async(self, request, pk=None):
        """
        执行单个API请求（异步版本 - Celery）

        使用 Celery 任务异步执行，适合耗时较长的请求
        """
        from testmanager_app.tasks import execute_api_request_task
        
        api_request = self.get_object()
        task = execute_api_request_task.delay(api_request.id, request.user.id)
        return Response({'task_id': task.id, 'status': 'pending'}, status=status.HTTP_202_ACCEPTED)

    @api_exception_handler
    @action(detail=False, methods=['post'], url_path='execute-batch')
    def execute_batch(self, request):
        """
        批量执行API请求（简化同步版本）

        简化点：
        - 移除复杂的异步逻辑，使用同步执行
        - 批量查询优化，避免 N+1 问题
        - 逐一执行每个API请求，避免事件循环冲突
        - 保持结果返回格式一致
        """
        from core.services.chatbot_execution_logger import get_chatbot_logger
        
        request_ids = request.data.get('request_ids', [])
        if not request_ids:
            return Response({'error': 'request_ids is required'}, status=status.HTTP_400_BAD_REQUEST)

        if len(request_ids) > 20:
            return Response({'error': '批量执行最多支持20个请求'}, status=status.HTTP_400_BAD_REQUEST)
        
        conversation_id = request.data.get('conversation_id', 'manual-api-batch')
        logger = get_chatbot_logger(conversation_id)
        logger.start('api_test', f'批量执行API测试', f'正在批量执行 {len(request_ids)} 个API请求')

        api_requests = ApiRequest.objects.filter(id__in=request_ids).select_related('project', 'created_by').prefetch_related('assertions')
        request_map = {req.id: req for req in api_requests}

        results = []
        success_count = 0
        for request_id in request_ids:
            api_request = request_map.get(request_id)
            if api_request:
                result = TestExecutionService.execute_single_api_request(api_request, request.user)
                results.append(result)
                if result.get('success'):
                    success_count += 1
            else:
                logger.log(f"API请求不存在: {request_id}")
                results.append({
                    'error': f'API请求不存在: {request_id}',
                    'request_id': request_id
                })
        
        logger.finish({
            'status': 'success',
            'total': len(request_ids),
            'success': success_count,
            'failed': len(request_ids) - success_count
        })
        
        return Response({
            'results': results,
            'execution_log_ids': logger.get_log_ids()
        }, status=status.HTTP_200_OK)

    @api_exception_handler
    @action(detail=False, methods=['post'], url_path='execute-chain')
    def execute_chain(self, request):
        """
        链式执行API请求（支持变量传递）
        
        按项目的 ApiRequest 的 order_index 顺序执行：
        1. 执行请求
        2. 提取变量（根据 extract_rules）
        3. 将变量注入后续请求（使用 {{variable}} 模板语法）
        4. 支持失败停止
        
        请求体：
        {
            "project": 1,  // 项目ID（必填）
            "stop_on_failure": true  // 可选，默认 true
        }
        """
        from django.utils import timezone
        from core.models import TestExecution
        from testmanager_app.utils.sync_http_utils import execute_request_direct
        from testmanager_app.services.template_renderer import TemplateRenderer
        from jsonpath_ng import parse as jsonpath_parse
        import json
        
        project_id = request.data.get('project')
        if not project_id:
            return Response({'error': 'project is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)
        
        stop_on_failure = request.data.get('stop_on_failure', True)
        
        # 获取项目中已启用的请求，按 order_index 排序
        api_requests = ApiRequest.objects.filter(
            project=project,
            is_enabled=True
        ).select_related('project', 'created_by').prefetch_related('assertions').order_by('order_index')
        
        if not api_requests:
            return Response({'error': 'No enabled API requests found in this project'}, status=status.HTTP_400_BAD_REQUEST)
        
        context: dict[str, Any] = {}  # 变量上下文
        results = []
        request_renderer = TemplateRenderer()
        
        logger.info(f"[Chain Execution] Starting chain execution for project {project.name}, {api_requests.count()} requests")
        
        for api_request in api_requests:
            try:
                # 使用模板渲染器替换变量
                rendered_data = request_renderer.render(api_request, context)
                
                # 构造请求数据
                request_data = {
                    'id': api_request.id,
                    'method': rendered_data.get('method', api_request.method),
                    'url': rendered_data.get('url', api_request.url),
                    'headers': rendered_data.get('headers', api_request.headers),
                    'body': rendered_data.get('body', api_request.body),
                    'timeout': getattr(api_request, 'timeout', 30) or 30,
                }
                
                logger.info(f"[Chain Execution] Executing request {api_request.order_index}: {request_data['method']} {request_data['url']}")
                
                # 执行请求
                result = execute_request_direct(request_data)
                result['api_request_id'] = api_request.id
                result['api_request_name'] = api_request.name
                
                # 提取变量
                extracted_vars = {}
                if api_request.extract_rules and result.get('response_body'):
                    try:
                        response_body = result['response_body']
                        if isinstance(response_body, str):
                            response_json = json.loads(response_body)
                        else:
                            response_json = response_body
                        
                        for rule in api_request.extract_rules:
                            name = rule.get('name')
                            jsonpath_expr = rule.get('jsonpath')
                            if name and jsonpath_expr:
                                expr = jsonpath_parse(jsonpath_expr)
                                matches = [m.value for m in expr.find(response_json)]
                                if matches:
                                    extracted_vars[name] = matches[0]
                                    context[name] = matches[0]
                                    logger.info(f"[Chain Execution] Extracted variable: {name} = {matches[0]}")
                    except Exception as e:
                        logger.warning(f"[Chain Execution] Variable extraction failed: {e}")
                
                result['extracted_vars'] = extracted_vars
                results.append(result)
                
                # 失败停止
                if stop_on_failure and not result.get('success', False):
                    logger.warning(f"[Chain Execution] Request {api_request.name} failed, stopping chain execution")
                    break
                    
            except Exception as e:
                logger.error(f"[Chain Execution] Request {api_request.name} error: {e}")
                results.append({
                    'api_request_id': api_request.id,
                    'api_request_name': api_request.name,
                    'success': False,
                    'error': str(e)
                })
                if stop_on_failure:
                    break
        
        # 统计
        passed = sum(1 for r in results if r.get('success', False))
        failed = len(results) - passed
        
        return Response({
            'results': results,
            'summary': {
                'total': len(results),
                'passed': passed,
                'failed': failed
            }
        }, status=status.HTTP_200_OK)


class ApiAssertionViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """API断言管理API"""
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


class RequestCollectionViewSet(CacheMixin, QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """
    请求集合管理API
    
    DEPRECATED: 2026-04-15
    请使用 PressureTestConfigViewSet 替代
    保留原因：兼容现有代码，观察期后删除
    """
    queryset = RequestCollection.objects.all()
    serializer_class = RequestCollectionSerializer

    # 查询优化配置
    select_related_fields = ['project', 'created_by']
    prefetch_related_fields = ['requests']

    # 过滤器配置
    filter_int_fields = ['project']

    # 缓存配置
    cache_timeout = 120  # 2分钟
    cache_detail_timeout = 300  # 5分钟

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RequestCollectionCreateSerializer
        return RequestCollectionSerializer

    @api_exception_handler
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        执行请求集合（后台任务版本）
        
        DEPRECATED: 2026-04-15
        请使用 PressureTestConfigViewSet.execute() 替代
        保留原因：兼容现有代码，观察期后删除
        
        改进点：
        - 使用 Celery 后台任务执行，避免 HTTP 请求超时
        - 立即返回 execution_id 和 task_id
        - 用户可通过 task_id 查询执行进度
        """
        import warnings
        warnings.warn(
            "RequestCollection.execute() is deprecated. "
            "Use PressureTestConfig.execute() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        collection = self.get_object()
        
        execution = CollectionExecution.objects.create(
            collection=collection,
            executor=request.user if request.user.is_authenticated else None,
            status='pending'
        )
        
        user_id = request.user.id if request.user.is_authenticated else None
        task = execute_collection_task.delay(collection.id, execution.id, user_id)
        
        return Response({
            'execution_id': execution.id,
            'task_id': task.id,
            'status': 'pending',
            'message': f'请求集合已提交后台执行，共包含请求待执行'
        }, status=status.HTTP_202_ACCEPTED)


class CollectionExecutionViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """
    集合执行记录API
    
    DEPRECATED: 2026-04-15
    请使用 PressureTestExecutionViewSet 替代
    保留原因：兼容现有代码，观察期后删除
    """
    queryset = CollectionExecution.objects.all()
    serializer_class = CollectionExecutionSerializer

    # 查询优化配置
    select_related_fields = ['collection', 'executor']

    # 过滤器配置
    filter_int_fields = ['collection']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CollectionExecutionCreateSerializer
        return CollectionExecutionSerializer


# ============================================================================
# 压测配置和执行 ViewSet (Pressure Test)
# ============================================================================

class PressureTestConfigViewSet(CacheMixin, QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """压测配置管理API"""
    queryset = PressureTestConfig.objects.all()
    serializer_class = PressureTestConfigSerializer
    
    # 查询优化
    select_related_fields = ['project', 'api_request', 'created_by']
    
    # 过滤器配置
    filter_int_fields = ['project', 'api_request']
    
    # 缓存配置
    cache_timeout = 120  # 2分钟
    cache_detail_timeout = 300  # 5分钟
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PressureTestConfigCreateSerializer
        return PressureTestConfigSerializer
    
    @api_exception_handler
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        开始压测
        返回 WebSocket 连接 URL
        """
        config = self.get_object()
        logger.info(f"[PressureTest] Execute called - config_id={config.id}, config_name={config.name}, "
                    f"mode={config.pressure_mode}, user={request.user if request.user.is_authenticated else 'anonymous'}")
        
        execution = PressureTestExecution.objects.create(
            config=config,
            executor=request.user if request.user.is_authenticated else None,
            status='pending'
        )
        logger.info(f"[PressureTest] Created execution record - execution_id={execution.id}, status=pending")
        
        websocket_url = f"/ws/pressure-test/{execution.id}/"
        logger.info(f"[PressureTest] WebSocket URL: {websocket_url}")
        
        serializer = PressureTestExecuteResponseSerializer({
            'execution_id': execution.id,
            'websocket_url': websocket_url,
            'message': '请连接WebSocket并开始压测'
        })
        
        logger.info(f"[PressureTest] Execute response - execution_id={execution.id}, ws_url={websocket_url}")
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
    
    @api_exception_handler
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """获取压测历史记录"""
        config = self.get_object()
        executions = config.executions.order_by('-started_at')[:10]
        serializer = PressureTestExecutionSerializer(executions, many=True)
        return Response(serializer.data)


class PressureTestExecutionViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """压测执行记录API"""
    queryset = PressureTestExecution.objects.all()
    serializer_class = PressureTestExecutionSerializer
    
    # 查询优化
    select_related_fields = ['config', 'executor']
    
    # 过滤器配置
    filter_int_fields = ['config']
    filter_choice_fields = {
        'status': ['pending', 'running', 'completed', 'stopped', 'failed']
    }
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PressureTestExecutionCreateSerializer
        return PressureTestExecutionSerializer
    
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