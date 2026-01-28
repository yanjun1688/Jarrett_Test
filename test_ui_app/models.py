"""
UI测试应用的数据模型
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class UITestScript(models.Model):
    """UI测试脚本"""
    name = models.CharField(max_length=200, verbose_name="脚本名称")
    description = models.TextField(blank=True, verbose_name="描述")
    project = models.ForeignKey(
        'testmanager_app.Project',
        on_delete=models.CASCADE,
        related_name='ui_test_scripts',
        null=True,
        blank=True,
        verbose_name="所属项目"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_ui_scripts',
        verbose_name="创建人"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    
    # 统一的actions格式（JSON数组）
    # 格式: [{"id": "action_1", "order": 1, "type": "navigate", "params": {...}, "selector": {...}, "description": "..."}, ...]
    actions = models.JSONField(default=list, verbose_name="动作列表")
    
    # 浏览器配置
    browser_type = models.CharField(
        max_length=20,
        default='chromium',
        choices=[('chromium', 'Chromium'), ('firefox', 'Firefox'), ('webkit', 'WebKit')],
        verbose_name="浏览器类型"
    )
    headless = models.BooleanField(default=True, verbose_name="无头模式")
    viewport_width = models.IntegerField(default=1280, verbose_name="视口宽度")
    viewport_height = models.IntegerField(default=720, verbose_name="视口高度")
    timeout = models.IntegerField(default=30000, verbose_name="超时时间(毫秒)")
    
    class Meta:
        verbose_name = "UI测试脚本"
        verbose_name_plural = "UI测试脚本"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class UITestExecution(models.Model):
    """UI测试执行记录"""
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('passed', '通过'),
        ('failed', '失败'),
        ('skipped', '跳过'),
    ]
    
    script = models.ForeignKey(
        UITestScript,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name="测试脚本"
    )
    executed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ui_test_executions',
        verbose_name="执行人"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="执行状态"
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    duration = models.FloatField(null=True, blank=True, verbose_name="执行时长(秒)")
    
    # 执行结果
    result_summary = models.JSONField(default=dict, verbose_name="结果摘要")
    error_message = models.TextField(null=True, blank=True, verbose_name="错误信息")
    screenshots = models.JSONField(default=list, verbose_name="截图列表")
    execution_log = models.TextField(blank=True, verbose_name="执行日志")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "UI测试执行记录"
        verbose_name_plural = "UI测试执行记录"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.script.name} - {self.get_status_display()} - {self.created_at}"
