"""
缓存工具模块
提供统一的缓存操作接口，简化缓存使用

缓存策略：
- 项目统计：5分钟（数据变化不频繁）
- 项目列表：2分钟（可能变化）
"""
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# mypy: disable-error-code="attr-defined, arg-type, no-any-return"
from __future__ import annotations

import hashlib
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from django.core.cache import cache

logger = logging.getLogger(__name__)

T = TypeVar('T')

CACHE_KEY_PREFIX = {
    'project_stats': 'project_stats',
    'project_list': 'project_list',
    'report_data': 'report_data',
}


def get_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """
    生成缓存键
    
    Args:
        prefix: 缓存键前缀
        *args: 位置参数
        **kwargs: 关键字参数
    
    Returns:
        str: 缓存键
    """
    key_parts = [prefix]
    
    if args:
        key_parts.append(':'.join(str(arg) for arg in args))
    
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        key_parts.append(':'.join(f"{k}={v}" for k, v in sorted_kwargs))
    
    key_string = ':'.join(key_parts)
    
    if len(key_string) > 200:
        key_string = f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    return key_string


def cache_result(timeout: int = 300, key_prefix: Optional[str] = None, version: Optional[str] = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    缓存函数结果的装饰器
    
    Args:
        timeout: 缓存超时时间（秒），默认5分钟
        key_prefix: 缓存键前缀
        version: 缓存版本
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            prefix = key_prefix or func.__name__
            cache_key = get_cache_key(prefix, *args, **kwargs)
            
            cached_result = cache.get(cache_key, version=version)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_result
            
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            
            if result is not None:
                cache.set(cache_key, result, timeout, version=version)
                logger.debug(f"Cache set: {cache_key}, timeout={timeout}s")
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str, version: Optional[str] = None) -> None:
    """
    使缓存失效（通过模式匹配）
    
    对于通配符模式，尝试使用 Redis SCAN 命令删除匹配的键。
    如果底层缓存不支持通配符删除，则记录警告。
    """
    try:
        if '*' not in pattern:
            cache.delete(pattern, version=version)
            logger.info(f"Cache invalidated: {pattern}")
        else:
            # 尝试通过 Redis 原生客户端执行通配符删除
            try:
                client = cache.client.get_client()
                cursor = 0
                deleted_count = 0
                while True:
                    cursor, keys = client.scan(cursor, match=pattern, count=100)
                    if keys:
                        client.delete(*keys)
                        deleted_count += len(keys)
                    if cursor == 0:
                        break
                logger.info(f"Wildcard cache invalidated: {pattern}, deleted {deleted_count} keys")
            except Exception:
                logger.warning(
                    f"Wildcard cache invalidation not supported by current cache backend: {pattern}"
                )
    except Exception as e:
        logger.error(f"Failed to invalidate cache {pattern}: {str(e)}")


def cache_project_statistics(project_id: Union[int, str], data: Dict[str, Any], timeout: int = 300) -> None:
    """
    缓存项目统计信息
    """
    cache_key = get_cache_key(CACHE_KEY_PREFIX['project_stats'], project_id)
    cache.set(cache_key, data, timeout)
    logger.debug(f"Cached project statistics: project_id={project_id}")


def get_cached_project_statistics(project_id: Union[int, str]) -> Optional[Dict[str, Any]]:
    """
    获取缓存的项目统计信息
    """
    cache_key = get_cache_key(CACHE_KEY_PREFIX['project_stats'], project_id)
    return cache.get(cache_key)


def invalidate_project_statistics(project_id: Optional[Union[int, str]] = None) -> None:
    """
    使项目统计缓存失效

    同时清除全局统计缓存 (project_stats:all)，确保聚合数据也能即时刷新。
    """
    if project_id:
        cache_key = get_cache_key(CACHE_KEY_PREFIX['project_stats'], project_id)
        cache.delete(cache_key)
        logger.info(f"Invalidated project statistics cache: project_id={project_id}")

    global_key = get_cache_key(CACHE_KEY_PREFIX['project_stats'], 'all')
    cache.delete(global_key)
    logger.info("Invalidated global project statistics cache")