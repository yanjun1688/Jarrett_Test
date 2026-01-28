from django.apps import AppConfig


class TestsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "testmanager_app"
    
    def ready(self):
        """应用准备就绪时导入信号处理器"""
        import testmanager_app.signals  # noqa