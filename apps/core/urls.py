"""
URL Configuration for Core app API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ExternalDataSourceViewSet, SchemaMappingViewSet, FeedbackViewSet, EnquiryViewSet,
    AdminDashboardView
)

router = DefaultRouter()
router.register(r'data-sources', ExternalDataSourceViewSet, basename='datasource')
router.register(r'mappings', SchemaMappingViewSet, basename='mapping')
router.register(r'feedback', FeedbackViewSet, basename='feedback')
router.register(r'enquiries', EnquiryViewSet, basename='enquiry')

urlpatterns = [
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('', include(router.urls)),
]
