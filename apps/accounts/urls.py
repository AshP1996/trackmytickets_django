from django.urls import path, include
from .views import (
    LoginView, LogoutView, RegisterView, UserMeView, UserListView, UserDetailView,
    ForgotPasswordView, ResetPasswordView, DepartmentViewSet,
    DepartmentHeadStatsView, DepartmentHeadTicketsView, DepartmentHeadEmployeesView,
    ChangePasswordView, UserProfileView, OrganizationSettingsView,
    OrganizationSecretView, UserRolesView,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet, basename='department')

urlpatterns = [
    # Auth
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),   # AUDIT-FIX HIGH-3
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', UserMeView.as_view(), name='user-me'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),

    # Users
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/roles/', UserRolesView.as_view(), name='user-roles'),
    path('users/<int:pk>/roles/assign/', UserRolesView.as_view(), name='user-roles-assign'),
    path('users/<int:pk>/roles/<int:role_id>/', UserRolesView.as_view(), name='user-roles-delete'),

    # Department Head
    path('department-head/stats/', DepartmentHeadStatsView.as_view(), name='dept-head-stats'),
    path('department-head/tickets/', DepartmentHeadTicketsView.as_view(), name='dept-head-tickets'),
    path('department-head/employees/', DepartmentHeadEmployeesView.as_view(), name='dept-head-employees'),

    # Organization Settings
    path('organization/settings/', OrganizationSettingsView.as_view(), name='org-settings'),

    # Secrets / Env Vars
    path('secrets/', OrganizationSecretView.as_view(), name='org-secrets-list'),
    path('secrets/<int:pk>/', OrganizationSecretView.as_view(), name='org-secrets-detail'),

    # DRF Router
    path('', include(router.urls)),
]
