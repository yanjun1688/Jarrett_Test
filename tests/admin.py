from django.contrib import admin
from .models import Project, Module, TestCase, TestExecution, TestReport


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
