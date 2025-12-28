from django.contrib import admin
from testmanager_app.models import Project, Module, TestCase, TestExecution, TestReport, Role, UserRole, AuthToken


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'permission', 'description']
    list_filter = ['permission']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__username', 'role__name']
    ordering = ['-created_at']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-created_at']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'description', 'created_at']
    list_filter = ['project', 'created_at']
    search_fields = ['name', 'description', 'project__name']
    ordering = ['project', 'name']


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'module', 'priority', 'created_by', 'created_at']
    list_filter = ['project', 'module', 'priority', 'created_at']
    search_fields = ['title', 'steps', 'expected_result']
    ordering = ['-created_at']


@admin.register(TestExecution)
class TestExecutionAdmin(admin.ModelAdmin):
    list_display = ['testcase', 'executor', 'status', 'executed_at']
    list_filter = ['status', 'executor', 'executed_at']
    search_fields = ['testcase__title', 'actual_result', 'comments']
    ordering = ['-executed_at']


@admin.register(TestReport)
class TestReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'total_cases', 'passed_cases', 'pass_rate', 'created_at']
    list_filter = ['project', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-created_at']
    readonly_fields = ['pass_rate']


@admin.register(AuthToken)
class AuthTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'key_short', 'created', 'expires_at', 'last_used', 'is_expired_display']
    list_filter = ['created', 'expires_at', 'last_used']
    search_fields = ['user__username', 'key']
    ordering = ['-created']
    readonly_fields = ['key', 'created', 'last_used']
    
    def key_short(self, obj):
        """显示token的前8个字符"""
        return f"{obj.key[:8]}..." if obj.key else '-'
    key_short.short_description = 'Token'
    
    def is_expired_display(self, obj):
        """显示是否过期"""
        return '是' if obj.is_expired() else '否'
    is_expired_display.short_description = '是否过期'
