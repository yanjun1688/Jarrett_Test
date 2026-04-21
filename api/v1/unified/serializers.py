"""
Unified execution models serializers.
"""
from __future__ import annotations

from rest_framework import serializers

from core.models.unified import UnifiedExecution, UnifiedScript


class UnifiedScriptSerializer(serializers.ModelSerializer[UnifiedScript]):
    """统一脚本序列化器（只读）"""
    project_name = serializers.CharField(
        source='project.name', read_only=True, default=None,
    )
    created_by_name = serializers.CharField(
        source='created_by.username', read_only=True, default=None,
    )
    script_type_display = serializers.CharField(
        source='get_script_type_display', read_only=True,
    )

    class Meta:
        model = UnifiedScript
        fields = [
            'id', 'name', 'description',
            'script_type', 'script_type_display',
            'project', 'project_name',
            'created_by', 'created_by_name',
            'is_active', 'created_at', 'updated_at',
            'content_type', 'object_id',
        ]
        read_only_fields = fields


class UnifiedExecutionSerializer(serializers.ModelSerializer[UnifiedExecution]):
    """统一执行记录序列化器（只读）"""
    unified_script_name = serializers.CharField(
        source='unified_script.name', read_only=True,
    )
    script_type = serializers.CharField(
        source='unified_script.script_type', read_only=True,
    )
    executed_by_name = serializers.CharField(
        source='executed_by.username', read_only=True, default=None,
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
    )

    class Meta:
        model = UnifiedExecution
        fields = [
            'id', 'unified_script', 'unified_script_name', 'script_type',
            'status', 'status_display',
            'executed_by', 'executed_by_name',
            'started_at', 'completed_at', 'duration_seconds',
            'error_message',
            'content_type', 'object_id',
        ]
        read_only_fields = fields
