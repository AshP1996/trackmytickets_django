from django.urls import path
from apps.core.web_views import RenderTemplateView

urlpatterns = [
    path('notifications', RenderTemplateView.as_view(template_name='notifications.html'), name='notifications_page'),
]
