"""
Test Manager App Models

业务测试管理模型 - 外键引用 core 统一模型
"""
from __future__ import annotations
from typing import Any, List, Optional, Dict, TYPE_CHECKING
from datetime import datetime, timedelta
import secrets
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Manager, QuerySet, Count, Q
from django_stubs_ext.db.models import TypedModelMeta
from django.core.exceptions import ValidationError

if TYPE_CHECKING:
    from core.models import Project


class TestReport(models.Model):
    """测试报告模型"""
    project: models.ForeignKey[Project, Project] = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='所属项目'
    )
    name: models.CharField[str, str] = models.CharField(max_length=100, verbose_name='报告名称')
    description: models.TextField[str, str] = models.TextField(blank=True, verbose_name='报告描述')
    start_date: models.DateTimeField[datetime, datetime] = models.DateTimeField(verbose_name='开始时间')
    end_date: models.DateTimeField[datetime, datetime] = models.DateTimeField(verbose_name='结束时间')
    total_cases: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='总用例数')
    passed_cases: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='通过用例数')
    failed_cases: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='失败用例数')
    blocked_cases: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='阻塞用例数')
    skipped_cases: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='跳过用例数')
    created_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='test_reports',
        verbose_name='创建人'
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta(TypedModelMeta):
        verbose_name = '测试报告'
        verbose_name_plural = '测试报告'
        ordering = ['-created_at']
        db_table = 'test_report'
    
    def __str__(self) -> str:
        return self.name
    
    @property
    def pass_rate(self) -> float:
        """通过率"""
        if self.total_cases == 0:
            return 0
        return round((self.passed_cases / self.total_cases) * 100, 2)


class TestScript(models.Model):
    """测试脚本模型 - 简化为API配置工具"""
    SCRIPT_TYPE_CHOICES: List[tuple[str, str]] = [
        ('api', 'API测试'),
        ('yaml', 'YAML配置'),
    ]

    name: models.CharField[str, str] = models.CharField(max_length=100, verbose_name='脚本名称')
    description: models.TextField[str, str] = models.TextField(blank=True, verbose_name='脚本描述')
    script_type: models.CharField[str, str] = models.CharField(max_length=20, choices=SCRIPT_TYPE_CHOICES, default='api', verbose_name='脚本类型')
    content: models.TextField[str, str] = models.TextField(verbose_name='脚本内容', help_text='YAML格式的API测试配置')
    project: models.ForeignKey[Project, Project] = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='test_scripts',
        verbose_name='所属项目'
    )
    created_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='test_scripts',
        verbose_name='创建人'
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    is_active: models.BooleanField[bool, bool] = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta(TypedModelMeta):
        verbose_name = '测试脚本'
        verbose_name_plural = '测试脚本'
        ordering = ['-created_at']
        db_table = 'test_script'

    def __str__(self) -> str:
        return self.name


class ScriptExecution(models.Model):
    """脚本执行记录模型"""
    STATUS_CHOICES: List[tuple[str, str]] = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
    ]
    
    script: models.ForeignKey[TestScript, TestScript] = models.ForeignKey(
        TestScript,
        on_delete=models.CASCADE,
        related_name='script_executions',
        verbose_name='测试脚本'
    )
    executor: models.ForeignKey[User, User] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='script_executions',
        verbose_name='执行人'
    )
    status: models.CharField[str, str] = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='执行状态')
    output: models.TextField[str, str] = models.TextField(blank=True, verbose_name='执行输出')
    error_message: models.TextField[str, str] = models.TextField(blank=True, verbose_name='错误信息')
    started_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    finished_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    duration: models.DurationField[timedelta, timedelta] = models.DurationField(null=True, blank=True, verbose_name='执行耗时')
    
    class Meta(TypedModelMeta):
        verbose_name = '脚本执行记录'
        verbose_name_plural = '脚本执行记录'
        ordering = ['-started_at']
        db_table = 'script_execution'
    
    def __str__(self) -> str:
        return f"{self.script.name} - {self.get_status_display()}"  # type: ignore[attr-defined]

    @property
    def calculated_duration(self) -> Optional[timedelta]:
        """计算执行耗时 - 优先使用 duration 字段，否则根据起止时间计算"""
        if self.duration:
            return self.duration
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None


class ApiRequest(models.Model):
    """API请求模型"""
    METHOD_CHOICES: List[tuple[str, str]] = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
        ('HEAD', 'HEAD'),
        ('OPTIONS', 'OPTIONS'),
    ]

    name: models.CharField[str, str] = models.CharField(max_length=100, verbose_name='请求名称')
    description: models.TextField[str, str] = models.TextField(blank=True, verbose_name='请求描述')
    url: models.URLField[str, str] = models.URLField(verbose_name='请求URL')
    method: models.CharField[str, str] = models.CharField(max_length=10, choices=METHOD_CHOICES, default='GET', verbose_name='请求方法')
    headers: models.TextField[str, str] = models.TextField(blank=True, verbose_name='请求头')
    body: models.TextField[str, str] = models.TextField(blank=True, verbose_name='请求体')
    project: models.ForeignKey[Project, Project] = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='api_requests',
        verbose_name='所属项目'
    )
    created_by: models.ForeignKey[User, User] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_requests',
verbose_name='创建人'
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    order_index: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='执行顺序', db_index=True)
    extract_rules: models.JSONField[Optional[List[Dict[str, Any]]], Optional[List[Dict[str, Any]]]] = models.JSONField(
        null=True,
        blank=True,
        verbose_name='变量提取规则',
        help_text='JSON格式: [{"name": "var_name", "jsonpath": "$.data.id"}]'
    )
    stop_on_failure: models.BooleanField[bool, bool] = models.BooleanField(default=True, verbose_name='失败时停止')
    is_enabled: models.BooleanField[bool, bool] = models.BooleanField(
        default=True,
        verbose_name='启用状态',
        help_text='链式执行时，仅执行已启用的请求'
    )

    class Meta(TypedModelMeta):
        verbose_name = 'API请求'
        verbose_name_plural = 'API请求'
        ordering = ['project', 'order_index', '-created_at']
        db_table = 'api_request'
    
    def __str__(self) -> str:
        return self.name


class ApiAssertion(models.Model):
    """API断言模型
    
    设计理念：以「值定位」为核心，而不是以「响应类型」为核心
    - HTTP状态码只是一个特殊的值来源
    - 响应体字段断言才是接口测试的主战场
    - 一个断言只表达一个判断：一个值路径 + 一个比较方式 + 一个期望结果
    """
    ASSERTION_TYPE_CHOICES: List[tuple[str, str]] = [
        ('status_code', '状态码'),
        ('response_time', '响应时间'),
        ('response_body_field', '响应体字段'),
        ('response_header_field', '响应头字段'),
        ('jsonpath', 'JSONPath断言'),
    ]
    
    COMPARISON_CHOICES: List[tuple[str, str]] = [
        ('equals', '等于'),
        ('contains', '包含'),
        ('not_contains', '不包含'),
        ('greater_than', '大于'),
        ('less_than', '小于'),
    ]
    
    api_request: models.ForeignKey[ApiRequest, ApiRequest] = models.ForeignKey(
        ApiRequest,
        on_delete=models.CASCADE,
        related_name='assertions',
        verbose_name='API请求'
    )
    assertion_type: models.CharField[str, str] = models.CharField(max_length=30, choices=ASSERTION_TYPE_CHOICES, verbose_name='断言类型')
    field_path: models.CharField[str, str] = models.CharField(max_length=200, blank=True, verbose_name='字段路径')
    comparison: models.CharField[str, str] = models.CharField(max_length=20, choices=COMPARISON_CHOICES, verbose_name='比较方式')
    expected_value: models.CharField[str, str] = models.CharField(max_length=200, verbose_name='期望值')
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta(TypedModelMeta):
        verbose_name = 'API断言'
        verbose_name_plural = 'API断言'
        ordering = ['created_at']
        db_table = 'api_assertion'
    
    def __str__(self) -> str:
        return f"{self.api_request.name} - {self.get_assertion_type_display()}"  # type: ignore[attr-defined]
    
    def clean(self) -> None:
        """模型级别的验证：字段路径条件必填"""
        if self.assertion_type in ['response_body_field', 'response_header_field']:
            if not self.field_path or not self.field_path.strip():
                raise ValidationError({
                    'field_path': f'当断言类型为"{self.get_assertion_type_display()}"时，字段路径为必填项'  # type: ignore[attr-defined]
                })


class RequestCollection(models.Model):
    """请求集合模型"""
    EXECUTION_MODE_CHOICES: List[tuple[str, str]] = [
        ('sequential', '顺序执行'),
        ('concurrent', '并发执行'),
        ('chain', '链式执行（支持变量传递）'),
    ]

    name: models.CharField[str, str] = models.CharField(max_length=100, verbose_name='集合名称')
    description: models.TextField[str, str] = models.TextField(blank=True, verbose_name='集合描述')
    project: models.ForeignKey[Project, Project] = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='request_collections',
        verbose_name='所属项目'
    )
    execution_mode: models.CharField[str, str] = models.CharField(max_length=20, choices=EXECUTION_MODE_CHOICES, default='concurrent', verbose_name='执行模式')
    created_by: models.ForeignKey[User, User] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request_collections',
        verbose_name='创建人'
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    variables: models.JSONField[Optional[List[Dict[str, Any]]], Optional[List[Dict[str, Any]]]] = models.JSONField(
        default=list,
        blank=True,
        verbose_name='场景变量',
        help_text='格式: [{"key": "baseUrl", "value": "https://api.example.com"}]'
    )

    class Meta(TypedModelMeta):
        verbose_name = '请求集合'
        verbose_name_plural = '请求集合'
        ordering = ['-created_at']
        db_table = 'request_collection'

    def __str__(self) -> str:
        return self.name


class CollectionRequest(models.Model):
    """请求集合与API请求的关联表（支持排序和配置）"""
    REQUEST_TYPE_CHOICES: List[tuple[str, str]] = [
        ('normal', '正常请求'),
        ('setup', 'Setup前置请求'),
        ('teardown', 'Teardown后置请求'),
    ]
    
    collection: models.ForeignKey[RequestCollection, RequestCollection] = models.ForeignKey(
        RequestCollection,
        on_delete=models.CASCADE,
        related_name='collection_requests',
        verbose_name='请求集合'
    )
    api_request: models.ForeignKey[ApiRequest, ApiRequest] = models.ForeignKey(
        ApiRequest,
        on_delete=models.CASCADE,
        related_name='collection_requests',
        verbose_name='API请求'
    )
    order_index: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='执行顺序', db_index=True)
    request_type: models.CharField[str, str] = models.CharField(
        max_length=20,
        choices=REQUEST_TYPE_CHOICES,
        default='normal',
        verbose_name='请求类型',
        help_text='Setup: 在正常请求前执行；Teardown: 在正常请求后执行（无论成功失败）'
    )
    stop_on_failure: models.BooleanField[bool, bool] = models.BooleanField(default=True, verbose_name='失败时停止')
    extract_rules: models.JSONField[Optional[List[Dict[str, Any]]], Optional[List[Dict[str, Any]]]] = models.JSONField(
        null=True,
        blank=True,
        verbose_name='变量提取规则',
        help_text='JSON格式: [{"name": "var_name", "jsonpath": "$.data.id"}]'
    )
    request_count: models.IntegerField[int, int] = models.IntegerField(
        default=1,
        verbose_name='请求次数',
        validators=[
            MinValueValidator(1, '请求次数必须大于0'),
            MaxValueValidator(1000, '单次请求次数不能超过1000')
        ],
        help_text='该请求在集合中的执行次数'
    )

    class Meta(TypedModelMeta):
        verbose_name = '集合请求关联'
        verbose_name_plural = '集合请求关联'
        ordering = ['order_index']
        unique_together = ['collection', 'api_request']
        db_table = 'collection_request'

    def __str__(self) -> str:
        return f"{self.collection.name} - {self.api_request.name} (#{self.order_index})"


class CollectionExecution(models.Model):
    """集合执行记录模型"""
    STATUS_CHOICES: List[tuple[str, str]] = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
    ]
    
    collection: models.ForeignKey[RequestCollection, RequestCollection] = models.ForeignKey(
        RequestCollection,
        on_delete=models.CASCADE,
        related_name='collection_executions',
        verbose_name='请求集合'
    )
    executor: models.ForeignKey[User, User] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collection_executions',
        verbose_name='执行人'
    )
    status: models.CharField[str, str] = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='执行状态')
    total_requests: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='总请求数')
    passed_requests: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='通过请求数')
    failed_requests: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='失败请求数')
    output: models.TextField[str, str] = models.TextField(blank=True, verbose_name='执行输出')
    started_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    finished_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    duration: models.DurationField[timedelta, timedelta] = models.DurationField(null=True, blank=True, verbose_name='执行耗时')
    
    class Meta(TypedModelMeta):
        verbose_name = '集合执行记录'
        verbose_name_plural = '集合执行记录'
        ordering = ['-started_at']
        db_table = 'collection_execution'
    
    def __str__(self) -> str:
        return f"{self.collection.name} - {self.get_status_display()}"  # type: ignore[attr-defined]

    @property
    def calculated_duration(self) -> Optional[timedelta]:
        """计算执行耗时 - 优先使用 duration 字段，否则根据起止时间计算"""
        if self.duration:
            return self.duration
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None

    @property
    def pass_rate(self) -> float:
        """通过率"""
        if self.total_requests == 0:
            return 0
        return round((self.passed_requests / self.total_requests) * 100, 2)


class FeatureTestCase(models.Model):
    """功能测试用例（MVP）
    所有业务字段均为纯文本，不做权限控制
    """
    title: models.CharField[str, str] = models.CharField(max_length=200, verbose_name='测试标题')
    project: models.ForeignKey[Project, Project] = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='feature_test_cases',
        verbose_name='所属项目'
    )
    created_by: models.ForeignKey[User, User] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feature_test_cases',
        verbose_name='创建人'
    )
    pre_steps: models.TextField[str, str] = models.TextField(blank=True, verbose_name='前置步骤')
    steps: models.TextField[str, str] = models.TextField(verbose_name='操作步骤')
    expected_result: models.TextField[str, str] = models.TextField(verbose_name='预期结果')
    actual_result: models.TextField[str, str] = models.TextField(blank=True, verbose_name='实际结果')
    to_confirm: models.TextField[str, str] = models.TextField(blank=True, verbose_name='待确定')
    is_passed: models.BooleanField[Optional[bool], Optional[bool]] = models.BooleanField(null=True, blank=True, verbose_name='是否通过')
    version: models.CharField[str, str] = models.CharField(max_length=50, blank=True, verbose_name='版本号')
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta(TypedModelMeta):
        verbose_name = '功能测试用例'
        verbose_name_plural = '功能测试用例'
        ordering = ['-created_at']
        db_table = 'feature_test_case'

    def __str__(self) -> str:
        return str(self.title)[:50]


class AuthToken(models.Model):
    """自定义Token模型，支持过期时间和多端点登录"""
    id: models.BigAutoField[int, int] = models.BigAutoField(primary_key=True, verbose_name='ID')
    key: models.CharField[str, str] = models.CharField(max_length=100, unique=True, verbose_name='Token密钥')
    token: models.CharField[Optional[str], Optional[str]] = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name='Token值')
    user: models.ForeignKey[User, User] = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='auth_tokens',
        verbose_name='用户'
    )
    created: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    expires_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(blank=True, null=True, verbose_name='过期时间')
    last_used: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True, verbose_name='最后使用时间')
    is_active: models.BooleanField[bool, bool] = models.BooleanField(default=True, verbose_name='是否激活')
    
    class Meta(TypedModelMeta):
        verbose_name = '认证Token'
        verbose_name_plural = '认证Token'
        ordering = ['-created']
        db_table = 'auth_token'
    
    def __str__(self) -> str:
        return f"{self.user.username} - {self.key[:8] if self.key else ''}..."
    
    def is_expired(self) -> bool:
        """检查token是否过期"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def refresh(self) -> None:
        """刷新token（延长过期时间）"""
        self.expires_at = timezone.now() + timedelta(days=7)
        self.save()
    
    @staticmethod
    def generate_key() -> str:
        """生成token密钥"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create_token(user: User, expires_in_days: int = 7) -> AuthToken:
        """创建新的token（支持多端点登录）"""
        key = AuthToken.generate_key()
        expires_at = timezone.now() + timedelta(days=expires_in_days)
        token = AuthToken.objects.create(
            user=user,
            key=key,
            expires_at=expires_at
        )
        return token
    
    @staticmethod
    def refresh_token(token_key: str) -> Optional[AuthToken]:
        """刷新token（延长过期时间）"""
        try:
            token = AuthToken.objects.get(key=token_key)
            if token.is_expired():
                return None
            token.expires_at = timezone.now() + timedelta(days=7)
            token.save()
            return token
        except AuthToken.DoesNotExist:
            return None