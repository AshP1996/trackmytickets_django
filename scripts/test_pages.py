import sys
import os
import django
from django.test import Client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_pages():
    client = Client()
    
    pages = [
        '/',
        '/testcompany/login',
        '/platform/login',
    ]
    

    # Create test organization
    try:
        from apps.accounts.models import Organization
        org = Organization.objects.create(
            name='Test Company',
            subdomain='testcompany',
            email='test@example.com',
            is_active=True
        )
        print(f"Created test organization: {org.subdomain}")
    except Exception as e:
        print(f"Failed to create organization: {e}")
        return

    print("Verifying pages...")
    for page in pages:
        try:
            response = client.get(page)
            if response.status_code == 200:
                print(f"[OK] {page}")
            else:
                print(f"[FAIL] {page} - Status: {response.status_code}")
                if response.status_code == 404:
                     print("Resolver match:", response.resolver_match)
                # print(response.content.decode('utf-8')[:1000]) # Preview error
        except Exception as e:
            print(f"[ERROR] {page} - {str(e)}")

    # Cleanup
    try:
        org.delete()
        print("Cleaned up test organization")
    except:
        pass

if __name__ == '__main__':
    test_pages()
