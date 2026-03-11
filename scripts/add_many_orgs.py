
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import Organization

def add_orgs():
    print("Adding 20 organizations...")
    for i in range(20):
        Organization.objects.create(
            name=f"Extra Org {i}",
            subdomain=f"extra-{i}",
            email=f"extra-{i}@example.com",
            is_active=True
        )
    print("Done.")

if __name__ == "__main__":
    add_orgs()
