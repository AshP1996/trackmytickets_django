from django.urls import path
from apps.core.web_views import RenderTemplateView

urlpatterns = [
    path('login', RenderTemplateView.as_view(template_name='login.html'), name='login_page'),
    path('forgot-password', RenderTemplateView.as_view(template_name='auth/forgot_password.html'), name='forgot_password_page'),
    path('reset-password', RenderTemplateView.as_view(template_name='auth/reset_password.html'), name='reset_password_page'),
    
    path('dashboard', RenderTemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    
    # Admin
    path('admin/dashboard', RenderTemplateView.as_view(template_name='admin/dashboard.html'), name='admin_dashboard'),
    path('admin/users', RenderTemplateView.as_view(template_name='admin/users.html'), name='admin_users'),
    path('admin/departments', RenderTemplateView.as_view(template_name='admin/departments.html'), name='admin_departments'),
    path('admin/secrets', RenderTemplateView.as_view(template_name='admin/secrets.html'), name='admin_secrets'),
    path('admin/data-sources', RenderTemplateView.as_view(template_name='admin/data_sources.html'), name='admin_data_sources'),
    path('admin/reports', RenderTemplateView.as_view(template_name='admin/reports.html'), name='admin_reports'),
    
    # Head
    path('head/dashboard', RenderTemplateView.as_view(template_name='head/dashboard.html'), name='head_dashboard'),
    path('head/assign', RenderTemplateView.as_view(template_name='head/assign.html'), name='head_assign'),
]
