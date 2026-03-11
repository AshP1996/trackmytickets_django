from django.contrib import admin
from .models import PlatformAdmin, Organization, GlobalUser, User, Department, UserRole

@admin.register(PlatformAdmin)
class PlatformAdminInterface(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'created_at')
    search_fields = ('email',)

@admin.register(Organization)
class OrganizationAdminInterface(admin.ModelAdmin):
    list_display = ('name', 'subdomain', 'plan', 'is_active', 'created_at')
    search_fields = ('name', 'subdomain', 'email')
    list_filter = ('plan', 'is_active')

@admin.register(GlobalUser)
class GlobalUserAdminInterface(admin.ModelAdmin):
    list_display = ('email', 'organization', 'tenant_user_id', 'status', 'created_at')
    search_fields = ('email', 'organization__name')
    list_filter = ('status',)
    readonly_fields = ('email', 'organization', 'tenant_user_id')

@admin.register(User)
class TenantUserAdminInterface(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'role', 'department', 'is_active')
    search_fields = ('email', 'full_name')
    list_filter = ('role', 'is_active', 'department')

@admin.register(Department)
class DepartmentAdminInterface(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)

@admin.register(UserRole)
class UserRoleAdminInterface(admin.ModelAdmin):
    list_display = ('user', 'role', 'scope_type', 'scope_id')
    search_fields = ('user__email',)
    list_filter = ('role', 'scope_type')
