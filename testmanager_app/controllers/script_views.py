"""
脚本相关视图
包含：TestScriptViewSet, ScriptExecutionViewSet (deprecated)
"""

import logging
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models.test_management import TestExecution
from testmanager_app.models import TestScript, ScriptExecution
from testmanager_app.serializers import (
    TestScriptSerializer, TestScriptCreateSerializer,
    ScriptExecutionSerializer, ScriptExecutionCreateSerializer
)
from testmanager_app.viewsets import BaseViewSet, QueryOptimizerMixin, CommonFilterMixin, CacheMixin
from testmanager_app.utils.api_exceptions import api_exception_handler
from testmanager_app.services.execution_engine.script_engine import TestChainExecutor as ScriptEngine

logger = logging.getLogger(__name__)


class TestScriptViewSet(CacheMixin, QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """测试脚本管理API

    继承的Mixin提供：
    - CacheMixin: 列表和详情查询缓存支持
    - BaseViewSet: 权限控制和created_by自动填充
    - QueryOptimizerMixin: 自动select_related优化
    - CommonFilterMixin: 自动处理project参数过滤

    支持的查询参数：
    - ?project=1: 按项目ID过滤

    特殊功能：
    - execute action: 执行测试脚本（支持api/json/yaml类型）
    
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

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TestScriptCreateSerializer
        return TestScriptSerializer

    @api_exception_handler
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        执行测试脚本（支持api/json/yaml类型）

        使用统一的 TestExecution 模型记录执行结果（test_type='script'）
        """
        script = self.get_object()
        
        # 创建 TestExecution 记录（替代 ScriptExecution）
        execution = TestExecution.objects.create(
            test_type='script',
            test_script=script,
            executed_by=request.user if request.user.is_authenticated else None,
            status='pending'
        )
        
        try:
            # 根据脚本类型执行
            if script.script_type == 'api':
                result = self._execute_api_script(script)
            elif script.script_type == 'json':
                result = self._execute_json_script(script)
            elif script.script_type == 'yaml':
                result = self._execute_yaml_script(script)
            else:
                raise ValueError(f"不支持的脚本类型: {script.script_type}")
            
            # 更新执行记录
            test_passed = result.get('success', False)
            execution.status = 'passed' if test_passed else 'failed'
            execution.api_logs = '\n'.join(result.get('logs', []))
            execution.error_message = result.get('error', '')

            # 构建步骤执行摘要
            results_list = result.get('results', [])
            total_steps = len(results_list)
            passed_steps = sum(1 for r in results_list if r.get('success'))
            failed_steps = total_steps - passed_steps

            execution.step_results = {
                'total': total_steps,
                'passed': passed_steps,
                'failed': failed_steps,
                'details': results_list,
            }
            execution.save()

            # 响应中包含 summary 和 execution_id
            result['summary'] = {
                'total_steps': total_steps,
                'passed': passed_steps,
                'failed': failed_steps,
                'execution_id': execution.id,
                'execution_status': execution.status,
            }
            result['execution_id'] = execution.id

            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"执行脚本失败: {str(e)}")
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.save()
            
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _execute_api_script(self, script):
        """执行API脚本"""
        engine = ScriptEngine()
        return engine.execute_api_script(script.content)

    def _execute_json_script(self, script):
        """执行JSON脚本"""
        engine = ScriptEngine()
        return engine.execute_json_script(script.content)

    def _execute_yaml_script(self, script):
        """执行YAML脚本"""
        engine = ScriptEngine()
        return engine.execute_yaml_script(script.content)


class ScriptExecutionViewSet(CacheMixin, QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """脚本执行记录API

    DEPRECATED: 2026-04-21
    请使用 TestExecution API (test_type='script') 替代。
    此 ViewSet 保留用于向后兼容，查询历史 ScriptExecution 记录。
    """
    queryset = ScriptExecution.objects.all()
    serializer_class = ScriptExecutionSerializer

    # 查询优化配置
    select_related_fields = ['script', 'executor']

    # 过滤器配置
    filter_int_fields = ['script']

    # 缓存配置
    cache_timeout = 120
    cache_list = True
    cache_retrieve = True

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ScriptExecutionCreateSerializer
        return ScriptExecutionSerializer
