"""
Unified execution models views.
"""
from __future__ import annotations

from typing import Any

from django.db.models import Count, QuerySet
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.models.unified import UnifiedExecution, UnifiedScript

from .serializers import UnifiedExecutionSerializer, UnifiedScriptSerializer


class UnifiedScriptViewSet(viewsets.ReadOnlyModelViewSet):
    """统一脚本查询 ViewSet（只读）"""
    serializer_class = UnifiedScriptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[UnifiedScript]:
        qs = UnifiedScript.objects.select_related(
            'project', 'created_by', 'content_type',
        )
        script_type = self.request.query_params.get('script_type')
        project = self.request.query_params.get('project')
        name = self.request.query_params.get('name')
        is_active = self.request.query_params.get('is_active')

        if script_type:
            qs = qs.filter(script_type=script_type)
        if project:
            qs = qs.filter(project_id=project)
        if name:
            qs = qs.filter(name__icontains=name)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        return qs


class UnifiedExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """统一执行记录查询 ViewSet（只读）"""
    serializer_class = UnifiedExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[UnifiedExecution]:
        qs = UnifiedExecution.objects.select_related(
            'unified_script', 'unified_script__project',
            'executed_by', 'content_type',
        )
        unified_script = self.request.query_params.get('unified_script')
        status_param = self.request.query_params.get('status')
        executed_by = self.request.query_params.get('executed_by')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if unified_script:
            qs = qs.filter(unified_script_id=unified_script)
        if status_param:
            qs = qs.filter(status=status_param)
        if executed_by:
            qs = qs.filter(executed_by_id=executed_by)
        if start_date:
            qs = qs.filter(started_at__gte=start_date)
        if end_date:
            qs = qs.filter(started_at__lte=end_date)
        return qs

    @action(detail=False, methods=['get'])
    def statistics(self, request: Request) -> Response:
        """跨类型执行统计"""
        qs = self.get_queryset()
        total = qs.count()
        by_status = qs.values('status').annotate(count=Count('id'))
        by_type = qs.values(
            'unified_script__script_type',
        ).annotate(count=Count('id'))

        status_dict = {
            item['status']: item['count'] for item in by_status
        }
        passed = status_dict.get('passed', 0)

        return Response({
            'total': total,
            'passed': passed,
            'failed': status_dict.get('failed', 0),
            'running': status_dict.get('running', 0),
            'pending': status_dict.get('pending', 0),
            'stopped': status_dict.get('stopped', 0),
            'pass_rate': (
                round(passed / total * 100, 2) if total > 0 else 0
            ),
            'by_type': {
                item['unified_script__script_type']: item['count']
                for item in by_type
            },
        })
