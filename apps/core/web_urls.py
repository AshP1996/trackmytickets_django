from django.urls import path
from apps.core.web_views import RenderTemplateView

urlpatterns = [
    # Landing Page
    path('', RenderTemplateView.as_view(template_name='landing.html'), name='index'),
    
    # Platform Pages (with and without trailing slash for compatibility)
    path('platform/login', RenderTemplateView.as_view(template_name='platform/login.html'), name='platform_login'),
    path('platform/login/', RenderTemplateView.as_view(template_name='platform/login.html'), name='platform_login_slash'),
    path('platform/forgot-password', RenderTemplateView.as_view(template_name='platform/forgot_password.html'), name='platform_forgot_password'),
    path('platform/reset-password', RenderTemplateView.as_view(template_name='platform/reset_password.html'), name='platform_reset_password'),
    path('platform/dashboard', RenderTemplateView.as_view(template_name='platform/dashboard.html'), name='platform_dashboard'),
]
