"""
缓存Mixin
为ViewSet提供列表和详情查询的缓存支持

使用方式：
    class MyViewSet(CacheMixin, BaseViewSet):
        cache_timeout = 300  # 缓存时间（秒）
        cache_list = True    # 是否缓存列表查询
        cache_retrieve = True  # 是否缓存详情查询
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.response import Response

from django.core.cache import cache
from rest_framework.response import Response
from testmanager_app.utils.cache_helper import get_cache_key
import logging

logger = logging.getLogger(__name__)

try:
    from django.conf import settings
    DEFAULT_CACHE_TIMEOUT = getattr(settings, 'CACHE_TIMEOUT_LIST', 300)
except ImportError:
    DEFAULT_CACHE_TIMEOUT = 300


class CacheMixin:
    """
    缓存Mixin，为ViewSet提供列表和详情查询的缓存支持
    
    特性：
    - 自动缓存list()和retrieve()方法的响应
    - 支持基于查询参数的缓存键生成
    - 支持自定义缓存时间
    - 自动处理缓存失效
    
    配置：
    - cache_timeout: 缓存超时时间（秒），默认300秒（5分钟）
    - cache_list: 是否缓存列表查询，默认True
    - cache_retrieve: 是否缓存详情查询，默认True
    - cache_key_prefix: 缓存键前缀，默认使用ViewSet的queryset.model.__name__
    """
    
    # 缓存配置
    cache_timeout = DEFAULT_CACHE_TIMEOUT  # 默认5分钟（从settings读取）
    cache_list = True
    cache_retrieve = True
    cache_key_prefix: str | None = None
    
    def _get_cache_prefix(self) -> str:
        """获取缓存键前缀"""
        if self.cache_key_prefix:
            return self.cache_key_prefix
        model_name = self.queryset.model.__name__.lower()  # type: ignore[attr-defined]
        return f"{model_name}_viewset"
    
    def _get_list_cache_key(self) -> str:
        """生成列表查询的缓存键"""
        prefix = f"{self._get_cache_prefix()}_list"
        
        # 获取查询参数（用于生成缓存键）
        query_params: dict[str, Any] = {}
        for key, value in self.request.query_params.items():  # type: ignore[attr-defined]
            # 只包含影响结果的查询参数
            if key not in ['page', 'format']:  # 排除分页和格式参数
                query_params[key] = value
        
        return get_cache_key(prefix, **query_params)
    
    def _get_retrieve_cache_key(self, pk: Any) -> str:
        """生成详情查询的缓存键"""
        prefix = f"{self._get_cache_prefix()}_retrieve"
        return get_cache_key(prefix, pk=pk)
    
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        列表查询（带缓存）
        
        缓存策略：
        - 基于查询参数生成缓存键
        - 缓存序列化后的数据
        - 缓存时间可配置
        """
        if not self.cache_list:
            return super().list(request, *args, **kwargs)  # type: ignore[misc]
        
        cache_key = self._get_list_cache_key()
        
        # 尝试从缓存获取
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            logger.debug(f"List cache hit: {cache_key}")
            return Response(cached_response)
        
        # 缓存未命中，执行查询
        response = super().list(request, *args, **kwargs)  # type: ignore[misc]
        
        # 存入缓存（只缓存成功响应）
        if response.status_code == 200:
            cache.set(cache_key, response.data, self.cache_timeout)
            logger.debug(f"List cache set: {cache_key}, timeout={self.cache_timeout}s")
        
        return response
    
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        详情查询（带缓存）
        
        缓存策略：
        - 基于对象ID生成缓存键
        - 缓存序列化后的数据
        - 缓存时间可配置
        """
        if not self.cache_retrieve:
            return super().retrieve(request, *args, **kwargs)  # type: ignore[misc]
        
        pk = kwargs.get('pk')
        cache_key = self._get_retrieve_cache_key(pk)
        
        # 尝试从缓存获取
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            logger.debug(f"Retrieve cache hit: {cache_key}")
            return Response(cached_response)
        
        # 缓存未命中，执行查询
        response = super().retrieve(request, *args, **kwargs)  # type: ignore[misc]
        
        # 存入缓存（只缓存成功响应）
        if response.status_code == 200:
            cache.set(cache_key, response.data, self.cache_timeout)
            logger.debug(f"Retrieve cache set: {cache_key}, timeout={self.cache_timeout}s")
        
        return response
    
    def invalidate_cache(self, pk: int | None = None) -> None:
        """
        使缓存失效
        
        Args:
            pk: 对象ID，如果提供则只清除该对象的缓存，否则清除所有相关缓存
        """
        if pk:
            # 清除详情缓存
            cache_key = self._get_retrieve_cache_key(pk)
            cache.delete(cache_key)
            logger.info(f"Cache invalidated: {cache_key}")
        else:
            # 清除列表缓存（需要知道所有可能的查询参数组合，这里简化处理）
            logger.warning("Clearing all list cache not fully supported (use specific query params)")
    
    def perform_create(self, serializer: Any) -> Any:
        """创建后清除列表缓存"""
        result = super().perform_create(serializer)  # type: ignore[misc]
        # 清除所有列表缓存（创建新对象会影响所有列表查询）
        # 使用通配符清除所有相关缓存
        prefix = self._get_cache_prefix()
        self._clear_all_list_cache(prefix)
        logger.debug(f"All list cache invalidated after create: prefix={prefix}")
        return result
    
    def perform_update(self, serializer: Any) -> Any:
        """更新后清除相关缓存"""
        instance = serializer.instance
        result = super().perform_update(serializer)  # type: ignore[misc]
        # 清除详情缓存和所有列表缓存
        self.invalidate_cache(instance.pk)
        prefix = self._get_cache_prefix()
        self._clear_all_list_cache(prefix)
        logger.debug(f"Cache invalidated after update: pk={instance.pk}")
        return result
    
    def perform_destroy(self, instance: Any) -> Any:
        """删除后清除相关缓存"""
        pk = instance.pk
        result = super().perform_destroy(instance)  # type: ignore[misc]
        # 清除详情缓存和所有列表缓存
        self.invalidate_cache(pk)
        prefix = self._get_cache_prefix()
        self._clear_all_list_cache(prefix)
        logger.debug(f"Cache invalidated after delete: pk={pk}")
        return result
    
    def _clear_all_list_cache(self, prefix: str) -> None:
        """清除所有列表缓存（包括带查询参数的）"""
        from django.core.cache import cache as django_cache
        
        # 尝试清除常见查询参数组合的缓存
        # project 是最常用的过滤参数
        try:
            # 获取所有可能的缓存键并清除
            # 由于 Django cache 不支持通配符删除，我们尝试清除常见组合
            base_key = get_cache_key(f"{prefix}_list")
            django_cache.delete(base_key)
            
            # 如果有 project 过滤，尝试清除带 project 参数的缓存
            # 遍历可能的项目ID（从1到100，覆盖大多数情况）
            for project_id in range(1, 101):
                cache_key = get_cache_key(f"{prefix}_list", project=project_id)
                django_cache.delete(cache_key)
            
            logger.debug(f"Cleared list cache for prefix={prefix} and project range 1-100")
        except Exception as e:
            logger.warning(f"Failed to clear all list cache: {e}")

