import os
import sys
import django
from django.conf import settings
from django.core.management import call_command

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod_override')
django.setup()

from apps.core.models import ExternalDataSource

def migrate_demo_tenant():
    print("Migrating demo tenant database...")
    
    # Get the data source
    try:
        ds = ExternalDataSource.objects.get(name='Demo SQLite DB') # I assume name, or look by org
    except ExternalDataSource.DoesNotExist:
        # Try finding any for 'demo'
        ds = ExternalDataSource.objects.filter(organization__subdomain='demo').first()
        if not ds:
            print("No ExternalDataSource found for demo!")
            return

    print(f"Found Data Source: {ds.name} ({ds.type})")
    
    # Configure database connection
    db_alias = 'tenant_demo'
    
    db_config = settings.DATABASES['default'].copy()
    db_config['ENGINE'] = 'django.db.backends.sqlite3'
    db_config['NAME'] = ds.database
    db_config['OPTIONS'] = {} # Clear options for sqlite
    
    settings.DATABASES[db_alias] = db_config
    
    print(f"Configured {db_alias} with {ds.database}")
    
    # Run migrate
    try:
        call_command('migrate', database=db_alias)
        print("Migration successful!")
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    migrate_demo_tenant()
