"""
Test Management Models

This module contains test case, test execution, and test flow models.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q, Count, Manager, QuerySet
from django.utils import timezone

from .project import Project, Module


class TestCase(models.Model):
    """统一测试用例模型 - 扩展支持AI生成"""
    
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '紧急'),
    ]
    
    class Source(models.TextChoices):
        CHATBOT = 'chatbot', 'Chatbot生成'
        MANUAL_UPLOAD = 'manual_upload', '手动上传PRD'
        MANUAL_CREATE = 'manual_create', '手动创建'
    
    title = models.CharField(max_length=200, verbose_name='用例标题')
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='testcases',
        verbose_name='所属项目'
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='testcases',
        verbose_name='所属模块',
        null=True,
        blank=True
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='优先级'
    )
    precondition = models.TextField(blank=True, verbose_name='前置条件')
    steps = models.TextField(verbose_name='测试步骤')
    expected_result = models.TextField(verbose_name='预期结果')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testcases',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL_CREATE,
        verbose_name='来源',
        db_index=True
    )
    
    prd_document = models.ForeignKey(
        'core.KnowledgeDocument',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='关联PRD文档'
    )
    
    conversation = models.ForeignKey(
        'core.AgentConversation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='生成会话'
    )
    
    quality_score = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='质量评分'
    )
    
    generation_metadata = models.JSONField(
        default=dict,
        verbose_name='生成元数据'
    )
    
    class Meta:
        verbose_name = '测试用例'
        verbose_name_plural = '测试用例'
        ordering = ['-created_at']
        db_table = 'core_test_case'
        indexes = [
            models.Index(fields=['project', 'source']),
            models.Index(fields=['prd_document']),
        ]
    
    def __str__(self) -> str:
        return self.title


class TestExecutionQuerySet(QuerySet['TestExecution']):
    """测试执行记录的自定义 QuerySet"""

    def by_project(self, project: Any) -> 'TestExecutionQuerySet':
        """按项目过滤"""
        return self.filter(
            Q(test_case__project=project) |
            Q(api_request__project=project) |
            Q(collection_execution__collection__project=project) |
            Q(test_script__project=project)
        )

    def by_date_range(self, start_date: Any, end_date: Any) -> 'TestExecutionQuerySet':
        """按时间范围过滤"""
        return self.filter(executed_at__range=[start_date, end_date])

    def aggregate_stats(self) -> Dict[str, Any]:
        """聚合统计执行数据"""
        return self.aggregate(
            total_executions=Count('id'),
            passed_executions=Count('id', filter=Q(status='passed')),
            failed_executions=Count('id', filter=Q(status='failed')),
            blocked_executions=Count('id', filter=Q(status='blocked')),
            skipped_executions=Count('id', filter=Q(status='skipped')),
            total_cases=Count('test_case', distinct=True, filter=Q(test_case__isnull=False)) +
                        Count('api_request', distinct=True, filter=Q(api_request__isnull=False)) +
                        Count('collection_execution', distinct=True, filter=Q(collection_execution__isnull=False)) +
                        Count('test_script', distinct=True, filter=Q(test_script__isnull=False))
        )


class TestExecutionManager(Manager['TestExecution']):
    """测试执行记录的自定义 Manager"""

    def get_queryset(self) -> TestExecutionQuerySet:
        return TestExecutionQuerySet(self.model, using=self._db)

    def by_project(self, project: Any) -> QuerySet['TestExecution']:
        return self.get_queryset().by_project(project)

    def by_project_and_date_range(self, project: Any, start_date: Any, end_date: Any) -> QuerySet['TestExecution']:
        qs = self.get_queryset()
        return qs.by_project(project).by_date_range(start_date, end_date)


class TestExecution(models.Model):
    """统一测试执行记录模型 - 支持功能测试、API测试、UI测试"""
    
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('passed', '通过'),
        ('failed', '失败'),
        ('blocked', '阻塞'),
        ('skipped', '跳过'),
    ]

    TEST_TYPE_CHOICES = [
        ('functional', '功能测试'),
        ('api', 'API测试'),
        ('flow', '流程测试'),
        ('script', '测试脚本'),
    ]

    test_type = models.CharField(
        max_length=20,
        choices=TEST_TYPE_CHOICES,
        default='functional',
        verbose_name='测试类型'
    )
    
    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name='executions',
        null=True,
        blank=True,
        verbose_name='功能测试用例',
        db_index=True
    )
    
    api_request = models.ForeignKey(
        'testmanager_app.ApiRequest',
        on_delete=models.CASCADE,
        related_name='executions',
        null=True,
        blank=True,
        verbose_name='API请求'
    )

    collection_execution = models.ForeignKey(
        'testmanager_app.CollectionExecution',
        on_delete=models.CASCADE,
        related_name='api_executions',
        null=True,
        blank=True,
        verbose_name='所属集合执行'
    )

    test_script = models.ForeignKey(
        'testmanager_app.TestScript',
        on_delete=models.CASCADE,
        related_name='executions',
        null=True,
        blank=True,
        verbose_name='测试脚本',
        db_index=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='执行状态',
        db_index=True
    )
    
    executed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='test_executions',
        verbose_name='执行人'
    )
    
    executed_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='执行时间',
        db_index=True
    )
    
    duration = models.FloatField(default=0, verbose_name='执行时长(秒)')
    
    actual_result = models.TextField(blank=True, verbose_name='实际结果')
    notes = models.TextField(blank=True, verbose_name='备注')
    
    api_response_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='API响应数据'
    )
    api_logs = models.TextField(blank=True, verbose_name='API执行日志')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    step_results = models.JSONField(
        null=True,
        blank=True,
        verbose_name='步骤执行结果',
        help_text='格式: {"total": 10, "passed": 8, "failed": 2, "details": [...]}'
    )
    
    screenshot_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='截图路径'
    )
    log_file_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='日志文件路径'
    )
    
    class Meta:
        verbose_name = '测试执行记录'
        verbose_name_plural = '测试执行记录'
        ordering = ['-executed_at']
        db_table = 'core_test_execution'
    
    objects = TestExecutionManager()
    
    def __str__(self) -> str:
        if self.test_type == 'script' and self.test_script:
            return f"{self.test_script.name} - {self.get_status_display()}"
        elif self.test_type == 'api' and self.api_request:
            return f"{self.api_request.name} - {self.get_status_display()}"
        elif self.test_type == 'api' and self.collection_execution:
            return f"{self.collection_execution.collection.name} - {self.get_status_display()}"
        elif self.test_type == 'api':
            return f"API测试 - {self.get_status_display()}"
        elif self.test_case:
            return f"{self.test_case.title} - {self.get_status_display()}"
        else:
            return f"测试执行 - {self.get_status_display()}"


