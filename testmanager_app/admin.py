from __future__ import annotations
from typing import Any
from django.contrib import admin
from core.models import Project, Module, TestExecution
from testmanager_app.models import TestReport, AuthToken, ApiRequest, RequestCollection, FeatureTestCase


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


@admin.register(TestExecution)
class TestExecutionAdmin(admin.ModelAdmin):
    list_display = ['executed_by', 'status', 'executed_at']
    list_filter = ['status', 'executed_by', 'executed_at']
    search_fields = ['actual_result', 'notes']
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
    
    def key_short(self, obj: AuthToken) -> str:
        """显示token的前8个字符"""
        return f"{obj.key[:8]}..." if obj.key else '-'
    key_short.short_description = 'Token'  # type: ignore[attr-defined]
    
    def is_expired_display(self, obj: AuthToken) -> str:
        """显示是否过期"""
        return '是' if obj.is_expired() else '否'
    is_expired_display.short_description = '是否过期'  # type: ignore[attr-defined]


@admin.register(ApiRequest)
class ApiRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'method', 'url', 'created_at']
    list_filter = ['project', 'method', 'created_at']
    search_fields = ['name', 'url', 'description']
    ordering = ['project', '-created_at']


@admin.register(RequestCollection)
class RequestCollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'execution_mode', 'created_at']
    list_filter = ['project', 'execution_mode', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-created_at']


@admin.register(FeatureTestCase)
class FeatureTestCaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'is_passed', 'version', 'created_at']
    list_filter = ['project', 'is_passed', 'created_at']
    search_fields = ['title', 'steps', 'expected_result']
    ordering = ['-created_at']