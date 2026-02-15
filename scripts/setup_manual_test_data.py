import os
import sys
import django
from django.conf import settings

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.accounts.models import Organization, User, PlatformAdmin, Department
from apps.tickets.models import Project

def setup():
    print("Setting up Manual Test Data...")
    
    # 1. Platform Admin
    admin, created = PlatformAdmin.objects.get_or_create(email="admin@platform.com")
    admin.set_password("password")
    admin.save()
    print(f"Platform Admin: admin@platform.com / password ({'Created' if created else 'Updated'})")
    
    # 2. Organization 'demo'
    org, created = Organization.objects.get_or_create(
        subdomain="demo",
        defaults={
            'name': "Demo Inc",
            'email': "contact@demo.com",
            'plan': "growth_cluster",
            'is_active': True
        }
    )
    if not created:
        org.plan = "growth_cluster"
        org.is_active = True
        org.save()
    print(f"Organization: Demo Inc (demo.{settings.SERVER_IP if hasattr(settings, 'SERVER_IP') else 'localhost'})")
    
    # 3. Org Admin
    user, created = User.objects.get_or_create(
        email="admin@demo.com",
        defaults={
            'full_name': "Demo Admin",
            'organization': org,
            'role': "admin",
            'is_active': True
        }
    )
    user.set_password("password")
    user.organization = org
    user.role = "admin"
    user.save()
    print(f"Org Admin: admin@demo.com / password")
    
    # 4. Department
    dept, _ = Department.objects.get_or_create(name="Support", organization=org)
    
    # 5. Agent
    agent, created = User.objects.get_or_create(
        email="agent@demo.com",
        defaults={
            'full_name': "Agent Smith",
            'organization': org,
            'role': "agent",
            'department': "Support",
            'is_active': True
        }
    )
    agent.set_password("password")
    agent.save()
    print(f"Agent: agent@demo.com / password")
    
    # 6. Project
    Project.objects.get_or_create(
        key="DEMO",
        organization=org,
        defaults={
            'name': "Demo Project",
            'lead_user': user,
            'is_active': True
        }
    )
    print("Project: Demo Project (DEMO)")
    
    print("\nSetup Complete!")

if __name__ == "__main__":
    setup()
