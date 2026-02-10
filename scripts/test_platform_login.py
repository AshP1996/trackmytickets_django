"""
Test platform login flow
"""
import os
import sys
import django
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import PlatformAdmin

def test_platform_login():
    print("=" * 70)
    print("PLATFORM LOGIN FLOW TEST")
    print("=" * 70)
    
    # Check if platform admin exists
    admin = PlatformAdmin.objects.filter(email='superadmin@platform.com').first()
    
    if not admin:
        print("\n✗ Platform admin not found!")
        print("  Run setup_demo_data.py first")
        return
    
    print(f"\n✓ Platform admin found: {admin.email}")
    print(f"  Active: {admin.is_active}")
    print(f"  is_staff: {admin.is_staff}")
    print(f"  is_superuser: {admin.is_superuser}")
    
    # Test login API
    print("\n" + "=" * 70)
    print("Testing Login API")
    print("=" * 70)
    
    base_url = "http://localhost:9000"
    
    # Test login
    print("\n[1/3] Testing login...")
    response = requests.post(
        f"{base_url}/api/platform/login",
        json={
            "email": "superadmin@platform.com",
            "password": "admin123"
        }
    )
    
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("  ✓ Login successful")
        print(f"  Access token: {data.get('access_token', 'N/A')[:50]}...")
        print(f"  User: {data.get('user', {})}")
        
        access_token = data.get('access_token')
        
        # Test /me endpoint
        print("\n[2/3] Testing /api/platform/me...")
        me_response = requests.get(
            f"{base_url}/api/platform/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        print(f"  Status: {me_response.status_code}")
        
        if me_response.status_code == 200:
            me_data = me_response.json()
            print("  ✓ Authentication successful")
            print(f"  User data: {me_data}")
        else:
            print(f"  ✗ Authentication failed")
            print(f"  Response: {me_response.text}")
        
        # Test organizations endpoint
        print("\n[3/3] Testing /api/platform/organizations...")
        orgs_response = requests.get(
            f"{base_url}/api/platform/organizations",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        print(f"  Status: {orgs_response.status_code}")
        
        if orgs_response.status_code == 200:
            orgs_data = orgs_response.json()
            print(f"  ✓ Organizations loaded: {len(orgs_data)} found")
        else:
            print(f"  ✗ Failed to load organizations")
            print(f"  Response: {orgs_response.text}")
    else:
        print(f"  ✗ Login failed")
        print(f"  Response: {response.text}")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nIf all tests passed, platform login should work in browser.")
    print("\nTo test in browser:")
    print("1. Go to http://localhost:9000/platform/login")
    print("2. Login with:")
    print("   Email: superadmin@platform.com")
    print("   Password: admin123")
    print("3. Should redirect to /platform/dashboard")
    print("=" * 70)

if __name__ == '__main__':
    test_platform_login()
