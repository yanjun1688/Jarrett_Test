from __future__ import annotations

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class TestsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "testmanager_app"
    
    def ready(self) -> None:
        """应用准备就绪"""
        pass