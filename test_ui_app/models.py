"""
UI测试应用的数据模型
"""
from __future__ import annotations
from typing import Any, List, Optional, Dict, TYPE_CHECKING
from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django_stubs_ext.db.models import TypedModelMeta
import json

if TYPE_CHECKING:
    from core.models import Project


class UITestScript(models.Model):
    """UI测试脚本"""
    name: models.CharField[str, str] = models.CharField(max_length=200, verbose_name="脚本名称")
    description: models.TextField[str, str] = models.TextField(blank=True, verbose_name="描述")
    project: models.ForeignKey[Project, Project] = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='ui_test_scripts',
        verbose_name="所属项目"
    )
    created_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_ui_scripts',
        verbose_name="创建人"
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_active: models.BooleanField[bool, bool] = models.BooleanField(default=True, verbose_name="是否启用")
    
    # 统一的actions格式（JSON数组）
    actions: models.JSONField[List[Dict[str, Any]], List[Dict[str, Any]]] = models.JSONField(default=list, verbose_name="动作列表")
    
    # 浏览器配置
    BROWSER_TYPE_CHOICES: List[tuple[str, str]] = [
        ('chromium', 'Chromium'),
        ('firefox', 'Firefox'),
        ('webkit', 'WebKit'),
    ]
    browser_type: models.CharField[str, str] = models.CharField(
        max_length=20,
        default='chromium',
        choices=BROWSER_TYPE_CHOICES,
        verbose_name="浏览器类型"
    )
    headless: models.BooleanField[bool, bool] = models.BooleanField(default=True, verbose_name="无头模式")
    viewport_width: models.IntegerField[int, int] = models.IntegerField(default=1280, verbose_name="视口宽度")
    viewport_height: models.IntegerField[int, int] = models.IntegerField(default=720, verbose_name="视口高度")
    timeout: models.IntegerField[int, int] = models.IntegerField(default=30000, verbose_name="超时时间(毫秒)")
    
    class Meta(TypedModelMeta):
        verbose_name = "UI测试脚本"
        verbose_name_plural = "UI测试脚本"
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        return self.name


class UITestExecution(models.Model):
    """UI测试执行记录"""
    STATUS_CHOICES: List[tuple[str, str]] = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('passed', '通过'),
        ('failed', '失败'),
        ('skipped', '跳过'),
    ]
    
    script: models.ForeignKey[UITestScript, UITestScript] = models.ForeignKey(
        UITestScript,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name="测试脚本"
    )
    executed_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ui_test_executions',
        verbose_name="执行人"
    )
    status: models.CharField[str, str] = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="执行状态"
    )
    started_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    duration: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True, verbose_name="执行时长(秒)")
    
    # 执行结果
    result_summary: models.JSONField[Dict[str, Any], Dict[str, Any]] = models.JSONField(default=dict, verbose_name="结果摘要")
    error_message: models.TextField[Optional[str], Optional[str]] = models.TextField(null=True, blank=True, verbose_name="错误信息")
    screenshots: models.JSONField[List[str], List[str]] = models.JSONField(default=list, verbose_name="截图列表")
    execution_log: models.TextField[str, str] = models.TextField(blank=True, verbose_name="执行日志")
    
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta(TypedModelMeta):
        verbose_name = "UI测试执行记录"
        verbose_name_plural = "UI测试执行记录"
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        return f"{self.script.name} - {self.get_status_display()} - {self.created_at}"
