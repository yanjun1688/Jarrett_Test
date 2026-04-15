"""
Test Management Models

This module contains test case, test execution, and test flow models.
"""

from typing import Any, Dict
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q, Count, Manager, QuerySet
from django.utils import timezone

from .project import Project, Module


class TestCase(models.Model):
    """统一测试用例模型"""
    
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '紧急'),
    ]
    
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
        verbose_name='所属模块'
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
    
    class Meta:
        verbose_name = '测试用例'
        verbose_name_plural = '测试用例'
        ordering = ['-created_at']
        db_table = 'core_test_case'
    
    def __str__(self) -> str:
        return self.title


class TestExecutionQuerySet(QuerySet['TestExecution']):
    """测试执行记录的自定义 QuerySet"""

    def by_project(self, project: Any) -> 'TestExecutionQuerySet':
        """按项目过滤"""
        return self.filter(
            Q(test_case__project=project) | Q(api_request__project=project) | Q(collection_execution__collection__project=project)
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
                        Count('collection_execution', distinct=True, filter=Q(collection_execution__isnull=False))
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
        ('ui', 'UI测试'),
        ('flow', '流程测试'),
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
        if self.test_type == 'api' and self.api_request:
            return f"{self.api_request.name} - {self.get_status_display()}"
        elif self.test_type == 'api' and self.collection_execution:
            return f"{self.collection_execution.collection.name} - {self.get_status_display()}"
        elif self.test_type == 'api':
            return f"API测试 - {self.get_status_display()}"
        elif self.test_case:
            return f"{self.test_case.title} - {self.get_status_display()}"
        else:
            return f"测试执行 - {self.get_status_display()}"


class TestFlow(models.Model):
    """Test flow model"""
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='test_flows',
        null=True,
        verbose_name='Project'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='core_test_flows',
        null=True,
        verbose_name='Created By'
    )
    name = models.CharField(max_length=255, verbose_name='Flow Name')
    description = models.TextField(blank=True, verbose_name='Description')
    scenario_description = models.TextField(verbose_name='Scenario Description')
    flow_data = models.JSONField(default=dict, verbose_name='Flow Data')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    version = models.IntegerField(default=1, verbose_name='Version')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Test Flow'
        verbose_name_plural = 'Test Flows'
        ordering = ['-updated_at']
        db_table = 'core_test_flow'
        indexes = [
            models.Index(fields=['project', 'is_active']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} (v{self.version})"


class TestFlowExecution(models.Model):
    """Test flow execution record"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    test_flow = models.ForeignKey(
        TestFlow,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='Test Flow'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='core_flow_executions',
        null=True,
        verbose_name='Executed By'
    )
    execution_data = models.JSONField(default=dict, verbose_name='Execution Data')
    result = models.JSONField(default=dict, blank=True, verbose_name='Execution Result')
    metrics = models.JSONField(default=dict, blank=True, verbose_name='Execution Metrics')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status'
    )
    error_message = models.TextField(blank=True, verbose_name='Error Message')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Started At')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Completed At')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        verbose_name = 'Flow Execution'
        verbose_name_plural = 'Flow Executions'
        ordering = ['-created_at']
        db_table = 'core_test_flow_execution'
        indexes = [
            models.Index(fields=['test_flow', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.test_flow.name} - {self.get_status_display()}"
    
    @property
    def duration(self) -> float | None:
        """Execution duration in seconds"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def nodes_executed(self) -> int:
        """Number of nodes executed (from metrics)"""
        return self.metrics.get('nodes_executed', 0) if self.metrics else 0
    
    @property
    def successful_nodes(self) -> int:
        """Number of successful nodes (from metrics)"""
        return self.metrics.get('successful_nodes', 0) if self.metrics else 0
    
    @property
    def failed_nodes(self) -> int:
        """Number of failed nodes (from metrics)"""
        return self.metrics.get('failed_nodes', 0) if self.metrics else 0