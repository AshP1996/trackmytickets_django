from django.urls import path, include
from .views import (
    LoginView, RegisterView, UserMeView, UserListView, UserDetailView,
    ForgotPasswordView, ResetPasswordView, DepartmentViewSet,
    DepartmentHeadStatsView, DepartmentHeadTicketsView, DepartmentHeadEmployeesView
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet, basename='department')

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', UserMeView.as_view(), name='user-me'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('department-head/stats/', DepartmentHeadStatsView.as_view(), name='dept-head-stats'),
    path('department-head/tickets/', DepartmentHeadTicketsView.as_view(), name='dept-head-tickets'),
    path('department-head/employees/', DepartmentHeadEmployeesView.as_view(), name='dept-head-employees'),
    path('', include(router.urls)),
]
