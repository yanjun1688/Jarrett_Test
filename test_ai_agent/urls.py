"""
AI Agent URL Configuration

Routes are now unified under api/urls.py (/api/v1/)
This file is kept for backward compatibility and exports.
"""

from django.urls import path
from .views import ProcessPRDView

urlpatterns = [
    path('process-prd/', ProcessPRDView.as_view(), name='process_prd'),
]