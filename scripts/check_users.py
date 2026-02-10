
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.accounts.models import User, Organization, PlatformAdmin

def check_users():
    print("--- Platform Admins ---")
    platform_admins = PlatformAdmin.objects.all()
    if platform_admins.exists():
        for pa in platform_admins:
            print(f"Email: {pa.email}, Active: {pa.is_active}")
    else:
        print("No Platform Admins found.")

    print("\n--- Organizations ---")
    orgs = Organization.objects.all()
    for org in orgs:
        print(f"Org: {org.name} ({org.subdomain})")
        users = User.objects.filter(organization=org)
        print(f"  Users ({users.count()}):")
        for u in users:
            print(f"    - {u.full_name} ({u.email}) - Role: {u.role}")

if __name__ == "__main__":
    check_users()
