import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod_override')
os.environ.setdefault('SECRET_KEY', 'EAl1GuKGVqU4WALJrd8tqcROFPBARgPlQwEs6Xe16lBeBtRoysZ0HeAYhyKy3zEOYl0')
os.environ.setdefault('DB_PASSWORD', 'TrackMyTickets2026!')
os.environ.setdefault('DB_PORT', '5433')

django.setup()

from apps.accounts.models import Organization

orgs = Organization.objects.all()
print(f'Total organizations: {orgs.count()}')
for org in orgs:
    print(f'  - {org.name} (subdomain: {org.subdomain})')
