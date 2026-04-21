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
        """Import signals when app is ready"""
        import core.signals  # noqa: F401
        # Connect lazy signals that need models from the same app
        core.signals._connect_test_execution_signals()
        core.signals._connect_chatbot_execution_log_signals()