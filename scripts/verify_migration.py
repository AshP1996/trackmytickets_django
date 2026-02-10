import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.accounts.models import Organization, User, UserRole, Department
from apps.tickets.models import Project, Ticket
from django.contrib.auth import get_user_model

def run():
    print("Verifying Migration...")
    
    # 1. Create Organization
    org_name = "Test Corp"
    subdomain = "test"
    
    org, created = Organization.objects.get_or_create(
        subdomain=subdomain,
        defaults={'name': org_name, 'email': 'admin@test.com', 'is_active': True}
    )
    if created:
        print(f"[SUCCESS] Created Organization: {org.name} ({org.subdomain})")
    else:
        print(f"[INFO] Organization already exists: {org.name}")
        
    # 2. Create User
    email = "admin@test.com"
    user = User.objects.filter(email=email, organization=org).first()
    
    if not user:
        user = User.objects.create(
            email=email,
            organization=org,
            full_name="Test Admin",
            role="admin",
            is_active=True,
            is_onboarded=True
        )
        user.set_password("password123")
        user.save()
        print(f"[SUCCESS] Created User: {user.email}")
    else:
        print(f"[INFO] User already exists: {user.email}")

    # 3. Create Project
    project_key = "TEST"
    project, created = Project.objects.get_or_create(
        key=project_key,
        organization=org,
        defaults={'name': 'Test Project', 'lead_user': user, 'is_active': True}
    )
    if created:
        print(f"[SUCCESS] Created Project: {project.name} ({project.key})")
        
    # 4. Create Platform Admin
    from apps.accounts.models import PlatformAdmin
    platform_email = "superadmin@platform.com"
    admin = PlatformAdmin.objects.filter(email=platform_email).first()
    
    if not admin:
        admin = PlatformAdmin.objects.create(email=platform_email, is_active=True)
        admin.set_password("password123")
        admin.save()
        print(f"[SUCCESS] Created Platform Admin: {admin.email}")
    else:
        print(f"[INFO] Platform Admin already exists: {admin.email}")

    print("\nModification Verified. Database is ready.")
    print(f"Tenant Login: http://localhost:8000/{subdomain}/login")
    print(f"Platform Login: http://localhost:8000/platform/login")
    print(f"Tenant Email: {email} / password123")
    print(f"Platform Email: {platform_email} / password123")

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
