from django.urls import path
from .platform_views import (
    PlatformLoginView, PlatformMeView, PlatformOrganizationsView,
    PlatformStatsView, PlatformEnquiriesView, PlatformEnquiryReadView,
    PublicEnquiryView, PlatformForgotPasswordView, PlatformResetPasswordView
)

urlpatterns = [
    path('login', PlatformLoginView.as_view(), name='platform_api_login'),
    path('me', PlatformMeView.as_view(), name='platform_api_me'),
    path('organizations', PlatformOrganizationsView.as_view(), name='platform_api_organizations'),
    path('stats', PlatformStatsView.as_view(), name='platform_api_stats'),
    path('enquiries', PlatformEnquiriesView.as_view(), name='platform_api_enquiries'),
    path('enquiries/<int:pk>/read', PlatformEnquiryReadView.as_view(), name='platform_api_enquiry_read'),
    path('public/enquiries', PublicEnquiryView.as_view(), name='platform_api_public_enquiry'),
    path('forgot-password', PlatformForgotPasswordView.as_view(), name='platform_api_forgot_password'),
    path('reset-password', PlatformResetPasswordView.as_view(), name='platform_api_reset_password'),
]
