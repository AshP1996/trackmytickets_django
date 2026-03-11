import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.tickets.models import Project
from apps.accounts.models import Organization
from django.db import IntegrityError

try:
    org = Organization.objects.get(subdomain='audit-test')
    print("Org found:", org.id)
    
    p = Project.objects.create(
        name="Audit Platform Debug",
        key="APD",
        description="test",
        organization_id=org.id
    )
    print("Project created:", p.id)
except IntegrityError as e:
    print("IntegrityError:", str(e))
except Exception as e:
    print("Other error:", str(e))
