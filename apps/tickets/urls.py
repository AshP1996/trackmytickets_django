from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketViewSet, ProjectViewSet

router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'projects', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
]
