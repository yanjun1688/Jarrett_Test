from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.db.models import Manager, QuerySet, Count, Q


class Project(models.Model):
    """项目模型"""
    name = models.CharField(max_length=100, verbose_name='项目名称')
    description = models.TextField(blank=True, verbose_name='项目描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    
    class Meta:
        verbose_name = '项目'
        verbose_name_plural = '项目'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class Module(models.Model):
    """模块模型"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='modules', verbose_name='所属项目')
    name = models.CharField(max_length=100, verbose_name='模块名称')
    description = models.TextField(blank=True, verbose_name='模块描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '模块'
        verbose_name_plural = '模块'
        ordering = ['name']
        unique_together = ['project', 'name']
    
    def __str__(self):
        return f"{self.project.name} - {self.name}"


class TestCase(models.Model):
    """测试用例模型"""
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '紧急'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='用例标题')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='testcases', verbose_name='所属项目')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='testcases', verbose_name='所属模块')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name='优先级')
    precondition = models.TextField(blank=True, verbose_name='前置条件')
    steps = models.TextField(verbose_name='测试步骤')
    expected_result = models.TextField(verbose_name='预期结果')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '测试用例'
        verbose_name_plural = '测试用例'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class TestExecutionQuerySet(QuerySet):
    """测试执行记录的自定义 QuerySet"""

    def by_project(self, project):
        """按项目过滤"""
        return self.filter(
            Q(testcase__project=project) | Q(api_request__project=project)
        )

    def by_date_range(self, start_date, end_date):
        """按时间范围过滤"""
        return self.filter(executed_at__range=[start_date, end_date])

    def aggregate_stats(self):
        """聚合统计执行数据"""
        return self.aggregate(
            total_executions=Count('id'),
            passed_executions=Count('id', filter=Q(status='passed')),
            failed_executions=Count('id', filter=Q(status='failed')),
            blocked_executions=Count('id', filter=Q(status='blocked')),
            skipped_executions=Count('id', filter=Q(status='skipped')),
            total_cases=Count('testcase', distinct=True, filter=Q(testcase__isnull=False)) +
                        Count('api_request', distinct=True, filter=Q(api_request__isnull=False))
        )


class TestExecutionManager(Manager):
    """测试执行记录的自定义 Manager"""

    def get_queryset(self):
        return TestExecutionQuerySet(self.model, using=self._db)

    def by_project(self, project):
        return self.get_queryset().by_project(project)

    def by_project_and_date_range(self, project, start_date, end_date):
        return self.get_queryset().by_project(project).by_date_range(start_date, end_date)


class TestExecution(models.Model):
    """测试执行记录模型"""
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('passed', '通过'),
        ('failed', '失败'),
        ('blocked', '阻塞'),
        ('skipped', '跳过'),
    ]

    TEST_TYPE_CHOICES = [
        ('testcase', '功能测试用例'),
        ('api', 'API测试'),
    ]

    test_type = models.CharField(max_length=10, choices=TEST_TYPE_CHOICES, default='testcase', verbose_name='测试类型')
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='executions', verbose_name='测试用例', db_index=True, null=True, blank=True)
    api_request = models.ForeignKey('ApiRequest', on_delete=models.CASCADE, related_name='executions', verbose_name='API请求', db_index=True, null=True, blank=True)

    # 新增：集合执行关联
    collection_execution = models.ForeignKey(
        'CollectionExecution',
        on_delete=models.CASCADE,
        related_name='api_executions',
        null=True,
        blank=True,
        verbose_name='所属集合执行'
    )

    executor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='执行人')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, verbose_name='执行结果', db_index=True)
    actual_result = models.TextField(blank=True, verbose_name='实际结果')
    comments = models.TextField(blank=True, verbose_name='备注')
    executed_at = models.DateTimeField(default=timezone.now, verbose_name='执行时间', db_index=True)
    execution_duration = models.DurationField(null=True, blank=True, verbose_name='执行耗时')
    api_response_data = models.JSONField(null=True, blank=True, verbose_name='API响应数据')
    api_logs = models.TextField(blank=True, verbose_name='API执行日志')

    class Meta:
        verbose_name = '测试执行记录'
        verbose_name_plural = '测试执行记录'
        ordering = ['-executed_at']

    objects = TestExecutionManager()  # 使用自定义 Manager

    def __str__(self):
        if self.test_type == 'api' and self.api_request:
            return f"{self.api_request.name} - {self.get_status_display()}"
        elif self.testcase:
            return f"{self.testcase.title} - {self.get_status_display()}"
        return f"未知测试 - {self.get_status_display()}"


class TestReport(models.Model):
    """测试报告模型"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports', verbose_name='所属项目')
    name = models.CharField(max_length=100, verbose_name='报告名称')
    description = models.TextField(blank=True, verbose_name='报告描述')
    start_date = models.DateTimeField(verbose_name='开始时间')
    end_date = models.DateTimeField(verbose_name='结束时间')
    total_cases = models.IntegerField(default=0, verbose_name='总用例数')
    passed_cases = models.IntegerField(default=0, verbose_name='通过用例数')
    failed_cases = models.IntegerField(default=0, verbose_name='失败用例数')
    blocked_cases = models.IntegerField(default=0, verbose_name='阻塞用例数')
    skipped_cases = models.IntegerField(default=0, verbose_name='跳过用例数')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '测试报告'
        verbose_name_plural = '测试报告'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def pass_rate(self):
        """通过率"""
        if self.total_cases == 0:
            return 0
        return round((self.passed_cases / self.total_cases) * 100, 2)


class TestScript(models.Model):
    """测试脚本模型 - 简化为API配置工具"""
    SCRIPT_TYPE_CHOICES = [
        ('api', 'API测试'),
        ('yaml', 'YAML配置'),
    ]

    name = models.CharField(max_length=100, verbose_name='脚本名称')
    description = models.TextField(blank=True, verbose_name='脚本描述')
    script_type = models.CharField(max_length=20, choices=SCRIPT_TYPE_CHOICES, default='api', verbose_name='脚本类型')
    content = models.TextField(verbose_name='脚本内容', help_text='YAML格式的API测试配置')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_scripts', verbose_name='所属项目')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta:
        verbose_name = '测试脚本'
        verbose_name_plural = '测试脚本'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ScriptExecution(models.Model):
    """脚本执行记录模型"""
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
    ]
    
    script = models.ForeignKey(TestScript, on_delete=models.CASCADE, related_name='executions', verbose_name='测试脚本')
    executor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='执行人')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='执行状态')
    output = models.TextField(blank=True, verbose_name='执行输出')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    duration = models.DurationField(null=True, blank=True, verbose_name='执行耗时')
    
    class Meta:
        verbose_name = '脚本执行记录'
        verbose_name_plural = '脚本执行记录'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.script.name} - {self.get_status_display()}"

    @property
    def calculated_duration(self):
        """计算执行耗时 - 优先使用 duration 字段，否则根据起止时间计算"""
        if self.duration:
            return self.duration
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None


class ApiRequest(models.Model):
    """API请求模型"""
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ]

    name = models.CharField(max_length=100, verbose_name='请求名称')
    description = models.TextField(blank=True, verbose_name='请求描述')
    url = models.URLField(verbose_name='请求URL')
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='GET', verbose_name='请求方法')
    headers = models.TextField(blank=True, verbose_name='请求头')
    body = models.TextField(blank=True, verbose_name='请求体')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='api_requests', verbose_name='所属项目', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'API请求'
        verbose_name_plural = 'API请求'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class ApiAssertion(models.Model):
    """API断言模型
    
    设计理念：以「值定位」为核心，而不是以「响应类型」为核心
    - HTTP状态码只是一个特殊的值来源
    - 响应体字段断言才是接口测试的主战场
    - 一个断言只表达一个判断：一个值路径 + 一个比较方式 + 一个期望结果
    """
    ASSERTION_TYPE_CHOICES = [
        ('status_code', '状态码'),
        ('response_time', '响应时间'),
        ('response_body_field', '响应体字段'),  # 修改：从response_body改为response_body_field
        ('response_header_field', '响应头字段'),  # 修改：从response_header改为response_header_field
    ]
    
    COMPARISON_CHOICES = [
        ('equals', '等于'),
        ('contains', '包含'),
        ('not_contains', '不包含'),
        ('greater_than', '大于'),
        ('less_than', '小于'),
    ]
    
    api_request = models.ForeignKey(ApiRequest, on_delete=models.CASCADE, related_name='assertions', verbose_name='API请求')
    assertion_type = models.CharField(max_length=30, choices=ASSERTION_TYPE_CHOICES, verbose_name='断言类型')
    # 字段路径：用于精确定位某个值（如：data.id、data.list[0].name 或 $.data.id）
    # 支持点号路径（data.id）和JSONPath（$.data.id）两种格式
    field_path = models.CharField(max_length=200, blank=True, verbose_name='字段路径')
    comparison = models.CharField(max_length=20, choices=COMPARISON_CHOICES, verbose_name='比较方式')
    expected_value = models.CharField(max_length=200, verbose_name='期望值')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = 'API断言'
        verbose_name_plural = 'API断言'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.api_request.name} - {self.get_assertion_type_display()}"
    
    def clean(self):
        """模型级别的验证：字段路径条件必填"""
        from django.core.exceptions import ValidationError
        
        # 当断言类型为响应体字段或响应头字段时，字段路径为必填
        if self.assertion_type in ['response_body_field', 'response_header_field']:
            if not self.field_path or not self.field_path.strip():
                raise ValidationError({
                    'field_path': f'当断言类型为"{self.get_assertion_type_display()}"时，字段路径为必填项'
                })


class RequestCollection(models.Model):
    """请求集合模型"""
    EXECUTION_MODE_CHOICES = [
        ('concurrent', '并发执行'),
        ('sequential', '顺序执行'),
        ('chain', '链式执行（支持变量传递）'),
    ]

    name = models.CharField(max_length=100, verbose_name='集合名称')
    description = models.TextField(blank=True, verbose_name='集合描述')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='request_collections', verbose_name='所属项目', null=True, blank=True)  # 修复：允许为空
    execution_mode = models.CharField(max_length=20, choices=EXECUTION_MODE_CHOICES, default='concurrent', verbose_name='执行模式')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '请求集合'
        verbose_name_plural = '请求集合'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class CollectionRequest(models.Model):
    """请求集合与API请求的关联表（支持排序和配置）"""
    REQUEST_TYPE_CHOICES = [
        ('normal', '正常请求'),
        ('setup', 'Setup前置请求'),
        ('teardown', 'Teardown后置请求'),
    ]
    
    collection = models.ForeignKey(RequestCollection, on_delete=models.CASCADE, related_name='collection_requests', verbose_name='请求集合')
    api_request = models.ForeignKey('ApiRequest', on_delete=models.CASCADE, related_name='collection_requests', verbose_name='API请求')
    order_index = models.IntegerField(default=0, verbose_name='执行顺序', db_index=True)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES, default='normal', verbose_name='请求类型',
        help_text='Setup: 在正常请求前执行；Teardown: 在正常请求后执行（无论成功失败）')
    stop_on_failure = models.BooleanField(default=True, verbose_name='失败时停止')
    extract_rules = models.JSONField(null=True, blank=True, verbose_name='变量提取规则',
        help_text='JSON格式: [{"name": "var_name", "jsonpath": "$.data.id"}]')
    request_count = models.IntegerField(default=1, verbose_name='请求次数', validators=[
        MinValueValidator(1, '请求次数必须大于0'),
        MaxValueValidator(1000, '单次请求次数不能超过1000')
    ], help_text='该请求在集合中的执行次数')

    class Meta:
        verbose_name = '集合请求关联'
        verbose_name_plural = '集合请求关联'
        ordering = ['order_index']
        unique_together = ['collection', 'api_request']

    def __str__(self):
        return f"{self.collection.name} - {self.api_request.name} (#{self.order_index})"


class CollectionExecution(models.Model):
    """集合执行记录模型"""
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
    ]
    
    collection = models.ForeignKey(RequestCollection, on_delete=models.CASCADE, related_name='executions', verbose_name='请求集合')
    executor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='执行人')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='执行状态')
    total_requests = models.IntegerField(default=0, verbose_name='总请求数')
    passed_requests = models.IntegerField(default=0, verbose_name='通过请求数')
    failed_requests = models.IntegerField(default=0, verbose_name='失败请求数')
    output = models.TextField(blank=True, verbose_name='执行输出')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    duration = models.DurationField(null=True, blank=True, verbose_name='执行耗时')
    
    class Meta:
        verbose_name = '集合执行记录'
        verbose_name_plural = '集合执行记录'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.collection.name} - {self.get_status_display()}"

    @property
    def calculated_duration(self):
        """计算执行耗时 - 优先使用 duration 字段，否则根据起止时间计算"""
        if self.duration:
            return self.duration
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None

    @property
    def pass_rate(self):
        """通过率"""
        if self.total_requests == 0:
            return 0
        return round((self.passed_requests / self.total_requests) * 100, 2)


class FeatureTestCase(models.Model):
    """功能测试用例（MVP）
    所有业务字段均为纯文本，不做权限控制
    """
    title = models.CharField(max_length=200, verbose_name='测试标题')
    pre_steps = models.TextField(blank=True, verbose_name='前置步骤')
    steps = models.TextField(verbose_name='操作步骤')
    expected_result = models.TextField(verbose_name='预期结果')
    actual_result = models.TextField(blank=True, verbose_name='实际结果')
    to_confirm = models.TextField(blank=True, verbose_name='待确定')
    is_passed = models.BooleanField(null=True, blank=True, verbose_name='是否通过')
    version = models.CharField(max_length=50, blank=True, verbose_name='版本号')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '功能测试用例'
        verbose_name_plural = '功能测试用例'
        ordering = ['-created_at']

    def __str__(self):
        return str(self.title)[:50]

class TestResult(models.Model):
    """API测试结果模型"""
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失败'),
    ]

    api_request = models.ForeignKey(ApiRequest, on_delete=models.CASCADE, related_name='test_results', verbose_name='API请求')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, verbose_name='测试结果')
    status_code = models.IntegerField(null=True, blank=True, verbose_name='响应状态码')
    response_time = models.FloatField(null=True, blank=True, verbose_name='响应时间(ms)')
    response_body = models.TextField(blank=True, verbose_name='响应体')
    response_headers = models.TextField(blank=True, verbose_name='响应头')
    assertion_results = models.JSONField(null=True, blank=True, verbose_name='断言结果')
    executed_at = models.DateTimeField(auto_now_add=True, verbose_name='执行时间')

    class Meta:
        verbose_name = 'API测试结果'
        verbose_name_plural = 'API测试结果'
        ordering = ['-executed_at']

    def __str__(self):
        return f"{self.api_request.name} - {self.get_status_display()}"


class Role(models.Model):
    """角色模型 - 定义用户角色和权限"""
    
    PERMISSION_CHOICES = [
        ('view', '仅查看'),
        ('crud', '增删改查'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='角色名称')
    permission = models.CharField(
        max_length=20, 
        choices=PERMISSION_CHOICES, 
        verbose_name='权限类型'
    )
    description = models.TextField(blank=True, verbose_name='角色描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '角色'
        verbose_name_plural = '角色'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class UserRole(models.Model):
    """用户角色关联模型 - 用户和角色的多对多关系"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='role_links',
        verbose_name='用户'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_links',
        verbose_name='角色'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '用户角色关联'
        verbose_name_plural = '用户角色关联'
        unique_together = ['user', 'role']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

    @staticmethod
    def get_user_roles(user):
        """获取用户的所有角色"""
        return Role.objects.filter(user_links__user=user)

    @staticmethod
    def assign_role_to_user(user, role):
        """为用户分配角色"""
        user_role, created = UserRole.objects.get_or_create(user=user, role=role)
        return user_role, created

    @staticmethod
    def remove_role_from_user(user, role):
        """移除用户的角色"""
        try:
            user_role = UserRole.objects.get(user=user, role=role)
            user_role.delete()
            return True
        except UserRole.DoesNotExist:
            return False


class AuthToken(models.Model):
    """自定义Token模型，支持过期时间和多端点登录"""
    key = models.CharField(max_length=100, primary_key=True, verbose_name='Token密钥')
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='auth_tokens',
        verbose_name='用户'
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    expires_at = models.DateTimeField(verbose_name='过期时间')
    last_used = models.DateTimeField(auto_now=True, verbose_name='最后使用时间')
    
    class Meta:
        verbose_name = '认证Token'
        verbose_name_plural = '认证Token'
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.user.username} - {self.key[:8]}..."
    
    def is_expired(self):
        """检查token是否过期"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    @staticmethod
    def generate_key():
        """生成token密钥"""
        import secrets
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create_token(user, expires_in_days=7):
        """创建新的token（支持多端点登录）"""
        from django.utils import timezone
        from datetime import timedelta
        
        # 生成新的token key
        key = AuthToken.generate_key()
        
        # 设置过期时间（默认7天）
        expires_at = timezone.now() + timedelta(days=expires_in_days)
        
        # 创建token
        token = AuthToken.objects.create(
            user=user,
            key=key,
            expires_at=expires_at
        )
        
        return token
    
    @staticmethod
    def refresh_token(token_key):
        """刷新token（延长过期时间）"""
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            token = AuthToken.objects.get(key=token_key)
            if token.is_expired():
                return None
            
            # 延长过期时间（再延长7天）
            token.expires_at = timezone.now() + timedelta(days=7)
            token.save()
            return token
        except AuthToken.DoesNotExist:
            return None
