
import sys
sys.path.append('/app')
import os
import django
from django.conf import settings

# Setup Django if not already running
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod_override')
if not settings.configured:
    django.setup()

from apps.tickets.models import Project
from apps.accounts.models import User
from apps.core.routers import TenantDatabaseRouter, get_current_db_alias, set_current_db_alias

def debug_db():
    print("--- DEBUG DB SETTINGS ---")
    print(f"DATABASES keys: {list(settings.DATABASES.keys())}")
    
    # Check default DB
    default_db = settings.DATABASES.get('default', {})
    print(f"Default DB Engine: {default_db.get('ENGINE')}")
    print(f"Default DB Name: {default_db.get('NAME')}")
    
    # Check if other aliases exist (from base?)
    for key in settings.DATABASES:
        if key != 'default':
            print(f"{key} DB Engine: {settings.DATABASES[key].get('ENGINE')}")

    router = TenantDatabaseRouter()
    
    print("\n--- ROUTER ---")
    # Simulate tenant context?
    # Default without middleware runs in 'default' alias
    print(f"Current Thread DB Alias (initial): {get_current_db_alias()}")
    
    user_db = router.db_for_write(User)
    print(f"DB for User (write): {user_db}")
    
    project_db = router.db_for_write(Project)
    print(f"DB for Project (write): {project_db}")
    
    print("\n--- QUERIES (Default Context) ---")
    try:
        user_count = User.objects.count()
        print(f"User count: {user_count} (Success)")
    except Exception as e:
        print(f"User query failed: {str(e)}")
        
    try:
        project_count = Project.objects.count()
        print(f"Project count: {project_count} (Success)")
    except Exception as e:
        print(f"Project query failed: {str(e)}")

    from apps.core.models import ExternalDataSource
    from apps.accounts.models import Organization
    
    # Check External Data Sources
    print("\n--- EXTERNAL DATA SOURCES ---")
    orgs = Organization.objects.all()
    for org in orgs:
        ds = ExternalDataSource.objects.filter(organization=org)
        print(f"Org: {org.name} ({org.subdomain}) - Data Sources: {ds.count()}")
        for d in ds:
             print(f"  - ID: {d.id}, Name: {d.name}, Type: {d.type}, Active: {d.is_active}, Connected: {d.connection_status}")

if __name__ == "__main__":
    debug_db()
