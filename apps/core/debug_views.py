"""
Tenant debug endpoint — ONLY enabled when DEBUG=True or ENABLE_TENANT_DEBUG=True.
Use for development and troubleshooting multi-tenant routing.
"""
import logging
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger('apps')


def tenant_debug_view(request, **kwargs):
    """
    Returns current tenant context: organization, org_id, database_alias, database_name.
    Available at /api/debug/tenant when DEBUG or ENABLE_TENANT_DEBUG is True.
    """
    if not getattr(settings, 'DEBUG', False) and not getattr(settings, 'ENABLE_TENANT_DEBUG', False):
        return JsonResponse({'error': 'Tenant debug endpoint is disabled'}, status=404)

    org = getattr(request, 'organization', None)
    org_id = getattr(request, 'organization_id', None)

    from apps.core.routers import get_current_db_alias
    db_alias = get_current_db_alias()

    db_name = 'N/A'
    if db_alias in settings.DATABASES:
        db_name = settings.DATABASES[db_alias].get('NAME', 'N/A')
        if hasattr(db_name, 'name'):  # Path-like
            db_name = str(db_name)

    payload = {
        'organization': org.subdomain if org else None,
        'org_id': org_id,
        'database_alias': db_alias,
        'database_name': db_name,
    }
    return JsonResponse(payload)
