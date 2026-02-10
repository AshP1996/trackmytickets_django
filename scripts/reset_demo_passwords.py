"""
Reset passwords for all demo organization users
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import Organization, User

def reset_passwords():
    print("Resetting passwords for demo organization users...")
    
    try:
        org = Organization.objects.get(subdomain='demo')
    except Organization.DoesNotExist:
        print("✗ Demo organization not found")
        return
    
    users = User.objects.filter(organization=org)
    password = 'admin123'
    
    for user in users:
        user.set_password(password)
        user.save()
        print(f"✓ Reset password for {user.email} to '{password}'")
    
    print(f"\n[SUCCESS] Reset {users.count()} user passwords")
    print(f"All users now have password: {password}")

if __name__ == '__main__':
    reset_passwords()
