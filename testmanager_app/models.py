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

    class Source(models.TextChoices):
        CHATBOT = 'chatbot', 'Chatbot生成'
        MANUAL_UPLOAD = 'manual_upload', '手动上传'
        MANUAL_CREATE = 'manual_create', '手动创建'

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
    
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL_CREATE,
        verbose_name='来源',
        db_index=True
    )

    class Meta(TypedModelMeta):
        verbose_name = '测试脚本'
        verbose_name_plural = '测试脚本'
        ordering = ['-created_at']
        db_table = 'test_script'
        indexes = [
            models.Index(fields=['project', 'source']),
        ]

    def __str__(self) -> str:
        return self.name


class ScriptExecution(models.Model):
    """脚本执行记录模型

    DEPRECATED: 2026-04-21
    请使用 TestExecution (test_type='script') 替代。
    此模型保留用于向后兼容和历史数据查询。
    """
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
    executor: models.ForeignKey[User | None, User | None] = models.ForeignKey(
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
    started_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    finished_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    duration: models.DurationField[Optional[timedelta], Optional[timedelta]] = models.DurationField(null=True, blank=True, verbose_name='执行耗时')
    
    class Meta(TypedModelMeta):
        verbose_name = '脚本执行记录'
        verbose_name_plural = '脚本执行记录'
        ordering = ['-started_at']
        db_table = 'script_execution'
    
    def __str__(self) -> str:
        return f"{self.script.name} - {self.get_status_display()}"

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
    created_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
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
    is_critical: models.BooleanField[bool, bool] = models.BooleanField(
        default=False,
        verbose_name='是否关键断言',
        help_text='关键断言失败时整个测试标记为失败',
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta(TypedModelMeta):
        verbose_name = 'API断言'
        verbose_name_plural = 'API断言'
        ordering = ['created_at']
        db_table = 'api_assertion'
    
    def __str__(self) -> str:
        return f"{self.api_request.name} - {self.get_assertion_type_display()}"
    
    def clean(self) -> None:
        """模型级别的验证：字段路径条件必填"""
        if self.assertion_type in ['response_body_field', 'response_header_field']:
            if not self.field_path or not self.field_path.strip():
                raise ValidationError({
                    'field_path': f'当断言类型为"{self.get_assertion_type_display()}"时，字段路径为必填项'
                })


class RequestCollection(models.Model):
    """
    请求集合模型
    
    DEPRECATED: 2026-04-15
    请使用 PressureTestConfig 替代
    保留原因：兼容现有数据，观察期后删除
    """
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
    created_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
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
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """保存时输出废弃警告"""
        import warnings
        warnings.warn(
            "RequestCollection is deprecated. Use PressureTestConfig instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().save(*args, **kwargs)


class CollectionRequest(models.Model):
    """
    请求集合与API请求的关联表（支持排序和配置）
    
    DEPRECATED: 2026-04-15
    请使用 PressureTestRequest 替代
    保留原因：兼容现有数据，观察期后删除
    """
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
    """
    集合执行记录模型
    
    DEPRECATED: 2026-04-15
    请使用 PressureTestExecution 替代
    保留原因：兼容现有数据，观察期后删除
    """
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
    executor: models.ForeignKey[User | None, User | None] = models.ForeignKey(
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
    started_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    finished_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    duration: models.DurationField[Optional[timedelta], Optional[timedelta]] = models.DurationField(null=True, blank=True, verbose_name='执行耗时')
    
    class Meta(TypedModelMeta):
        verbose_name = '集合执行记录'
        verbose_name_plural = '集合执行记录'
        ordering = ['-started_at']
        db_table = 'collection_execution'
    
    def __str__(self) -> str:
        return f"{self.collection.name} - {self.get_status_display()}"

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
    created_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feature_test_cases',
        verbose_name='创建人'
    )
    pre_steps: models.TextField[str, str] = models.TextField(blank=True, verbose_name='前置步骤')
    steps: models.TextField[str, str] = models.TextField(verbose_name='操作步骤')
    expected_result: models.TextField[str, str] = models.TextField(blank=True, verbose_name='预期结果')
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


class PressureTestConfig(models.Model):
    """压测配置 - 专用于单接口压力测试
    
    支持三种压测模式：
    - instant: 瞬时并发（同时发起N个请求）
    - sustained: 持续并发（每秒X个，持续Y秒）
    - batch: 分批并发（每批N个，间隔T秒）
    """
    PRESSURE_MODE_CHOICES: List[tuple[str, str]] = [
        ('instant', '瞬时并发'),
        ('sustained', '持续并发'),
        ('batch', '分批并发'),
    ]

    # 基础信息
    name: models.CharField[str, str] = models.CharField(max_length=100, verbose_name='配置名称')
    description: models.TextField[str, str] = models.TextField(blank=True, verbose_name='配置描述')
    project: models.ForeignKey[Project, Project] = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='pressure_test_configs',
        verbose_name='所属项目'
    )
    created_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pressure_test_configs',
        verbose_name='创建人'
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    # 关联请求（单选，简化设计）
    api_request: models.ForeignKey[ApiRequest, ApiRequest] = models.ForeignKey(
        ApiRequest,
        on_delete=models.CASCADE,
        related_name='pressure_test_configs',
        verbose_name='测试请求'
    )

    # 压测模式
    pressure_mode: models.CharField[str, str] = models.CharField(
        max_length=20,
        choices=PRESSURE_MODE_CHOICES,
        verbose_name='压测模式'
    )

    # 瞬时并发参数
    request_count: models.IntegerField[int, int] = models.IntegerField(
        default=100,
        validators=[MaxValueValidator(1000)],
        verbose_name='请求次数',
        help_text='瞬时并发模式：总请求数（最大1000）'
    )

    # 持续并发参数
    rate_per_second: models.IntegerField[int, int] = models.IntegerField(
        default=10,
        verbose_name='每秒请求数',
        help_text='持续并发模式：每秒发起的请求数'
    )
    duration_seconds: models.IntegerField[int, int] = models.IntegerField(
        default=60,
        verbose_name='持续秒数',
        help_text='持续并发模式：持续执行的秒数'
    )

    # 分批并发参数
    batch_size: models.IntegerField[int, int] = models.IntegerField(
        default=50,
        verbose_name='每批数量',
        help_text='分批并发模式：每批发起的请求数'
    )
    batch_interval: models.IntegerField[int, int] = models.IntegerField(
        default=5,
        verbose_name='批次间隔',
        help_text='分批并发模式：批次之间的间隔（秒）'
    )

    # 通用参数
    max_concurrent: models.IntegerField[int, int] = models.IntegerField(
        default=100,
        validators=[MaxValueValidator(200)],
        verbose_name='最大并发数',
        help_text='同时最多发起的请求数（单机压测建议≤200，最大200）'
    )

    # 可选：服务器监控（P2阶段实现）
    monitor_server: models.BooleanField[bool, bool] = models.BooleanField(
        default=False,
        verbose_name='监控服务器'
    )
    ssh_config: models.JSONField[Optional[Dict[str, Any]], Optional[Dict[str, Any]]] = models.JSONField(
        null=True,
        blank=True,
        verbose_name='SSH配置',
        help_text='JSON格式: {"host": "", "port": 22, "username": "", "password": ""}'
    )

    class Meta(TypedModelMeta):
        verbose_name = '压测配置'
        verbose_name_plural = '压测配置'
        ordering = ['-created_at']
        db_table = 'pressure_test_config'

    def __str__(self) -> str:
        return self.name


class PressureTestExecution(models.Model):
    """压测执行记录 - 包含详细聚合指标"""
    STATUS_CHOICES: List[tuple[str, str]] = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('stopped', '已停止'),
        ('failed', '失败'),
    ]

    # 关联关系
    config: models.ForeignKey[PressureTestConfig, PressureTestConfig] = models.ForeignKey(
        PressureTestConfig,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='压测配置'
    )
    executor: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pressure_test_executions',
        verbose_name='执行人'
    )

    # 状态
    status: models.CharField[str, str] = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='执行状态'
    )

    # 时间记录
    started_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    finished_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    duration_seconds: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True, verbose_name='执行耗时（秒）')

    # 基础统计
    total_requests: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='总请求数')
    success_count: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='成功数')
    failed_count: models.IntegerField[int, int] = models.IntegerField(default=0, verbose_name='失败数')
    error_rate: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True, verbose_name='错误率（%）')

    # 响应时间统计（毫秒）
    min_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True, verbose_name='最小响应时间（ms）')
    max_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True, verbose_name='最大响应时间（ms）')
    avg_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True, verbose_name='平均响应时间（ms）')
    p50_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True, verbose_name='P50响应时间（ms）')
    p90_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True, verbose_name='P90响应时间（ms）')
    p95_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True, verbose_name='P95响应时间（ms）')
    p99_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True, verbose_name='P99响应时间（ms）')

    # 吞吐量
    throughput: models.FloatField[Optional[float], Optional[float]] = models.FloatField(null=True, blank=True, verbose_name='吞吐量（RPS）')

    # 并发统计
    peak_concurrent: models.IntegerField[Optional[int], Optional[int]] = models.IntegerField(null=True, blank=True, verbose_name='峰值并发数')

    # 可选：服务器监控数据
    server_metrics: models.JSONField = models.JSONField(
        null=True,
        blank=True,
        verbose_name='服务器监控数据'
    )

    raw_results: models.JSONField = models.JSONField(
        null=True,
        blank=True,
        verbose_name='原始结果数据',
        help_text='每次请求的详细结果，用于后续分析'
    )

    logs: models.TextField[str, str] = models.TextField(
        blank=True,
        verbose_name='执行日志',
        help_text='压测执行过程的完整日志'
    )

    class Meta(TypedModelMeta):
        verbose_name = '压测执行记录'
        verbose_name_plural = '压测执行记录'
        ordering = ['-started_at']
        db_table = 'pressure_test_execution'

    def __str__(self) -> str:
        return f"{self.config.name} - {self.get_status_display()}"


class AdvancedPressureTestConfig(models.Model):
    """高级压测配置 - 基于Locust的分布式压测
    
    支持事务编排、分布式Worker、详细的统计报告
    """
    
    # 提取器类型选择
    EXTRACTOR_TYPE_CHOICES: List[tuple[str, str]] = [
        ('json_path', 'JSON Path'),
        ('regex', '正则表达式'),
        ('xpath', 'XPath'),
        ('header', '响应头'),
        ('status_code', '状态码'),
        ('response_time', '响应时间'),
    ]
    
    # 基础信息
    name: models.CharField[str, str] = models.CharField(
        max_length=100, 
        verbose_name='配置名称'
    )
    description: models.TextField[str, str] = models.TextField(
        blank=True, 
        verbose_name='配置描述'
    )
    project: models.ForeignKey[Any, Any] = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='advanced_pressure_test_configs',
        verbose_name='所属项目'
    )
    created_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='advanced_pressure_test_configs',
        verbose_name='创建人'
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='创建时间'
    )
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now=True, 
        verbose_name='更新时间'
    )
    
    # 压测场景定义（支持事务编排）
    scenario: models.JSONField[Dict[str, Any], Dict[str, Any]] = models.JSONField(
        verbose_name='测试场景',
        help_text='''JSON格式定义测试场景和步骤:
        {
            "scenario_name": "场景名称",
            "steps": [
                {
                    "name": "步骤名称",
                    "api_request_id": 1,
                    "weight": 1,
                    "extractors": [
                        {"name": "token", "type": "json_path", "expression": "$.data.token"}
                    ],
                    "headers": {"Authorization": "Bearer ${token}"},
                    "think_time": {"min": 1, "max": 3}
                }
            ]
        }'''
    )
    
    # Locust参数
    host: models.URLField[str, str] = models.URLField(
        verbose_name='目标服务器地址',
        help_text='压测目标的基础URL，例如: http://localhost:8080'
    )
    user_count: models.IntegerField[int, int] = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
        verbose_name='并发用户数',
        help_text='同时模拟的用户数量'
    )
    spawn_rate: models.IntegerField[int, int] = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        verbose_name='启动速率',
        help_text='每秒启动的用户数'
    )
    duration_seconds: models.IntegerField[int, int] = models.IntegerField(
        default=60,
        validators=[MinValueValidator(1), MaxValueValidator(3600)],
        verbose_name='持续时间(秒)',
        help_text='压测持续的最大秒数'
    )
    
    # 分布式配置
    use_distributed: models.BooleanField[bool, bool] = models.BooleanField(
        default=False,
        verbose_name='启用分布式',
        help_text='是否启用分布式Worker模式'
    )
    worker_count: models.IntegerField[int, int] = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name='Worker数量',
        help_text='分布式模式下的Worker节点数量'
    )
    
    # Web UI配置
    web_ui_port: models.IntegerField[int, int] = models.IntegerField(
        default=18089,
        verbose_name='Web UI端口',
        help_text='Locust Web UI访问端口'
    )
    enable_web_ui: models.BooleanField[bool, bool] = models.BooleanField(
        default=True,
        verbose_name='启用Web UI',
        help_text='是否启动Locust原生Web界面'
    )
    
    # 高级选项
    tags: models.JSONField[List[str], List[str]] = models.JSONField(
        default=list,
        blank=True,
        verbose_name='任务标签',
        help_text='要运行的任务标签列表'
    )
    exclude_tags: models.JSONField[List[str], List[str]] = models.JSONField(
        default=list,
        blank=True,
        verbose_name='排除标签',
        help_text='要排除的任务标签列表'
    )
    
    class Meta(TypedModelMeta):
        verbose_name = '高级压测配置'
        verbose_name_plural = '高级压测配置'
        ordering = ['-created_at']
        db_table = 'advanced_pressure_test_config'
    
    def __str__(self) -> str:
        return self.name


class AdvancedPressureTestExecution(models.Model):
    """高级压测执行记录 - 存储Locust执行结果"""
    
    STATUS_CHOICES: List[tuple[str, str]] = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('stopped', '已停止'),
        ('failed', '失败'),
    ]
    
    # 关联关系
    config: models.ForeignKey[AdvancedPressureTestConfig, AdvancedPressureTestConfig] = models.ForeignKey(
        AdvancedPressureTestConfig,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='压测配置'
    )
    executor: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='advanced_pressure_test_executions',
        verbose_name='执行人'
    )
    
    # 执行状态
    status: models.CharField[str, str] = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='执行状态'
    )
    
    # 时间记录
    started_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='开始时间'
    )
    finished_at: models.DateTimeField[Optional[datetime], Optional[datetime]] = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='完成时间'
    )
    duration_seconds: models.FloatField[Optional[float], Optional[float]] = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name='执行耗时(秒)'
    )
    
    # 基础统计
    total_requests: models.IntegerField[int, int] = models.IntegerField(
        default=0, 
        verbose_name='总请求数'
    )
    success_count: models.IntegerField[int, int] = models.IntegerField(
        default=0, 
        verbose_name='成功数'
    )
    failed_count: models.IntegerField[int, int] = models.IntegerField(
        default=0, 
        verbose_name='失败数'
    )
    error_rate: models.FloatField[Optional[float], Optional[float]] = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name='错误率(%)'
    )
    
    # 响应时间统计（毫秒）
    min_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name='最小响应时间(ms)'
    )
    max_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name='最大响应时间(ms)'
    )
    avg_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name='平均响应时间(ms)'
    )
    p50_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name='P50响应时间(ms)'
    )
    p90_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name='P90响应时间(ms)'
    )
    p95_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name='P95响应时间(ms)'
    )
    p99_response_time: models.FloatField[Optional[float], Optional[float]] = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name='P99响应时间(ms)'
    )
    
    # 吞吐量
    throughput: models.FloatField[Optional[float], Optional[float]] = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name='吞吐量(RPS)'
    )
    
    # 并发统计
    current_users: models.IntegerField[Optional[int], Optional[int]] = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name='当前用户数'
    )
    peak_users: models.IntegerField[Optional[int], Optional[int]] = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name='峰值用户数'
    )
    
    # Worker信息（分布式）
    worker_count: models.IntegerField[Optional[int], Optional[int]] = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name='Worker数量'
    )
    worker_status: models.JSONField[Optional[Dict[str, Any]], Optional[Dict[str, Any]]] = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name='Worker状态',
        help_text='Worker节点状态信息'
    )
    
    # 报告存储
    report_html: models.TextField[Optional[str], Optional[str]] = models.TextField(
        null=True, 
        blank=True, 
        verbose_name='HTML报告内容'
    )
    raw_results: models.JSONField[Optional[List[Dict[str, Any]]], Optional[List[Dict[str, Any]]]] = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name='原始结果数据',
        help_text='每次请求的详细结果'
    )
    
    # 错误日志
    error_log: models.TextField[Optional[str], Optional[str]] = models.TextField(
        null=True, 
        blank=True, 
        verbose_name='错误日志'
    )

    logs: models.TextField[str, str] = models.TextField(
        blank=True,
        verbose_name='执行日志',
        help_text='高级压测执行过程的完整日志'
    )
    
    class Meta(TypedModelMeta):
        verbose_name = '高级压测执行记录'
        verbose_name_plural = '高级压测执行记录'
        ordering = ['-started_at']
        db_table = 'advanced_pressure_test_execution'
    
    def __str__(self) -> str:
        return f"{self.config.name} - {self.get_status_display()}"
