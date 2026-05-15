from django.urls import path
from apps.core.web_views import RenderTemplateView

urlpatterns = [
    # Landing Page
    path('', RenderTemplateView.as_view(template_name='landing.html'), name='index'),
    
    # SEO Pages — crawlable, keyword-optimized static pages
    path('features', RenderTemplateView.as_view(template_name='seo/features.html'), name='features'),
    path('features/', RenderTemplateView.as_view(template_name='seo/features.html'), name='features_slash'),
    path('pricing', RenderTemplateView.as_view(template_name='seo/pricing.html'), name='pricing'),
    path('pricing/', RenderTemplateView.as_view(template_name='seo/pricing.html'), name='pricing_slash'),
    
    # Legal Pages
    path('privacy-policy', RenderTemplateView.as_view(template_name='legal/privacy_policy.html'), name='privacy_policy'),
    path('terms-of-service', RenderTemplateView.as_view(template_name='legal/terms_of_service.html'), name='terms_of_service'),
    
    # Platform Pages (with and without trailing slash for compatibility)
    path('platform/login', RenderTemplateView.as_view(template_name='platform/login.html'), name='platform_login'),
    path('platform/login/', RenderTemplateView.as_view(template_name='platform/login.html'), name='platform_login_slash'),
    path('platform/forgot-password', RenderTemplateView.as_view(template_name='platform/forgot_password.html'), name='platform_forgot_password'),
    path('platform/reset-password', RenderTemplateView.as_view(template_name='platform/reset_password.html'), name='platform_reset_password'),
    path('platform/dashboard', RenderTemplateView.as_view(template_name='platform/dashboard.html'), name='platform_dashboard'),
]

