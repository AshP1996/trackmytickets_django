
import os
import sys
import django
import requests
import json

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import PlatformAdmin, Organization
from apps.core.models import Enquiry

BASE_URL = "http://localhost:8002"

def setup_test_data():
    """Ensure we have enough data for pagination"""
    print("Setting up test data...")
    
    # Create extra organizations if needed
    current_orgs = Organization.objects.count()
    if current_orgs < 5:
        for i in range(5 - current_orgs):
            Organization.objects.create(
                name=f"Pagination Test Org {i}",
                subdomain=f"page-test-{i}",
                email=f"page-test-{i}@example.com",
                is_active=True
            )
            print(f"Created Org: Pagination Test Org {i}")
            
    # Create extra enquiries if needed
    current_enqs = Enquiry.objects.count()
    if current_enqs < 5:
        for i in range(5 - current_enqs):
            Enquiry.objects.create(
                name=f"Enquiry Test {i}",
                email=f"enquiry-{i}@example.com",
                message=f"Test message for pagination {i}"
            )
            print(f"Created Enquiry: Enquiry Test {i}")

def test_pagination():
    print("=" * 70)
    print("PLATFORM PAGINATION TEST")
    print("=" * 70)

    # 1. Login
    print("\n[1/3] Logging in...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/platform/login",
            json={
                "email": "superadmin@platform.com",
                "password": "admin123"
            }
        )
    except requests.exceptions.ConnectionError:
        print(f"✗ Could not connect to {BASE_URL}. Is the server running?")
        return False

    if response.status_code != 200:
        print(f"✗ Login failed: {response.text}")
        return False
        
    token = response.json().get('access_token')
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Login successful")

    # 2. Test Organization Pagination
    print("\n[2/3] Testing Organization Pagination (page_size=2)...")
    org_response = requests.get(
        f"{BASE_URL}/api/platform/organizations?page=1&page_size=2",
        headers=headers
    )
    
    if org_response.status_code == 200:
        data = org_response.json()
        print(f"Status Verify: {org_response.status_code}")
        # DRF pagination structure: count, next, previous, results
        if 'count' in data and 'results' in data:
             print(f"✓ Structure valid (count={data['count']})")
             print(f"  Next: {data.get('next')}")
             print(f"  Previous: {data.get('previous')}")
             results = data['results']
             print(f"  Results length: {len(results)}")
             try:
                 print(f"  Results sample: {[r.get('name') for r in results]}")
             except:
                 print(f"  Results sample keys: {[list(r.keys()) for r in results]}")
             
             if len(results) == 2:
                 print(f"✓ Page size respected (got {len(results)} items)")
             else:
                 print(f"✗ Page size mismatch (expected 2, got {len(results)})")
        else:
             print(f"✗ Invalid pagination structure. Keys: {data.keys()}")
             # Fallback check for old structure
             if 'organizations' in data:
                 print("✗ Still returning old 'organizations' list format!")
    else:
        print(f"✗ Request failed: {org_response.status_code} - {org_response.text}")

    # 3. Test Enquiry Pagination
    print("\n[3/3] Testing Enquiry Pagination (page_size=2)...")
    enq_response = requests.get(
        f"{BASE_URL}/api/platform/enquiries?page=1&page_size=2",
        headers=headers
    )
    
    if enq_response.status_code == 200:
        data = enq_response.json()
        if 'count' in data and 'results' in data:
             print(f"✓ Structure valid (count={data['count']})")
             results = data['results']
             if len(results) == 2:
                 print(f"✓ Page size respected (got {len(results)} items)")
             else:
                 print(f"✗ Page size mismatch (expected 2, got {len(results)})")
        else:
             print(f"✗ Invalid pagination structure. Keys: {data.keys()}")
    else:
        print(f"✗ Request failed: {enq_response.status_code} - {enq_response.text}")

if __name__ == "__main__":
    setup_test_data()
    test_pagination()
