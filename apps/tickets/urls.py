from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TicketViewSet, ProjectViewSet, TagViewSet, SLAPolicyViewSet,
    CannedResponseViewSet, KBCategoryViewSet, KBArticleViewSet,
    AuditLogViewSet,
)

router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'sla-policies', SLAPolicyViewSet, basename='sla-policy')
router.register(r'canned-responses', CannedResponseViewSet, basename='canned-response')
router.register(r'kb/categories', KBCategoryViewSet, basename='kb-category')
router.register(r'kb/articles', KBArticleViewSet, basename='kb-article')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]
