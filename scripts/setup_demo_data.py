import os
import sys
import django

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import Organization, User, PlatformAdmin, UserRole

def setup_demo_data():
    print("Setting up demo data...")

    # 1. Create Platform Admin
    try:
        if not PlatformAdmin.objects.filter(email='superadmin@platform.com').exists():
            admin = PlatformAdmin(email='superadmin@platform.com')
            admin.set_password('password123')
            admin.save()
            print("[CREATED] Platform Admin: superadmin@platform.com / password123")
        else:
            print("[EXISTS] Platform Admin: superadmin@platform.com")
            
    except Exception as e:
        print(f"[ERROR] Platform Admin: {e}")

    # 2. Create Demo Organization
    try:
        org, created = Organization.objects.get_or_create(
            subdomain='demo',
            defaults={
                'name': 'Demo Corp',
                'email': 'contact@demo.com',
                'is_active': True
            }
        )
        if created:
            print(f"[CREATED] Organization: {org.name} ({org.subdomain})")
        else:
            print(f"[EXISTS] Organization: {org.name}")

        # 3. Create Org Admin User
        if not User.objects.filter(email='admin@demo.com', organization=org).exists():
            user = User.objects.create(
                email='admin@demo.com',
                organization=org,
                full_name='Demo Admin',
                role='admin',
                is_active=True
            )
            user.set_password('password123')
            user.save()
            print("[CREATED] Org User: admin@demo.com / password123")
        else:
            print("[EXISTS] Org User: admin@demo.com")

    except Exception as e:
        print(f"[ERROR] Organization/User: {e}")

if __name__ == '__main__':
    setup_demo_data()
