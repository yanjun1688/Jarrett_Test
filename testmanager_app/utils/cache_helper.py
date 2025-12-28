"""
缓存工具模块
提供统一的缓存操作接口，简化缓存使用

缓存策略：
- 项目统计：5分钟（数据变化不频繁）
- 用户角色：10分钟（相对稳定）
- 权限检查：5分钟（相对稳定）
- 项目列表：2分钟（可能变化）
"""

from django.core.cache import cache
from functools import wraps
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


# 缓存键前缀
CACHE_KEY_PREFIX = {
    'project_stats': 'project_stats',
    'user_roles': 'user_roles',
    'user_permissions': 'user_permissions',
    'project_list': 'project_list',
    'report_data': 'report_data',
}


def get_cache_key(prefix, *args, **kwargs):
    """
    生成缓存键
    
    Args:
        prefix: 缓存键前缀
        *args: 位置参数
        **kwargs: 关键字参数
    
    Returns:
        str: 缓存键
    """
    # 将参数序列化为字符串
    key_parts = [prefix]
    
    if args:
        key_parts.append(':'.join(str(arg) for arg in args))
    
    if kwargs:
        # 对kwargs排序以确保一致性
        sorted_kwargs = sorted(kwargs.items())
        key_parts.append(':'.join(f"{k}={v}" for k, v in sorted_kwargs))
    
    key_string = ':'.join(key_parts)
    
    # 如果键太长，使用hash
    if len(key_string) > 200:
        key_string = f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    return key_string


def cache_result(timeout=300, key_prefix=None, version=None):
    """
    缓存函数结果的装饰器
    
    Args:
        timeout: 缓存超时时间（秒），默认5分钟
        key_prefix: 缓存键前缀
        version: 缓存版本
    
    Usage:
        @cache_result(timeout=300, key_prefix='project_stats')
        def get_project_statistics(project_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            prefix = key_prefix or func.__name__
            cache_key = get_cache_key(prefix, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key, version=version)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_result
            
            # 缓存未命中，执行函数
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            
            # 将结果存入缓存
            if result is not None:
                cache.set(cache_key, result, timeout, version=version)
                logger.debug(f"Cache set: {cache_key}, timeout={timeout}s")
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern, version=None):
    """
    使缓存失效（通过模式匹配）
    
    Args:
        pattern: 缓存键模式（支持通配符，如 'project_stats:*'）
        version: 缓存版本
    
    Note:
        Django Redis 不支持通配符删除，这里使用简单的键匹配
        如果需要完整的通配符支持，需要使用 Redis 的 KEYS 命令（生产环境不推荐）
    """
    try:
        # 简单的键匹配（如果键是精确的）
        if '*' not in pattern:
            cache.delete(pattern, version=version)
            logger.info(f"Cache invalidated: {pattern}")
        else:
            # 对于通配符，需要遍历所有可能的键
            # 这里只处理简单的模式，如 'project_stats:*'
            prefix = pattern.replace('*', '')
            # 注意：实际项目中可能需要维护一个键列表或使用 Redis 的 KEYS 命令
            logger.warning(f"Wildcard cache invalidation not fully supported: {pattern}")
    except Exception as e:
        logger.error(f"Failed to invalidate cache {pattern}: {str(e)}")


def cache_project_statistics(project_id, data, timeout=300):
    """
    缓存项目统计信息
    
    Args:
        project_id: 项目ID
        data: 统计数据
        timeout: 超时时间（秒），默认5分钟
    """
    cache_key = get_cache_key(CACHE_KEY_PREFIX['project_stats'], project_id)
    cache.set(cache_key, data, timeout)
    logger.debug(f"Cached project statistics: project_id={project_id}")


def get_cached_project_statistics(project_id):
    """
    获取缓存的项目统计信息
    
    Args:
        project_id: 项目ID
    
    Returns:
        dict or None: 统计数据，如果缓存未命中返回None
    """
    cache_key = get_cache_key(CACHE_KEY_PREFIX['project_stats'], project_id)
    return cache.get(cache_key)


def invalidate_project_statistics(project_id=None):
    """
    使项目统计缓存失效
    
    Args:
        project_id: 项目ID，如果为None则清除所有项目统计缓存
    """
    if project_id:
        cache_key = get_cache_key(CACHE_KEY_PREFIX['project_stats'], project_id)
        cache.delete(cache_key)
        logger.info(f"Invalidated project statistics cache: project_id={project_id}")
    else:
        # 清除所有项目统计缓存（需要知道所有项目ID，这里简化处理）
        logger.warning("Clearing all project statistics cache not fully supported")


def cache_user_roles(user_id, roles_data, timeout=600):
    """
    缓存用户角色信息
    
    Args:
        user_id: 用户ID
        roles_data: 角色数据
        timeout: 超时时间（秒），默认10分钟
    """
    cache_key = get_cache_key(CACHE_KEY_PREFIX['user_roles'], user_id)
    cache.set(cache_key, roles_data, timeout)
    logger.debug(f"Cached user roles: user_id={user_id}")


def get_cached_user_roles(user_id):
    """
    获取缓存的用户角色信息
    
    Args:
        user_id: 用户ID
    
    Returns:
        list or None: 角色数据，如果缓存未命中返回None
    """
    cache_key = get_cache_key(CACHE_KEY_PREFIX['user_roles'], user_id)
    return cache.get(cache_key)


def invalidate_user_roles(user_id):
    """
    使用户角色缓存失效
    
    Args:
        user_id: 用户ID
    """
    cache_key = get_cache_key(CACHE_KEY_PREFIX['user_roles'], user_id)
    cache.delete(cache_key)
    logger.info(f"Invalidated user roles cache: user_id={user_id}")


def cache_user_permissions(user_id, request_method, permissions_data, timeout=300):
    """
    缓存用户权限检查结果
    
    Args:
        user_id: 用户ID
        request_method: HTTP请求方法
        permissions_data: 权限数据
        timeout: 超时时间（秒），默认5分钟
    """
    cache_key = get_cache_key(CACHE_KEY_PREFIX['user_permissions'], user_id, method=request_method)
    cache.set(cache_key, permissions_data, timeout)
    logger.debug(f"Cached user permissions: user_id={user_id}, method={request_method}")


def get_cached_user_permissions(user_id, request_method):
    """
    获取缓存的用户权限检查结果
    
    Args:
        user_id: 用户ID
        request_method: HTTP请求方法
    
    Returns:
        dict or None: 权限数据，如果缓存未命中返回None
    """
    cache_key = get_cache_key(CACHE_KEY_PREFIX['user_permissions'], user_id, method=request_method)
    return cache.get(cache_key)


def invalidate_user_permissions(user_id=None):
    """
    使用户权限缓存失效
    
    Args:
        user_id: 用户ID，如果为None则清除所有用户权限缓存
    """
    if user_id:
        # 清除该用户的所有权限缓存（需要知道所有方法，这里简化处理）
        logger.warning(f"Clearing all permissions cache for user {user_id} not fully supported")
    else:
        logger.warning("Clearing all user permissions cache not fully supported")

