"""
UI测试应用的视图
"""
from __future__ import annotations
from typing import Any
from rest_framework.request import Request
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import QuerySet
from django.utils import timezone
from .models import (
    UITestScript,
    UITestExecution,
)
from .serializers import (
    UITestScriptSerializer, UITestScriptCreateSerializer,
    UITestExecutionSerializer,
    ScriptRecordingSerializer,
)
from .services import UITestService, ScriptBuilder
from .recording.session_manager import RecordingSessionManager
from .validators.script_validator import ScriptValidator, ValidationError
import logging

logger = logging.getLogger(__name__)

# Windows上：不要设置 SelectorEventLoopPolicy
# Playwright 需要 ProactorEventLoopPolicy（默认）来创建子进程
# SelectorEventLoopPolicy 不支持子进程，会导致 NotImplementedError
# if sys.platform == 'win32':
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class UITestScriptViewSet(viewsets.ModelViewSet):
    """UI测试脚本视图集"""
    permission_classes = [IsAuthenticated]
    queryset = UITestScript.objects.all()
    
    def get_serializer_class(self) -> type[UITestScriptSerializer | UITestScriptCreateSerializer]:
        if self.action == 'create':
            return UITestScriptCreateSerializer
        return UITestScriptSerializer
    
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        创建测试脚本
        
        流程：
        1. 验证输入数据
        2. 创建脚本对象（Serializer处理）
        3. 校验actions（是否完整/合法）
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # 调用Serializer的create方法创建脚本
            script = serializer.save()
            
            # 创建后校验actions
            from .validators.script_validator import ScriptValidator, ValidationError
            
            validator = ScriptValidator()
            actions = script.actions or []
            
            if actions:
                is_valid, error_msg = validator.validate(
                    actions=actions,
                    browser_type=script.browser_type,
                    viewport_width=script.viewport_width,
                    viewport_height=script.viewport_height,
                    timeout=script.timeout
                )
                
                if not is_valid:
                    # 校验失败，删除已创建的脚本
                    script.delete()
                    logger.warning(f"创建脚本校验失败: {error_msg}")
                    return Response(
                        {'error': f'脚本校验失败: {error_msg}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                logger.info(f"创建脚本校验通过: script_id={script.id}, actions数量={len(actions)}")
            
            # 返回创建的脚本
            headers = self.get_success_headers(serializer.data)
            result_serializer = UITestScriptSerializer(script)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except ValidationError as e:
            logger.error(f"创建脚本校验异常: {str(e)}")
            return Response(
                {'error': f'脚本校验失败: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"创建脚本失败: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_queryset(self) -> QuerySet[UITestScript]:
        queryset = super().get_queryset()
        # 可以根据项目过滤
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset.select_related('project', 'created_by')
    
    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        更新测试脚本
        
        确保更新时不会意外清空actions字段：
        - 如果请求中没有传递actions字段，保留原有的actions
        - 如果请求中传递了actions字段，使用新的值
        """
        script = self.get_object()
        
        # 如果请求数据中没有actions字段，保留原有的actions
        if 'actions' not in request.data:
            # 处理QueryDict和dict两种情况
            if hasattr(request.data, '_mutable'):
                request.data._mutable = True
                request.data['actions'] = script.actions or []
                request.data._mutable = False
            else:
                request.data['actions'] = script.actions or []
        
        # 如果请求数据中没有project字段，保留原有的project
        if 'project' not in request.data:
            if hasattr(request.data, '_mutable'):
                request.data._mutable = True
                request.data['project'] = script.project_id
                request.data._mutable = False
            else:
                request.data['project'] = script.project_id
        
        # 调用父类的update方法
        return super().update(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def execute(self, request: Request, pk: int | None = None) -> Response:
        """
        执行测试脚本（异步执行）
        
        流程：
        1. 先创建执行记录（status=pending），立即返回 execution_id
        2. 提交 Celery 任务（非阻塞），任务内部更新执行记录
        3. 前端可以用 execution_id 轮询查询执行状态
        """
        from django.utils import timezone
        from core.services.chatbot_execution_logger import get_chatbot_logger
        
        script = self.get_object()
        
        logger.info(f"[Execute] 开始执行脚本 ID={script.id}, 名称={script.name}")
        
        conversation_id = request.data.get('conversation_id', 'manual-ui-test')
        logger_exec = get_chatbot_logger(conversation_id)
        logger_exec.start('ui_test', f'执行UI测试: {script.name}', f'正在执行 UI 测试脚本: {script.name}')
        
        try:
            # 检查actions是否存在（快速检查，避免提交无效任务）
            if not script.actions:
                logger.warning(f"[Execute] 脚本actions列表为空 ID={script.id}")
                return Response(
                    {'error': '脚本actions列表为空，无法执行。请先编辑脚本添加actions。'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 1. 先创建执行记录（status=pending），让前端可以立即获取 execution_id
            # started_at 不在此处设置，而是在实际执行开始时设置（在 Celery 任务中）
            execution = UITestExecution.objects.create(  # type: ignore[misc]
                script=script,
                executed_by=request.user,
                status='pending'
            )
            logger.info(f"[Execute] 执行记录创建成功 ID={execution.id}")
            
            # 2. 提交 Celery 任务，传递已创建的 execution_id
            service = UITestService()
            result = service.execute_script_with_execution(
                script_id=script.id,
                execution_id=execution.id,
                user_id=request.user.id
            )
            
            if result.get('success'):
                logger_exec.finish({
                    'status': 'pending',
                    'script_id': script.id,
                    'execution_id': execution.id
                })
                # 返回执行记录ID，前端可以轮询查询状态
                return Response({
                    'success': True,
                    'execution_id': execution.id,
                    'task_id': result.get('task_id'),
                    'message': '任务已提交，正在执行中',
                    'script_id': script.id,
                    'script_name': script.name,
                    'status': 'pending',
                    'execution_log_ids': logger_exec.get_log_ids()
                }, status=status.HTTP_202_ACCEPTED)
            else:
                # 任务提交失败，更新执行记录状态
                error_msg = result.get('error', '提交任务失败')
                execution.status = 'failed'
                execution.error_message = error_msg
                execution.completed_at = timezone.now()
                execution.save()
                
                logger_exec.finish({
                    'status': 'error',
                    'error': error_msg,
                    'script_id': script.id
                })
                
                logger.error(f"[Execute] 提交任务失败 ID={script.id}, 错误={error_msg}")
                return Response({
                    'success': False,
                    'execution_id': execution.id,
                    'error': error_msg,
                    'status': 'failed',
                    'execution_log_ids': logger_exec.get_log_ids()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger_exec.finish({
                'status': 'error',
                'error': str(e)
            })
            logger.error(f"[Execute] 执行脚本异常 ID={script.id}, 错误={str(e)}", exc_info=True)
            return Response(
                {'error': str(e), 'execution_log_ids': logger_exec.get_log_ids()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def get_execution_status(self, request: Request) -> Response:
        """查询执行状态"""
        execution_id = request.query_params.get('execution_id')
        if not execution_id:
            return Response(
                {'error': 'execution_id参数缺失'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            execution = UITestExecution.objects.get(id=execution_id)
            serializer = UITestExecutionSerializer(execution)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UITestExecution.DoesNotExist:
            return Response(
                {'error': f'执行记录不存在: {execution_id}'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"查询执行状态失败: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def record(self, request: Request) -> Response:
        """
        保存录制的脚本
        
        流程：
        1. 转换steps为actions
        2. 校验actions（是否完整/合法）
        3. 创建脚本对象
        """
        serializer = ScriptRecordingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                script = ScriptBuilder.create_script_from_steps(
                    name=serializer.validated_data['name'],
                    steps_data=serializer.validated_data['steps'],
                    project_id=serializer.validated_data.get('project_id'),
                    user_id=request.user.id,
                    description=serializer.validated_data.get('description', ''),
                )
                
                validator = ScriptValidator()
                actions = script.actions or []
                
                if actions:
                    is_valid, error_msg = validator.validate(
                        actions=actions,
                        browser_type=script.browser_type,
                        viewport_width=script.viewport_width,
                        viewport_height=script.viewport_height,
                        timeout=script.timeout
                    )
                    
                    if not is_valid:
                        # 校验失败，删除已创建的脚本
                        script.delete()
                        logger.warning(f"录制脚本校验失败: {error_msg}")
                        return Response(
                            {'error': f'脚本校验失败: {error_msg}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    logger.info(f"录制脚本校验通过: script_id={script.pk}, actions数量={len(actions)}")
                
                result_serializer = UITestScriptSerializer(script)
                return Response(result_serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                logger.error(f"录制脚本校验异常: {str(e)}")
                return Response(
                    {'error': f'脚本校验失败: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.error(f"保存录制脚本失败: {str(e)}")
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def sync_record(self, request: Request) -> Response:
        """
        开始同步录制，阻塞直到浏览器关闭并直接返回结果。

        注意：本接口只负责"采集步骤"，不直接保存脚本。
        录制完成后，前端应调用 quality_check 接口进行质量检查，
        用户确认无问题后，再调用 record/save 接口落库。
        """
        data = request.data
        start_url = data.get('start_url', 'https://www.baidu.com')
        browser_type = data.get('browser_type', 'chromium')
        
        logger.info(f"[SyncRecord] 开始同步录制: url={start_url}")
        
        from .recording.sync_recorder import SyncBrowserRecorder
        recorder = SyncBrowserRecorder()
        
        try:
            # 该方法会阻塞，直到浏览器关闭
            steps = recorder.start_recording(start_url, browser_type)
            
            return Response({
                'success': True,
                'steps': steps,
                'message': f'录制完成，共 {len(steps)} 个步骤'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"[SyncRecord] 录制异常: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def quality_check(self, request: Request) -> Response:
        """
        录制完成后的脚本质量检查（非实时）。

        使用场景：
        1. 前端调用 sync_record 或 RecordingSessionManager 获取 steps/actions；
        2. 将 steps/actions 通过本接口发送到后端；
        3. 后端调用 ScriptValidator.check_script_quality 进行统一质量检查；
        4. 返回逐步骤的错误/告警及友好建议，由用户确认是否保存为正式脚本。

        请求体示例:
        {
            "actions": [...],                # 必填，录制得到的 actions/steps 数组
            "browser_type": "chromium",      # 可选
            "viewport_width": 1280,          # 可选
            "viewport_height": 720,          # 可选
            "timeout": 30000                 # 可选
        }
        """
        data = request.data
        actions = data.get('actions')
        if not isinstance(actions, list) or len(actions) == 0:
            return Response(
                {'error': 'actions 不能为空，并且必须为数组'},
                status=status.HTTP_400_BAD_REQUEST
            )

        browser_type = data.get('browser_type', 'chromium')
        viewport_width = int(data.get('viewport_width', 1280))
        viewport_height = int(data.get('viewport_height', 720))
        timeout = int(data.get('timeout', 30000))

        try:
            validator = ScriptValidator()
            quality_result = validator.check_script_quality(
                actions=actions,
                browser_type=browser_type,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                timeout=timeout
            )

            return Response(
                {
                    'success': True,
                    'quality': quality_result
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"[QualityCheck] 脚本质量检查异常: {str(e)}", exc_info=True)
            return Response(
                {'error': f'脚本质量检查失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def get_recording_steps(self, request: Request) -> Response:
        """获取录制步骤（通过session_id）"""
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(
                {'error': 'session_id参数缺失'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            steps = RecordingSessionManager.get_steps(session_id)
            return Response({
                'success': True,
                'steps': steps
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"获取录制步骤失败: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
class UITestExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """UI测试执行记录视图集（只读）"""
    permission_classes = [IsAuthenticated]
    queryset = UITestExecution.objects.all()
    serializer_class = UITestExecutionSerializer
    
    def get_queryset(self) -> QuerySet[UITestExecution]:
        queryset = super().get_queryset()
        script_id = self.request.query_params.get('script_id')
        if script_id:
            queryset = queryset.filter(script_id=script_id)
        return queryset.select_related('script', 'executed_by').order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    def logs(self, request: Request, pk: int | None = None) -> Response:
        """
        获取UI测试执行日志详情（支持缓存）
        
        返回详细的执行日志，包括：
        - execution_log（按行分割）
        - execution_duration_ms（执行耗时，毫秒）
        - screenshots（截图列表）
        - result_summary（统计信息）
        """
        from django.core.cache import cache
        from testmanager_app.utils.cache_helper import get_cache_key
        
        execution = self.get_object()
        
        # 生成缓存键（基于执行记录ID和更新时间）
        updated_at_str = str(execution.completed_at) if execution.completed_at else str(execution.created_at)
        cache_key = get_cache_key('ui_execution_logs', execution.id, updated_at=updated_at_str)
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            # Removed verbose debug logging
            return Response(cached_data)
        
        # 计算执行耗时（毫秒）
        execution_duration_ms = None
        if execution.duration:
            execution_duration_ms = execution.duration * 1000
        
        # 将execution_log按行分割
        logs = []
        if execution.execution_log:
            logs = execution.execution_log.split('\n')
        
        data = {
            'execution_id': execution.id,
            'status': execution.status,
            'logs': logs,
            'execution_duration_ms': execution_duration_ms,
            'screenshots': execution.screenshots or [],
            'result_summary': execution.result_summary or {}
        }
        
        # 存入缓存（1小时，执行记录不会变化）
        cache.set(cache_key, data, timeout=3600)
        # Removed verbose debug logging
        
        return Response(data)


class ExtractElementsView(APIView):
    """
    提取页面元素API

    使用Playwright渲染页面并提取交互元素
    """
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        """
        提取页面元素

        请求参数:
        - url: 页面URL (必填)
        - browser_type: 浏览器类型 (可选, 默认chromium)
        - wait_for_network: 是否等待网络空闲 (可选, 默认True)
        - wait_selector: 等待特定选择器 (可选)
        - wait_timeout: 等待超时毫秒 (可选, 默认5000)
        """
        data = request.data
        url = data.get('url')
        if not url:
            return Response(
                {'error': 'url参数缺失'},
                status=status.HTTP_400_BAD_REQUEST
            )

        browser_type = data.get('browser_type', 'chromium')
        wait_for_network_raw = data.get('wait_for_network', True)
        wait_for_network = bool(wait_for_network_raw)
        wait_selector = data.get('wait_selector')
        wait_timeout_raw = data.get('wait_timeout', 5000)
        wait_timeout = int(wait_timeout_raw) if wait_timeout_raw is not None else 5000

        try:
            from .services import ElementExtractor
            extractor = ElementExtractor()
            result = extractor.extract_page_elements(
                url=url,
                wait_for_network=wait_for_network,
                wait_selector=wait_selector,
                wait_timeout=wait_timeout,
                headless=True,
                browser_type=browser_type
            )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"提取页面元素失败: {str(e)}")
            return Response(
                {'error': f'提取页面元素失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
