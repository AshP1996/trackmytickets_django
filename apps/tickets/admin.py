from django.contrib import admin
from .models import Ticket, Project, AuditLog

@admin.register(Ticket)
class TenantTicketAdminInterface(admin.ModelAdmin):
    list_display = ('id', 'subject', 'status', 'priority', 'organization_id')
    search_fields = ('subject', 'description', 'organization_id')
    list_filter = ('status', 'priority')

@admin.register(Project)
class TenantProjectAdminInterface(admin.ModelAdmin):
    list_display = ('key', 'name', 'organization_id', 'is_active')
    search_fields = ('key', 'name', 'organization_id')
    list_filter = ('is_active',)

@admin.register(AuditLog)
class PlatformAuditLogAdminInterface(admin.ModelAdmin):
    list_display = ('action', 'resource_type', 'user_id', 'organization_id', 'created_at')
    search_fields = ('action', 'resource_type', 'user_id', 'organization_id')
    list_filter = ('action', 'resource_type')
    readonly_fields = ('action', 'resource_type', 'resource_id', 'user_id', 'organization_id', 'ip_address', 'user_agent', 'description', 'extra_data')
