from django.urls import path
from .platform_views import (
    PlatformLoginView, PlatformMeView,
    PlatformOrganizationsView, PlatformOrganizationDetailView, PlatformOrganizationSuspendView,
    PublicOrganizationRegisterView,
    PlatformStatsView,
    PlatformEnquiriesView, PlatformEnquiryReadView, PlatformEnquiryDetailView,
    PublicEnquiryView,
    PlatformForgotPasswordView, PlatformResetPasswordView
)

urlpatterns = [
    # Auth
    path('login',            PlatformLoginView.as_view(),          name='platform_api_login'),
    path('me',               PlatformMeView.as_view(),             name='platform_api_me'),

    # Organizations
    path('organizations',            PlatformOrganizationsView.as_view(),      name='platform_api_organizations'),
    path('organizations/<int:pk>',   PlatformOrganizationDetailView.as_view(), name='platform_api_organization_detail'),
    path('organizations/<int:pk>/suspend', PlatformOrganizationSuspendView.as_view(), name='platform_api_organization_suspend'),

    # Stats
    path('stats', PlatformStatsView.as_view(), name='platform_api_stats'),

    # Enquiries
    path('enquiries',               PlatformEnquiriesView.as_view(),     name='platform_api_enquiries'),
    path('enquiries/<int:pk>',      PlatformEnquiryDetailView.as_view(), name='platform_api_enquiry_detail'),
    path('enquiries/<int:pk>/read', PlatformEnquiryReadView.as_view(),   name='platform_api_enquiry_read'),

    # Public
    path('public/enquiries', PublicEnquiryView.as_view(), name='platform_api_public_enquiry'),
    path('register', PublicOrganizationRegisterView.as_view(), name='platform_api_public_register'),

    # Password reset
    path('forgot-password', PlatformForgotPasswordView.as_view(), name='platform_api_forgot_password'),
    path('reset-password',  PlatformResetPasswordView.as_view(),  name='platform_api_reset_password'),
]
