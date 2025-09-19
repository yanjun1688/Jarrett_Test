from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator


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


class TestExecution(models.Model):
    """测试执行记录模型"""
    STATUS_CHOICES = [
        ('passed', '通过'),
        ('failed', '失败'),
        ('blocked', '阻塞'),
        ('skipped', '跳过'),
    ]
    
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='executions', verbose_name='测试用例')
    executor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='执行人')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, verbose_name='执行结果')
    actual_result = models.TextField(blank=True, verbose_name='实际结果')
    comments = models.TextField(blank=True, verbose_name='备注')
    executed_at = models.DateTimeField(default=timezone.now, verbose_name='执行时间')
    execution_duration = models.DurationField(null=True, blank=True, verbose_name='执行耗时')
    
    class Meta:
        verbose_name = '测试执行记录'
        verbose_name_plural = '测试执行记录'
        ordering = ['-executed_at']
    
    def __str__(self):
        return f"{self.testcase.title} - {self.get_status_display()}"


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
    """测试脚本模型"""
    SCRIPT_TYPE_CHOICES = [
        ('python', 'Python脚本'),
        ('api', 'API测试'),
        ('selenium', 'Selenium测试'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='脚本名称')
    description = models.TextField(blank=True, verbose_name='脚本描述')
    script_type = models.CharField(max_length=20, choices=SCRIPT_TYPE_CHOICES, default='python', verbose_name='脚本类型')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_scripts', verbose_name='所属项目')
    file = models.FileField(
        upload_to='test_scripts/', 
        validators=[FileExtensionValidator(allowed_extensions=['py', 'json', 'txt'])],
        verbose_name='脚本文件'
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='api_requests', verbose_name='所属项目')
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
    """API断言模型"""
    ASSERTION_TYPE_CHOICES = [
        ('status_code', '状态码'),
        ('response_time', '响应时间'),
        ('response_body', '响应体'),
        ('response_header', '响应头'),
    ]
    
    COMPARISON_CHOICES = [
        ('equals', '等于'),
        ('contains', '包含'),
        ('not_contains', '不包含'),
        ('greater_than', '大于'),
        ('less_than', '小于'),
    ]
    
    api_request = models.ForeignKey(ApiRequest, on_delete=models.CASCADE, related_name='assertions', verbose_name='API请求')
    assertion_type = models.CharField(max_length=20, choices=ASSERTION_TYPE_CHOICES, verbose_name='断言类型')
    field = models.CharField(max_length=100, blank=True, verbose_name='字段名')
    comparison = models.CharField(max_length=20, choices=COMPARISON_CHOICES, verbose_name='比较方式')
    expected_value = models.CharField(max_length=200, verbose_name='期望值')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = 'API断言'
        verbose_name_plural = 'API断言'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.api_request.name} - {self.get_assertion_type_display()}"


class RequestCollection(models.Model):
    """请求集合模型"""
    name = models.CharField(max_length=100, verbose_name='集合名称')
    description = models.TextField(blank=True, verbose_name='集合描述')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='request_collections', verbose_name='所属项目')
    requests = models.ManyToManyField(ApiRequest, blank=True, verbose_name='API请求')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '请求集合'
        verbose_name_plural = '请求集合'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


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
    def pass_rate(self):
        """通过率"""
        if self.total_requests == 0:
            return 0
        return round((self.passed_requests / self.total_requests) * 100, 2)
