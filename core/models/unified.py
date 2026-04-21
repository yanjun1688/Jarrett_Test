"""
Unified Execution Models

Bridge models that unify all script and execution record types
across testmanager_app and test_ui_app via Django ContentType framework.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django_stubs_ext.db.models import TypedModelMeta

from .project import Project


class ScriptType(models.TextChoices):
    API = 'api', 'API测试'
    UI = 'ui', 'UI测试'
    PRESSURE = 'pressure', '压测'
    ADVANCED_PRESSURE = 'advanced_pressure', '高级压测'


class UnifiedStatus(models.TextChoices):
    PENDING = 'pending', '待执行'
    RUNNING = 'running', '执行中'
    PASSED = 'passed', '通过'
    FAILED = 'failed', '失败'
    STOPPED = 'stopped', '已停止'


class UnifiedScript(models.Model):
    """统一脚本注册表 - 桥接所有类型的测试脚本"""

    # 反规范化字段
    name: models.CharField[str, str] = models.CharField(
        max_length=200, verbose_name='脚本名称', db_index=True,
    )
    description: models.TextField[str, str] = models.TextField(
        blank=True, verbose_name='描述',
    )
    script_type: models.CharField[str, str] = models.CharField(
        max_length=30, choices=ScriptType.choices,
        verbose_name='脚本类型', db_index=True,
    )
    project: models.ForeignKey[Optional[Project], Optional[Project]] = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='unified_scripts',
        verbose_name='所属项目',
        null=True,
        blank=True,
        db_index=True,
    )
    created_by: models.ForeignKey[Optional[User], Optional[User]] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unified_scripts',
        verbose_name='创建人',
    )
    is_active: models.BooleanField[bool, bool] = models.BooleanField(
        default=True, verbose_name='是否启用', db_index=True,
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间',
    )
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now=True, verbose_name='更新时间',
    )

    # GenericForeignKey 指向源模型
    content_type: models.ForeignKey[ContentType, ContentType] = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name='源模型类型',
    )
    object_id: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        verbose_name='源模型ID',
    )
    source_object = GenericForeignKey('content_type', 'object_id')

    class Meta(TypedModelMeta):
        verbose_name = '统一脚本'
        verbose_name_plural = '统一脚本'
        ordering = ['-created_at']
        db_table = 'core_unified_script'
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id'],
                name='unique_unified_script_source',
            ),
        ]
        indexes = [
            models.Index(fields=['script_type', 'is_active']),
            models.Index(fields=['project', 'script_type']),
        ]

    def __str__(self) -> str:
        return f'{self.name} ({self.get_script_type_display()})'


class UnifiedExecution(models.Model):
    """统一执行记录注册表 - 桥接所有类型的执行记录"""

    # 关联到 UnifiedScript
    unified_script: models.ForeignKey[UnifiedScript, UnifiedScript] = models.ForeignKey(
        UnifiedScript,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='统一脚本',
        db_index=True,
    )

    # 反规范化字段
    status: models.CharField[str, str] = models.CharField(
        max_length=20, choices=UnifiedStatus.choices,
        default=UnifiedStatus.PENDING,
        verbose_name='执行状态', db_index=True,
    )
    executed_by: models.ForeignKey[Optional[User], Optional[User]] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unified_executions',
        verbose_name='执行人', db_index=True,
    )
    started_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = (
        models.DateTimeField(
            null=True, blank=True,
            verbose_name='开始时间', db_index=True,
        )
    )
    completed_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = (
        models.DateTimeField(
            null=True, blank=True,
            verbose_name='完成时间',
        )
    )
    duration_seconds: models.FloatField[Optional[float], Optional[float]] = models.FloatField(
        null=True, blank=True, verbose_name='执行时长(秒)',
    )
    error_message: models.TextField[str, str] = models.TextField(
        blank=True, verbose_name='错误信息',
    )

    # GenericForeignKey 指向源执行记录
    content_type: models.ForeignKey[ContentType, ContentType] = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name='源模型类型',
    )
    object_id: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        verbose_name='源模型ID',
    )
    source_object = GenericForeignKey('content_type', 'object_id')

    class Meta(TypedModelMeta):
        verbose_name = '统一执行记录'
        verbose_name_plural = '统一执行记录'
        ordering = ['-started_at']
        db_table = 'core_unified_execution'
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id'],
                name='unique_unified_execution_source',
            ),
        ]
        indexes = [
            models.Index(fields=['unified_script', 'status']),
            models.Index(fields=['executed_by', 'started_at']),
        ]

    def __str__(self) -> str:
        return f'{self.unified_script.name} - {self.get_status_display()}'
