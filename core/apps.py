"""
Core App Configuration
"""
from __future__ import annotations

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core'
    
    def ready(self) -> None:
        """Import signals and register default node specs when app is ready"""
        import core.signals  # noqa: F401
        
        # 注册默认节点规格到全局注册表
        from core.flow.node_spec import register_default_node_specs
        register_default_node_specs()