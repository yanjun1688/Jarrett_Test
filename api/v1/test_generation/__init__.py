"""
Test Generation API
统一的测试生成 API 模块
"""

from .views import (
    GenerateUITestView,
    GenerateAPITestView,
    GenerateFromPRDView
)

__all__ = [
    'GenerateUITestView',
    'GenerateAPITestView',
    'GenerateFromPRDView'
]