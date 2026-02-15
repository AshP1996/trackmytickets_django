import os
import sys
import django
from django.conf import settings
from django.core.management import call_command

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod_override')
django.setup()

from apps.accounts.models import Organization, User
from apps.core.models import ExternalDataSource

def create_acme_org():
    print("Provisioning Acme Corp...")
    
    # 1. Create Organization
    org, created = Organization.objects.get_or_create(
        subdomain='acme',
        defaults={
            'name': 'Acme Corp',
            'email': 'admin@acme.com', # Contact email
            'plan': 'free',
            'is_active': True
        }
    )
    if created:
        print(f"[CREATED] Organization: {org.name}")
    else:
        print(f"[EXISTS] Organization: {org.name}")
        
    # 2. Create External Data Source (SQLite)
    db_name = 'acme.db'
    db_path = f"/tmp/{db_name}" # In Docker, this is effectively ephemeral but works for test
    
    ds, ds_created = ExternalDataSource.objects.get_or_create(
        organization=org,
        name='Acme SQLite DB',
        defaults={
            'type': 'sqlite',
            'database': db_path,
            'is_active': True,
            'connection_status': 'connected'
        }
    )
    if ds_created:
        print(f"[CREATED] Data Source: {ds.name} -> {db_path}")
    else:
        print(f"[EXISTS] Data Source: {ds.name}")
        
    # 3. Create Admin User
    if not User.objects.filter(email='admin@acme.com', organization=org).exists():
        user = User.objects.create(
            email='admin@acme.com',
            organization=org,
            full_name='Acme Admin',
            role='admin',
            is_active=True
        )
        user.set_password('password123')
        user.save()
        print("[CREATED] User: admin@acme.com / password123")
    else:
        print("[EXISTS] User: admin@acme.com")
        
    # 4. Migrate Tenant DB
    print("Migrating tenant database...")
    
    # Configure connection
    db_alias = 'tenant_acme'
    db_config = settings.DATABASES['default'].copy()
    db_config['ENGINE'] = 'django.db.backends.sqlite3'
    db_config['NAME'] = db_path
    db_config['OPTIONS'] = {} 
    
    settings.DATABASES[db_alias] = db_config
    
    try:
        call_command('migrate', database=db_alias)
        print("Migration successful!")
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    create_acme_org()
