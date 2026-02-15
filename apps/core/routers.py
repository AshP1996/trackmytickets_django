import threading
from django.conf import settings

# Thread-local storage for the current tenant DB alias
_thread_locals = threading.local()

def get_current_db_alias():
    return getattr(_thread_locals, 'db_alias', 'default')

def set_current_db_alias(alias):
    _thread_locals.db_alias = alias

def reset_current_db_alias():
    _thread_locals.db_alias = 'default'

class TenantDatabaseRouter:
    """
    Router to control database operations for tenant-specific apps.
    Routes 'tickets', 'comments', 'notifications' to the tenant DB configured in middleware.
    """
    
    tenant_apps = {'tickets', 'comments', 'notifications'}
    
    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.tenant_apps:
            alias = get_current_db_alias()
            return alias
        if model._meta.app_label == 'accounts':
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.tenant_apps:
            alias = get_current_db_alias()
            return alias
        if model._meta.app_label == 'accounts':
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations if both are in tenant apps
        if (
            obj1._meta.app_label in self.tenant_apps and 
            obj2._meta.app_label in self.tenant_apps
        ):
            return True
        
        # Allow relations between tenant apps and 'accounts' (User, Organization)
        # explicitly because we set db_constraint=False
        if (
            (obj1._meta.app_label in self.tenant_apps and obj2._meta.app_label == 'accounts') or
            (obj1._meta.app_label == 'accounts' and obj2._meta.app_label in self.tenant_apps)
        ):
            return True
            
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # We only migrate separate DBs if we have a way to target them specifically.
        # For now, we assume migrations run on 'default' unless specified.
        # If we are running migration for a tenant DB, we need to know.
        
        # This part is tricky without a specific management command to migrate tenant DBs.
        # However, for run_syncdb or migrate, we typically filter.
        
        if app_label in self.tenant_apps:
            if db != 'default':
                # Allow migrating tenant apps to tenant DBs
                return True
            # Also allow migrating to default because that's where they live by default
            return True
        
        # Non-tenant apps (accounts, core) should only be in default
        if db == 'default':
            return True
            
        return False
