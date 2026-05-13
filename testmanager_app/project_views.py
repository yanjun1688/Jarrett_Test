"""
项目相关视图
包含：ProjectViewSet, ModuleViewSet
"""

from __future__ import annotations

import logging
from typing import Any

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from core.models import Project, Module
from testmanager_app.serializers import ProjectSerializer, ModuleSerializer
from testmanager_app.viewsets import BaseViewSet, QueryOptimizerMixin, CommonFilterMixin
from testmanager_app.services.project_statistics import get_statistics

logger = logging.getLogger(__name__)


class ProjectViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
    """项目管理API

    继承BaseViewSet实现：
    - 自动设置 permission_classes = [RoleBasedPermission]
    - 自动填充 created_by (Project模型有这个字段)
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    # 查询优化配置 - 解决 N+1 查询问题
    select_related_fields = ['created_by']

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request: Request) -> Response:
        """
        GET /api/v1/projects/statistics/           → 全局 + 所有项目
        GET /api/v1/projects/statistics/?project=5 → 全局 + 指定项目
        """
        try:
            pid = request.query_params.get('project')
            data = get_statistics(int(pid) if pid else None)
            return Response(data)
        except Project.DoesNotExist:
            return Response({'error': '项目不存在'}, status=404)
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return Response({'error': '获取统计数据失败'}, status=500)


class ModuleViewSet(QueryOptimizerMixin, CommonFilterMixin, BaseViewSet):
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