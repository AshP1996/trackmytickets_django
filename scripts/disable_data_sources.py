
import os
import django
import sys


from django.conf import settings
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod_override')
if not settings.configured:
    django.setup()

from apps.core.models import ExternalDataSource

def disable_sources():
    print("Disabling all External Data Sources...")
    ds = ExternalDataSource.objects.filter(is_active=True)
    count = ds.count()
    print(f"Found {count} active data sources.")
    
    for d in ds:
        print(f"Disabling: {d.name} (Org: {d.organization.name})")
        d.is_active = False
        d.save()
        
    print("All data sources disabled.")

if __name__ == "__main__":
    disable_sources()
