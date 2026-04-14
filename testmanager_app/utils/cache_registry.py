"""
缓存键注册表模块

提供缓存键的注册和批量失效功能
支持分布式环境下的缓存管理
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Set

from django.core.cache import cache

logger = logging.getLogger(__name__)

REDIS_CACHE_REGISTRY_PREFIX = "cache_registry:"


class CacheKeyRegistry:
    """
    缓存键注册表
    
    使用 Redis Hash 存储键索引，支持分布式环境
    """
    
    def __init__(self, registry_name: str = "default") -> None:
        """
        初始化缓存键注册表
        
        Args:
            registry_name: 注册表名称，用于隔离不同模块的缓存
        """
        self.registry_name = registry_name
        self._redis_key = f"{REDIS_CACHE_REGISTRY_PREFIX}{registry_name}"
    
    def register(self, key: str) -> None:
        """
        注册一个缓存键
        
        Args:
            key: 缓存键
        """
        try:
            cache.cache.client._client.sadd(self._redis_key, key)
            logger.debug(f"Registered cache key: {key}")
        except Exception as e:
            logger.warning(f"Failed to register cache key {key}: {e}")
    
    def register_prefix(self, prefix: str, keys: list) -> None:
        """
        批量注册具有相同前缀的缓存键
        
        Args:
            prefix: 缓存键前缀
            keys: 缓存键列表
        """
        try:
            if keys:
                cache.cache.client._client.sadd(self._redis_key, *keys)
                logger.debug(f"Registered {len(keys)} cache keys with prefix: {prefix}")
        except Exception as e:
            logger.warning(f"Failed to register cache keys with prefix {prefix}: {e}")
    
    def invalidate(self, key: str) -> bool:
        """
        使单个缓存键失效
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功
        """
        try:
            cache.delete(key)
            try:
                cache.cache.client._client.srem(self._redis_key, key)
            except Exception:
                pass
            logger.info(f"Invalidated cache key: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate cache key {key}: {e}")
            return False
    
    def invalidate_prefix(self, prefix: str) -> int:
        """
        使指定前缀的所有缓存键失效
        
        Args:
            prefix: 缓存键前缀
            
        Returns:
            失效的键数量
        """
        try:
            all_keys = self.get_all_keys()
            matching_keys = [k for k in all_keys if k.startswith(prefix)]
            
            for key in matching_keys:
                try:
                    cache.delete(key)
                except Exception as e:
                    logger.warning(f"Failed to delete cache key {key}: {e}")
            
            if matching_keys:
                try:
                    cache.cache.client._client.srem(self._redis_key, *matching_keys)
                except Exception:
                    pass
                    
            logger.info(f"Invalidated {len(matching_keys)} cache keys with prefix: {prefix}")
            return len(matching_keys)
        except Exception as e:
            logger.error(f"Failed to invalidate cache keys with prefix {prefix}: {e}")
            return 0
    
    def invalidate_all(self) -> int:
        """
        使所有注册的缓存键失效
        
        Returns:
            失效的键数量
        """
        try:
            all_keys = self.get_all_keys()
            
            for key in all_keys:
                try:
                    cache.delete(key)
                except Exception as e:
                    logger.warning(f"Failed to delete cache key {key}: {e}")
            
            try:
                cache.cache.client._client.delete(self._redis_key)
            except Exception:
                pass
                
            logger.info(f"Invalidated all {len(all_keys)} cache keys")
            return len(all_keys)
        except Exception as e:
            logger.error(f"Failed to invalidate all cache keys: {e}")
            return 0
    
    def get_all_keys(self) -> list[str]:
        """
        获取所有注册的缓存键
        
        Returns:
            缓存键列表
        """
        try:
            return list(cache.cache.client._client.smembers(self._redis_key))
        except Exception as e:
            logger.warning(f"Failed to get all cache keys: {e}")
            return []
    
    def get_size(self) -> int:
        """
        获取注册表大小
        
        Returns:
            注册的键数量
        """
        try:
            return cache.cache.client._client.scard(self._redis_key)
        except Exception as e:
            logger.warning(f"Failed to get registry size: {e}")
            return 0


_global_registries: dict[str, CacheKeyRegistry] = {}


def get_cache_registry(name: str = "default") -> CacheKeyRegistry:
    """
    获取全局缓存注册表实例
    
    Args:
        name: 注册表名称
        
    Returns:
        CacheKeyRegistry 实例
    """
    if name not in _global_registries:
        _global_registries[name] = CacheKeyRegistry(name)
    return _global_registries[name]
