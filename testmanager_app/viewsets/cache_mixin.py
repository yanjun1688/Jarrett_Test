"""
缓存Mixin
为ViewSet提供列表和详情查询的缓存支持

使用方式：
    class MyViewSet(CacheMixin, BaseViewSet):
        cache_timeout = 300  # 缓存时间（秒）
        cache_list = True    # 是否缓存列表查询
        cache_retrieve = True  # 是否缓存详情查询
"""

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
    cache_key_prefix = None
    
    def _get_cache_prefix(self):
        """获取缓存键前缀"""
        if self.cache_key_prefix:
            return self.cache_key_prefix
        model_name = self.queryset.model.__name__.lower()
        return f"{model_name}_viewset"
    
    def _get_list_cache_key(self):
        """生成列表查询的缓存键"""
        prefix = f"{self._get_cache_prefix()}_list"
        
        # 获取查询参数（用于生成缓存键）
        query_params = {}
        for key, value in self.request.query_params.items():
            # 只包含影响结果的查询参数
            if key not in ['page', 'format']:  # 排除分页和格式参数
                query_params[key] = value
        
        return get_cache_key(prefix, **query_params)
    
    def _get_retrieve_cache_key(self, pk):
        """生成详情查询的缓存键"""
        prefix = f"{self._get_cache_prefix()}_retrieve"
        return get_cache_key(prefix, pk=pk)
    
    def list(self, request, *args, **kwargs):
        """
        列表查询（带缓存）
        
        缓存策略：
        - 基于查询参数生成缓存键
        - 缓存序列化后的数据
        - 缓存时间可配置
        """
        if not self.cache_list:
            return super().list(request, *args, **kwargs)
        
        cache_key = self._get_list_cache_key()
        
        # 尝试从缓存获取
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            logger.debug(f"List cache hit: {cache_key}")
            return Response(cached_response)
        
        # 缓存未命中，执行查询
        response = super().list(request, *args, **kwargs)
        
        # 存入缓存（只缓存成功响应）
        if response.status_code == 200:
            cache.set(cache_key, response.data, self.cache_timeout)
            logger.debug(f"List cache set: {cache_key}, timeout={self.cache_timeout}s")
        
        return response
    
    def retrieve(self, request, *args, **kwargs):
        """
        详情查询（带缓存）
        
        缓存策略：
        - 基于对象ID生成缓存键
        - 缓存序列化后的数据
        - 缓存时间可配置
        """
        if not self.cache_retrieve:
            return super().retrieve(request, *args, **kwargs)
        
        pk = kwargs.get('pk')
        cache_key = self._get_retrieve_cache_key(pk)
        
        # 尝试从缓存获取
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            logger.debug(f"Retrieve cache hit: {cache_key}")
            return Response(cached_response)
        
        # 缓存未命中，执行查询
        response = super().retrieve(request, *args, **kwargs)
        
        # 存入缓存（只缓存成功响应）
        if response.status_code == 200:
            cache.set(cache_key, response.data, self.cache_timeout)
            logger.debug(f"Retrieve cache set: {cache_key}, timeout={self.cache_timeout}s")
        
        return response
    
    def invalidate_cache(self, pk=None):
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
    
    def perform_create(self, serializer):
        """创建后清除列表缓存"""
        result = super().perform_create(serializer)
        # 清除列表缓存（创建新对象会影响列表）
        # 注意：这里无法清除所有可能的查询参数组合，所以只清除默认列表缓存
        cache_key = get_cache_key(f"{self._get_cache_prefix()}_list")
        cache.delete(cache_key)
        logger.debug(f"List cache invalidated after create: {cache_key}")
        return result
    
    def perform_update(self, serializer):
        """更新后清除相关缓存"""
        instance = serializer.instance
        result = super().perform_update(serializer)
        # 清除详情缓存和列表缓存
        self.invalidate_cache(instance.pk)
        cache_key = get_cache_key(f"{self._get_cache_prefix()}_list")
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated after update: pk={instance.pk}")
        return result
    
    def perform_destroy(self, instance):
        """删除后清除相关缓存"""
        pk = instance.pk
        result = super().perform_destroy(instance)
        # 清除详情缓存和列表缓存
        self.invalidate_cache(pk)
        cache_key = get_cache_key(f"{self._get_cache_prefix()}_list")
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated after delete: pk={pk}")
        return result

