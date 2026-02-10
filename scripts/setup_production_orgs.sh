#!/bin/bash
# Setup organizations in production database

set -e

echo "========================================="
echo "Setting up Organizations in Production"
echo "========================================="
echo ""

cd /var/www/trackmytickets/ticket_system_django
source /var/www/trackmytickets/venv/bin/activate

# Export environment variables
export DJANGO_SETTINGS_MODULE=config.settings.prod_override
export SECRET_KEY="EAl1GuKGVqU4WALJrd8tqcROFPBARgPlQwEs6Xe16lBeBtRoysZ0HeAYhyKy3zEOYl0"
export DB_NAME="trackmytickets"
export DB_USER="ticketuser"
export DB_PASSWORD="TrackMyTickets2026!"
export DB_HOST="127.0.0.1"
export DB_PORT="5433"

echo "Running setup script..."
python3 scripts/setup_demo_data.py

echo ""
echo "Creating TechFlow organization..."
python3 << 'EOF'
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod_override')
django.setup()

from apps.accounts.models import Organization, User

# Create TechFlow organization
org, created = Organization.objects.get_or_create(
    subdomain='techflow',
    defaults={
        'name': 'TechFlow Solutions',
        'email': 'contact@techflow.com',
        'is_active': True
    }
)

if created:
    print(f"[CREATED] Organization: {org.name} ({org.subdomain})")
    
    # Create admin user for TechFlow
    user = User.objects.create(
        email='admin@techflow.com',
        organization=org,
        full_name='TechFlow Admin',
        role='admin',
        is_active=True
    )
    user.set_password('password123')
    user.save()
    print("[CREATED] Org User: admin@techflow.com / password123")
else:
    print(f"[EXISTS] Organization: {org.name}")

# List all organizations
print("\nAll organizations in database:")
for org in Organization.objects.all():
    print(f"  - {org.name} (subdomain: {org.subdomain}, active: {org.is_active})")
EOF

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
