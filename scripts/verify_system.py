
import os
import sys
import django
from django.test import Client

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User, PlatformAdmin, Organization

def verify_pages():
    print("Starting System Verification...")
    client = Client()

    # 1. Platform Admin Verification
    print("\n--- Verifying Platform Admin ---")
    try:
        admin = PlatformAdmin.objects.get(email="superadmin@platform.com")
        client.force_login(admin, backend='apps.accounts.backends.PlatformAdminBackend')
        
        urls = [
            '/platform/dashboard',
        ]
        
        for url in urls:
            resp = client.get(url)
            print(f"{'✓' if resp.status_code == 200 else '✗'} {url} ({resp.status_code})")
                
        client.logout()
    except Exception as e:
        print(f"✗ Platform Admin verification failed: {e}")

    # 2. Company Admin Verification
    print("\n--- Verifying Company Admin (Demo Corp) ---")
    try:
        org = Organization.objects.get(subdomain="demo")
        user = User.objects.get(email="admin@demo.com", organization=org)
        client.force_login(user)
        
        urls = [
            f'/{org.subdomain}/dashboard',
            f'/{org.subdomain}/tickets',
        ]
        
        for url in urls:
            resp = client.get(url)
            print(f"{'✓' if resp.status_code == 200 else '✗'} {url} ({resp.status_code})")
        
        client.logout()
    except Exception as e:
        print(f"✗ Company Admin verification failed: {e}")

    # 3. Agent Verification
    print("\n--- Verifying Agent (Demo Corp) ---")
    try:
        org = Organization.objects.get(subdomain="demo")
        user = User.objects.get(email="agent@demo.com", organization=org)
        client.force_login(user)
        
        urls = [
            f'/{org.subdomain}/tickets',
        ]
        
        # Find a ticket
        from apps.tickets.models import Ticket
        ticket = Ticket.objects.filter(organization=org).first()
        if ticket:
            urls.append(f'/{org.subdomain}/tickets/{ticket.ticket_id}')
        
        for url in urls:
            resp = client.get(url)
            print(f"{'✓' if resp.status_code == 200 else '✗'} {url} ({resp.status_code})")
        
        client.logout()
    except Exception as e:
        print(f"✗ Agent verification failed: {e}")

    # 4. User Verification (Customer)
    print("\n--- Verifying Customer (Demo Corp) ---")
    try:
        org = Organization.objects.get(subdomain="demo")
        user = User.objects.get(email="customer@demo.com", organization=org)
        client.force_login(user)
        
        urls = [
            f'/{org.subdomain}/tickets',
            f'/{org.subdomain}/tickets/create',
        ]
        
        for url in urls:
            resp = client.get(url)
            print(f"{'✓' if resp.status_code == 200 else '✗'} {url} ({resp.status_code})")
        
        client.logout()
    except Exception as e:
        print(f"✗ Customer verification failed: {e}")

    # 5. Public Pages
    print("\n--- Verifying Public Pages ---")
    urls = [
        '/',
        '/platform/login',
        f'/demo/login',
    ]
    for url in urls:
        resp = client.get(url)
        if resp.status_code == 200:
            print(f"✓ {url} (200 OK)")
        else:
            print(f"✗ {url} ({resp.status_code})")

if __name__ == '__main__':
    verify_pages()
