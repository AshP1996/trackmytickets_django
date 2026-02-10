"""
Reset platform admin password
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import PlatformAdmin

def reset_platform_password():
    print("Resetting platform admin password...")
    
    admin = PlatformAdmin.objects.filter(email='superadmin@platform.com').first()
    
    if not admin:
        print("✗ Platform admin not found")
        print("Creating new platform admin...")
        admin = PlatformAdmin(email='superadmin@platform.com', is_active=True)
    
    # Set password
    admin.set_password('admin123')
    admin.save()
    
    print(f"✓ Password reset for {admin.email}")
    print(f"  Password: admin123")
    print(f"  Active: {admin.is_active}")
    
    # Verify password
    if admin.check_password('admin123'):
        print("✓ Password verification successful")
    else:
        print("✗ Password verification failed")

if __name__ == '__main__':
    reset_platform_password()
