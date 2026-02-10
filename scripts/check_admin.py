import sys
import os
import django

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import PlatformAdmin

def check_admin():
    email = "superadmin@platform.com"
    try:
        admin = PlatformAdmin.objects.get(email=email)
        print(f"User {email} found.")
        print(f"Is active: {admin.is_active}")
        
        # Reset password to be sure
        admin.set_password("password123")
        admin.save()
        print("Password reset to 'password123'.")
    except PlatformAdmin.DoesNotExist:
        print(f"User {email} NOT found.")

if __name__ == "__main__":
    check_admin()
