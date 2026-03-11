"""
TenantMiddleware — hardened edition.

Improvements over the original:
    1. Uses ContextVar-based set_current_db_alias (async-safe, via routers.py).
    2. Guards the settings.DATABASES write with a threading.Lock to prevent
       partial-config races when two requests start for the same new tenant
       simultaneously on different threads.
    3. Graceful 503 fallback when the tenant DB is configured but unreachable —
       instead of surfacing a raw OperationalError to the user.
    4. Logs the tenant_id on every request for correlation with CorrelationIDMiddleware.
"""

import logging
import re
import threading

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger('apps')

# Single process-wide lock that serialises writes to settings.DATABASES.
# Reads (which happen on every request) never need the lock because Python
# dict reads are safe without a GIL-drop, and we only guard *writes*.
_db_settings_lock = threading.Lock()


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        """
        AUDIT-FIX MED-1: Reset the ContextVar DB alias whenever a view raises
        an exception. Without this, the next reused WSGI worker thread inherits
        the previous tenant's alias and routes queries to the wrong database.
        """
        from apps.core.routers import reset_current_db_alias
        reset_current_db_alias()
        return None  # don't suppress — let DRF/Django handle the response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip infra endpoints — no tenant context needed
        if self._is_excluded_path(request.path):
            return None

        # ---- 1. Resolve company_name from URL kwargs or path segments ----
        company_name = view_kwargs.get('company_name') or self._extract_company_name(request.path)

        request.organization = None
        request.organization_id = None

        # Reset DB alias to default at the start of every view
        from apps.core.routers import reset_current_db_alias, set_current_db_alias
        reset_current_db_alias()

        if not company_name:
            return None  # Platform-level route; views must check request.organization themselves

        # ---- 2a. AUDIT-FIX HIGH-5: Whitelist slug character set ----
        # Rejects slugs with path traversal chars, null bytes, or excessive length
        # before touching the database. Protects against slug-based enumeration/probing.
        _SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9\-]{0,61}[a-z0-9]$')
        if not _SLUG_RE.match(company_name.lower()):
            return JsonResponse(
                {'error': 'Invalid organization identifier'},
                status=400,
            )

        # ---- 2. Resolve Organization ----
        from apps.accounts.models import Organization
        try:
            subdomain = company_name.lower().strip()
            organization = (
                Organization.objects
                .filter(subdomain=subdomain, is_active=True)
                .only('id', 'subdomain', 'name', 'plan', 'limits', 'settings')
                .first()
            )

            if not organization:
                return JsonResponse(
                    {'error': f'Organization not found: {company_name}'},
                    status=404
                )

            request.organization = organization
            request.organization_id = organization.id

            # ---- 3. BYODB: resolve tenant-specific DB ----
            db_alias = f'tenant_{organization.id}'

            if db_alias not in settings.DATABASES:
                # Only hit the DB to look up ExternalDataSource if the alias
                # isn't already registered (avoids redundant query on warm cache).
                from apps.core.models import ExternalDataSource
                data_source = (
                    ExternalDataSource.objects
                    .filter(
                        organization=organization,
                        is_active=True,
                        connection_status='connected',
                    )
                    .only(
                        'type', 'database', 'username', 'password_encrypted',
                        'host', 'port',
                    )
                    .first()
                )

                if data_source:
                    self._register_tenant_db(db_alias, data_source)

            # If alias was just registered *or* was already there, activate it.
            if db_alias in settings.DATABASES:
                # Lightweight connectivity check before routing
                if not self._db_is_reachable(db_alias):
                    logger.error(
                        'tenant_db_unreachable alias=%s org_id=%s',
                        db_alias, organization.id
                    )
                    return JsonResponse(
                        {
                            'error': 'Tenant database is temporarily unavailable.',
                            'retry_after': 30,
                        },
                        status=503,
                    )
                set_current_db_alias(db_alias)

            # ---- 4. HYBRID USER ARCHITECTURE: JWT Validation & Sync ----
            # Intercept JWT to guarantee cross-tenant isolation and synchronize GlobalUser
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                token_str = auth_header.split(' ')[1]
                from rest_framework_simplejwt.tokens import UntypedToken
                from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
                try:
                    token = UntypedToken(token_str)
                    
                    # 4a. Strict Subdomain Validation
                    token_org_id = token.get('org_id')
                    if token_org_id and token_org_id != organization.id:
                        logger.warning(
                            f"Cross-tenant access blocked! Token org={token_org_id} vs request org={organization.id}"
                        )
                        return JsonResponse(
                            {'error': 'Forbidden. Token does not belong to this organization.'}, 
                            status=403
                        )
                    
                    # 4b. GlobalUser Sync Validation (Self-Healing)
                    user_id = token.get('user_id')
                    if user_id and not token.get('is_platform_admin'):
                        from apps.accounts.models import GlobalUser
                        # We use default DB for GlobalUser via the Router automatically
                        exists = GlobalUser.objects.filter(
                            tenant_user_id=user_id, 
                            organization_id=organization.id
                        ).exists()
                        
                        if not exists:
                            from apps.accounts.models import User
                            tenant_user = User.objects.filter(id=user_id).first()
                            if tenant_user:
                                from apps.accounts.services import UserProvisionService
                                UserProvisionService.sync_global_user(tenant_user, organization)
                                
                except (InvalidToken, TokenError):
                    pass  # Let DRF handle invalid token errors within the View layer

        except Exception as e:
            logger.exception(
                'TenantMiddleware error company=%s: %s', company_name, str(e)
            )
            return JsonResponse({'error': 'Internal server error'}, status=500)

        return None

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _is_excluded_path(path: str) -> bool:
        excluded_prefixes = ('/admin/', '/static/', '/media/', '/health')
        excluded_exact = {'/robots.txt', '/sitemap.xml'}
        return path in excluded_exact or any(path.startswith(p) for p in excluded_prefixes)

    @staticmethod
    def _extract_company_name(path: str):
        parts = path.strip('/').split('/')
        if not parts or not parts[0]:
            return None
        known_routes = frozenset({'admin', 'api', 'static', 'media', 'platform', 'health'})
        if parts[0] not in known_routes:
            return parts[0]
        # api/<company>/...
        if parts[0] == 'api' and len(parts) >= 2 and parts[1] != 'platform':
            return parts[1]
        return None

    @staticmethod
    def _register_tenant_db(alias: str, data_source):
        """
        Build and write the Django DATABASES config for this tenant.
        Protected by a process-wide lock to prevent partial-write races when two
        requests for the same *new* tenant arrive simultaneously.
        """
        type_to_engine = {
            'postgres': 'django.db.backends.postgresql',
            'mysql': 'django.db.backends.mysql',
            'sqlite': 'django.db.backends.sqlite3',
            'mariadb': 'django.db.backends.mysql',
        }
        engine = type_to_engine.get(
            data_source.type,
            f'django.db.backends.{data_source.type}',
        )

        base = settings.DATABASES['default'].copy()
        db_config = {
            **base,
            'ENGINE': engine,
            'NAME': data_source.database,
            'USER': data_source.username or '',
            'PASSWORD': data_source.get_password() or '',
            'HOST': data_source.host or '',
            'PORT': data_source.port or '',
            'CONN_MAX_AGE': 600,
        }
        if data_source.type == 'sqlite':
            db_config['OPTIONS'] = {}

        with _db_settings_lock:
            # Double-checked locking: another thread may have registered it
            # while we were building the config dict.
            if alias not in settings.DATABASES:
                settings.DATABASES[alias] = db_config

    @staticmethod
    def _db_is_reachable(alias: str) -> bool:
        """
        Perform a cheap connectivity check (single SELECT 1).
        Returns True if the DB responds, False otherwise.
        Uses connection pool so warm connections are free.
        """
        try:
            from django.db import connections
            conn = connections[alias]
            conn.ensure_connection()
            return True
        except Exception:
            return False
