"""
UI测试应用的Admin配置
"""
from __future__ import annotations
from typing import Any
from django.contrib import admin
from django.http import HttpRequest
from .models import (
    UITestScript,
    UITestExecution,
)


@admin.register(UITestScript)
class UITestScriptAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'created_by', 'browser_type', 'is_active', 'created_at']
    list_filter = ['is_active', 'browser_type', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'project', 'created_by', 'is_active')
        }),
        ('浏览器配置', {
            'fields': ('browser_type', 'headless', 'viewport_width', 'viewport_height', 'timeout')
        }),
        ('Actions配置', {
            'fields': ('actions',),
            'description': 'Actions列表（JSON格式）'
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UITestExecution)
class UITestExecutionAdmin(admin.ModelAdmin):
    list_display = ['script', 'executed_by', 'status', 'started_at', 'completed_at', 'duration']
    list_filter = ['status', 'started_at']
    search_fields = ['script__name', 'error_message']
    readonly_fields = ['script', 'executed_by', 'status', 'started_at', 'completed_at',
                       'duration', 'result_summary', 'error_message', 'screenshots', 'execution_log', 'created_at']
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
