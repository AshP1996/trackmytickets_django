"""
Tenant Database Router — Full Isolation Edition.

ARCHITECTURE:
    Every organization gets its own database. ALL operational models
    (users, tickets, comments, notifications, departments, projects)
    live in the tenant database. Only platform-level models
    (Organization, PlatformAdmin, ExternalDataSource, OrganizationSecret)
    remain on the 'default' primary database.

WHY ContextVar OVER threading.local():
    threading.local() binds values to the OS thread. Under ASGI servers (Daphne, Uvicorn,
    hypercorn) or any async code, a single request can hop across threads — meaning the
    DB alias set in one thread can either be invisible in another, or worse, bleed into
    an entirely different coincidentally-executing request. ContextVar binds to the
    *execution context* (the asyncio task or coroutine frame), making it safe for both
    sync and async Django views.

COMPLEXITY:
    get / set operations on ContextVar are O(1) — same as dict lookup.
"""

from contextvars import ContextVar

# Default value explicitly set to 'default' to avoid AttributeError on uninitialised contexts.
_current_db_alias: ContextVar[str] = ContextVar('current_db_alias', default='default')


def get_current_db_alias() -> str:
    """Return the active tenant DB alias for this execution context."""
    return _current_db_alias.get()


def set_current_db_alias(alias: str):
    """
    Bind the given alias to the current execution context.
    Returns the Token returned by ContextVar.set() — callers *may* use it
    to reset after the request if needed (middleware handles this automatically).
    """
    return _current_db_alias.set(alias)


def reset_current_db_alias():
    """Reset the active alias back to 'default' for the current execution context."""
    _current_db_alias.set('default')


class TenantDatabaseRouter:
    """
    Routes ORM operations for tenant-aware apps to the correct database.

    FULL ISOLATION MODEL:
        Tenant apps:   accounts (User, Dept, UserRole), tickets, comments, notifications
                       → tenant DB alias (per request)
        Platform models: Organization, PlatformAdmin, OrganizationSecret, ExternalDataSource
                       → 'default' DB always

    The alias is retrieved from a ContextVar set by TenantMiddleware, so routing
    is both thread-safe and async-safe.
    """

    # Apps whose models live in the tenant-specific database
    tenant_apps = frozenset({'tickets', 'comments', 'notifications', 'accounts'})

    # Models that MUST stay on the primary/default database regardless of app_label.
    # These are looked up as (app_label, model_name) lowercase tuples.
    platform_models = frozenset({
        ('accounts', 'organization'),
        ('accounts', 'platformadmin'),
        ('accounts', 'organizationsecret'),
        ('accounts', 'globaluser'),
        ('core', 'externaldatasource'),
        ('tickets', 'auditlog'),
    })

    # ------------------------------------------------------------------ reads

    def db_for_read(self, model, **hints):
        key = (model._meta.app_label, model._meta.model_name)
        if key in self.platform_models:
            return 'default'
        if model._meta.app_label in self.tenant_apps:
            return get_current_db_alias()
        return None  # Let other routers or defaults decide

    # ----------------------------------------------------------------- writes

    def db_for_write(self, model, **hints):
        key = (model._meta.app_label, model._meta.model_name)
        if key in self.platform_models:
            return 'default'
        if model._meta.app_label in self.tenant_apps:
            return get_current_db_alias()
        return None

    # --------------------------------------------------------------- relations

    def allow_relation(self, obj1, obj2, **hints):
        """
        All tenant-app models now live in the same database, so relations
        between them are always safe. Cross-db relations (tenant ↔ platform)
        use db_constraint=False in models; we permit them at the ORM level.
        """
        app1 = obj1._meta.app_label
        app2 = obj2._meta.app_label

        both_tenant = app1 in self.tenant_apps and app2 in self.tenant_apps
        if both_tenant:
            return True

        # Allow cross-db relations for platform models ↔ tenant models
        key1 = (app1, obj1._meta.model_name)
        key2 = (app2, obj2._meta.model_name)
        if key1 in self.platform_models or key2 in self.platform_models:
            return True

        return None

    # --------------------------------------------------------------- migrations

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Tenant apps can migrate to any DB (default for initial setup;
        tenant-specific DBs for BYODB provisioning scripts).
        Platform models only ever migrate on 'default'.
        """
        if model_name:
            key = (app_label, model_name)
            if key in self.platform_models:
                return db == 'default'

        if app_label in self.tenant_apps:
            return True  # Permit migration on both default and any tenant DB alias

        # Django built-in apps (admin, auth, sessions, contenttypes) only on default
        return db == 'default'
