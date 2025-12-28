from django.urls import path
from .views import ProcessPRDView

urlpatterns = [
    path('process-prd/', ProcessPRDView.as_view(), name='process_prd'),
]