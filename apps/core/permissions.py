"""
Role-based permission classes for the multi-tenant ticket system.

Roles hierarchy:
  - platform_admin: Super admin, manages organizations (uses PlatformAdmin model)
  - admin: Organization admin, full access within their org
  - manager: Project manager, manages assigned projects and team
  - department_head: Manages their department's tickets and agents
  - agent: Can view/handle tickets assigned to them or in their projects
"""
from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    """Only allows access to Platform Admins."""
    message = 'Platform admin access required.'

    def has_permission(self, request, view):
        from apps.accounts.models import PlatformAdmin
        return (
            request.user
            and request.user.is_authenticated
            and isinstance(request.user, PlatformAdmin)
        )


class IsOrgAdmin(BasePermission):
    """Only allows access to organization admins."""
    message = 'Organization admin access required.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'role')
            and request.user.role == 'admin'
        )


class IsOrgAdminOrManager(BasePermission):
    """Allows access to org admins or managers."""
    message = 'Admin or manager access required.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'role')
            and request.user.role in ('admin', 'manager')
        )


class IsOrgAdminOrDepartmentHead(BasePermission):
    """Allows access to org admins or department heads."""
    message = 'Admin or department head access required.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'role')
            and request.user.role in ('admin', 'department_head')
        )


class IsOrgMember(BasePermission):
    """
    Ensures the authenticated user belongs to the organization
    specified in the URL (via request.organization set by TenantMiddleware).

    Additionally enforces that the JWT org_subdomain claim (set at login)
    matches the current request's organization subdomain. This prevents
    token replay attacks where a valid token from org A is used against org B.
    """
    message = 'You do not belong to this organization.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Platform admins bypass org-scoping entirely
        from apps.accounts.models import PlatformAdmin
        if isinstance(request.user, PlatformAdmin):
            return True

        org = getattr(request, 'organization', None)
        if not org:
            return True  # Non-tenant routes don't require org membership

        # 1. User must originate from a JWT tied to this Subdomain Context
        token = getattr(request.auth, 'payload', None) or getattr(request.auth, 'token', {}) \
            if hasattr(request, 'auth') and request.auth else None

        if not token or not hasattr(token, 'get'):
            return False

        # 2. SECURITY FIX C2: Validate JWT org_subdomain claim against URL org.
        #    Prevents token replay from a different org's login session.
        token_subdomain = token.get('org_subdomain')
        if not token_subdomain or token_subdomain != org.subdomain:
            return False

        return True


class ReadOnly(BasePermission):
    """Only allows read (GET, HEAD, OPTIONS) methods."""

    def has_permission(self, request, view):
        return request.method in ('GET', 'HEAD', 'OPTIONS')


class IsAdminOrReadOnly(BasePermission):
    """Admins get full access; everyone else gets read-only."""
    message = 'Admin access required for write operations.'

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'role')
            and request.user.role == 'admin'
        )
