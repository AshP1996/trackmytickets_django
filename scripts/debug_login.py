
import os
import sys
import django
from django.conf import settings

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User, Organization
from rest_framework_simplejwt.tokens import RefreshToken

def debug_login(email, password, subdomain):
    print(f"--- Debugging Login for {email} on {subdomain} ---")
    
    # 1. Check Organization
    try:
        org = Organization.objects.get(subdomain=subdomain)
        print(f"✓ Organization Found: {org.name} (ID: {org.id})")
    except Organization.DoesNotExist:
        print(f"✗ Organization '{subdomain}' NOT FOUND")
        return

    # 2. Check User existence in Org
    user = User.objects.filter(email=email, organization=org).first()
    if not user:
        print(f"✗ User {email} NOT FOUND in Organization {org.name}")
        # Check if user exists anywhere
        any_user = User.objects.filter(email=email).first()
        if any_user:
            print(f"  (User exists in wrong org: {any_user.organization.subdomain})")
        return
    else:
        print(f"✓ User Found: {user.full_name} (ID: {user.id})")
        print(f"  Role: {user.role}")
        print(f"  Is Active: {user.is_active}")

    # 3. Check Password
    if user.check_password(password):
        print(f"✓ Password '{password}' is CORRECT")
    else:
        print(f"✗ Password '{password}' is INCORRECT")
        # Reset password to be sure
        print("  Resetting password to 'password123'...")
        user.set_password("password123")
        user.save()
        if user.check_password("password123"):
             print("  ✓ Password reset successful.")

    # 4. Simulate Token Generation
    try:
        refresh = RefreshToken.for_user(user)
        print("✓ Token Generation Successful")
        print(f"  Access Token: {str(refresh.access_token)[:20]}...")
    except Exception as e:
        print(f"✗ Token Generation Failed: {e}")

if __name__ == '__main__':
    # aggressive debugging
    debug_login("admin@democorp.com", "password123", "demo")
    debug_login("agent@democorp.com", "password123", "demo")
    debug_login("head@democorp.com", "password123", "demo")
    debug_login("user@democorp.com", "password123", "demo")
