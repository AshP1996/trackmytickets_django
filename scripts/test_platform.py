import os
import sys
import django
import json
from django.test import Client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import PlatformAdmin

def test_platform_auth():
    print("Testing Platform Auth...")
    
    # Ensure admin exists
    admin, _ = PlatformAdmin.objects.get_or_create(email='superadmin@platform.com')
    if not admin.check_password('password123'):
        admin.set_password('password123')
        admin.save()
    
    c = Client()
    
    # 1. Login
    resp = c.post('/api/platform/login', 
                  {'email': 'superadmin@platform.com', 'password': 'password123'}, 
                  content_type='application/json')
    
    if resp.status_code != 200:
        print(f"[FAIL] Login failed: {resp.status_code} {resp.content}")
        return

    data = resp.json()
    token = data.get('access_token')
    print(f"[OK] Login successful. Token obtained.")
    
    # 2. Get Me
    resp = c.get('/api/platform/me', HTTP_AUTHORIZATION=f'Bearer {token}')
    
    if resp.status_code == 200:
        print(f"[OK] /api/platform/me: {resp.json()}")
    else:
        print(f"[FAIL] /api/platform/me failed: {resp.status_code} {resp.content}")

if __name__ == '__main__':
    test_platform_auth()
