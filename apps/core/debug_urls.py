"""
Debug URL configuration. Endpoints only work when DEBUG or ENABLE_TENANT_DEBUG=True.
Call as /api/<company_name>/debug/tenant/ to get tenant context.
"""
from django.urls import path
from .debug_views import tenant_debug_view

urlpatterns = [
    path('tenant/', tenant_debug_view),
]
