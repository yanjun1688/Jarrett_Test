"""
Services package for testmanager_app
"""

from testmanager_app.services.project_statistics import get_project_statistics
from testmanager_app.services.execution_service import TestExecutionService
from testmanager_app.services.report_service import ReportService

__all__ = [
    'get_project_statistics',
    'TestExecutionService',
    'ReportService',
]
