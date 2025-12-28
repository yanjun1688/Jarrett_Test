"""
用户相关工具函数
提供统一的用户角色查询接口，消除代码重复
支持缓存优化，减少数据库查询
"""

from django.contrib.auth.models import User
from testmanager_app.models import Role
from testmanager_app.serializers import RoleSerializer
from testmanager_app.utils.cache_helper import (
    get_cached_user_roles,
    cache_user_roles,
    invalidate_user_roles
)
import logging

logger = logging.getLogger(__name__)


def get_user_roles_qs(user: User, use_cache=True):
    """
    获取用户的角色查询集

    Args:
        user: 用户对象
        use_cache: 是否使用缓存，默认True

    Returns:
        QuerySet: 角色查询集（如果没有用户则返回空查询集）
    """
    if not user or not user.is_authenticated:
        return Role.objects.none()
    
    # 尝试从缓存获取角色ID列表
    if use_cache:
        cached_role_ids = get_cached_user_roles(user.id)
        if cached_role_ids is not None:
            logger.debug(f"User roles cache hit: user_id={user.id}")
            return Role.objects.filter(id__in=cached_role_ids)
    
    # 缓存未命中，查询数据库
    roles_qs = Role.objects.filter(user_links__user=user)
    
    # 缓存角色ID列表（10分钟）
    if use_cache:
        role_ids = list(roles_qs.values_list('id', flat=True))
        cache_user_roles(user.id, role_ids, timeout=600)
        logger.debug(f"User roles cached: user_id={user.id}")
    
    return roles_qs


def get_user_roles_data(user: User, serializer_context=None, use_cache=True):
    """
    获取用户的角色序列化数据

    Args:
        user: 用户对象
        serializer_context: 序列化上下文
        use_cache: 是否使用缓存，默认True

    Returns:
        list: 角色数据列表（已序列化）
    """
    roles = get_user_roles_qs(user, use_cache=use_cache)
    return RoleSerializer(roles, many=True, context=serializer_context).data


def get_user_role_ids(user: User):
    """
    获取用户的角色ID列表

    Args:
        user: 用户对象

    Returns:
        list: 角色ID列表
    """
    return list(get_user_roles_qs(user).values_list('id', flat=True))


def check_user_permissions(user: User, request_method: str, use_cache=True):
    """
    检查用户权限

    Args:
        user: 用户对象
        request_method: HTTP请求方法
        use_cache: 是否使用缓存，默认True

    Returns:
        dict: 权限检查结果，包含以下字段：
            - role_count: 角色数量
            - has_crud: 是否有CRUD权限
            - has_view: 是否有查看权限
            - can_access: 是否可以访问
    """
    from rest_framework.permissions import SAFE_METHODS
    from testmanager_app.utils.cache_helper import (
        get_cached_user_permissions,
        cache_user_permissions
    )

    # 尝试从缓存获取
    if use_cache:
        cached_permissions = get_cached_user_permissions(user.id, request_method)
        if cached_permissions is not None:
            logger.debug(f"User permissions cache hit: user_id={user.id}, method={request_method}")
            return cached_permissions

    roles_qs = get_user_roles_qs(user, use_cache=use_cache)

    has_crud = roles_qs.filter(permission='crud').exists()
    has_view = roles_qs.filter(permission='view').exists()
    role_count = roles_qs.count()

    # 权限检查逻辑
    can_access = False
    if user.is_superuser:
        can_access = True
    elif role_count > 0:
        if has_crud:
            can_access = True
        elif has_view and request_method in SAFE_METHODS:
            can_access = True

    result = {
        'role_count': role_count,
        'has_crud': has_crud,
        'has_view': has_view,
        'can_access': can_access,
    }
    
    # 存入缓存（5分钟）
    if use_cache:
        cache_user_permissions(user.id, request_method, result, timeout=300)
        logger.debug(f"User permissions cached: user_id={user.id}, method={request_method}")
    
    return result
