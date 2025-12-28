"""
权限控制模块

提供基于角色的权限控制功能
支持缓存优化，减少数据库查询

创建时间: 2024-11-24
"""
from rest_framework import permissions
from testmanager_app.utils.user_utils import get_user_roles_qs
import logging

logger = logging.getLogger(__name__)


class RoleBasedPermission(permissions.BasePermission):
    """
    基于角色的权限控制
    
    设计理念：
    - admin用户自动拥有所有crud权限（无需分配角色）
    - 其他用户通过角色来控制权限
    - view 权限: 只能读取 (GET, HEAD, OPTIONS)
    - crud 权限: 可以增删改查
    
    优化：使用缓存的用户角色查询，减少数据库访问
    """

    def has_permission(self, request, view):
        # 允许访问登录接口
        if request.path.startswith('/api/auth/login/') or request.path.startswith('/api/auth/debug/'):
            return True

        # 检查是否已认证
        if not request.user or not request.user.is_authenticated:
            return False

        # admin用户自动拥有所有权限
        if request.user.username == 'admin':
            return True

        # 使用缓存的用户角色查询（优化：减少数据库查询）
        user_roles_qs = get_user_roles_qs(request.user, use_cache=True)
        user_roles = list(user_roles_qs)

        # 如果用户没有任何角色，拒绝访问（admin除外）
        if not user_roles:
            logger.warning(f"User {request.user.username} has no roles assigned")
            return False

        # 从查询结果中提取权限（内存操作，无需额外数据库查询）
        permissions_set = {role.permission for role in user_roles}

        # 有 crud 权限允许所有操作
        if 'crud' in permissions_set:
            return True

        # 有 view 权限只允许读取操作
        if 'view' in permissions_set:
            return request.method in permissions.SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        """对象级别的权限检查"""
        return self.has_permission(request, view)