"""
权限控制模块

简化版权限控制：只有 superuser 才能访问 API
"""

from rest_framework import permissions


class IsSuperUser(permissions.BasePermission):
    """
    简化权限控制：只有 superuser 才能访问
    
    - 登录接口允许所有人访问
    - 其他接口只允许 superuser 访问
    """

    def has_permission(self, request, view):
        if request.path.startswith('/api/auth/login/') or request.path.startswith('/api/auth/debug/'):
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)