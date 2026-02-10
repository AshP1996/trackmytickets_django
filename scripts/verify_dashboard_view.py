
import os
import sys
import django
from django.conf import settings

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from apps.core.views import AdminDashboardView
from apps.accounts.models import User, Organization
from apps.tickets.models import Ticket

def verify_dashboard_view():
    print("Verifying AdminDashboardView...")
    
    # Setup Data
    org_name = 'Test Org'
    subdomain = 'testverify'
    try:
        org = Organization.objects.get(subdomain=subdomain)
        print(f"Found existing org: {org}")
    except Organization.DoesNotExist:
        org = Organization.objects.create(
            name=org_name,
            subdomain=subdomain,
            email='test@example.com',
            plan='pro',
            is_active=True
        )
        print(f"Created org: {org}")

    # Create User
    email = 'admin@testverify.com'
    try:
        user = User.objects.get(email=email)
        print(f"Found user: {user}")
    except User.DoesNotExist:
        user = User.objects.create(
            email=email,
            full_name='Test Admin',
            organization=org,
            role='admin', 
            is_active=True
        )
        user.set_password('password')
        user.save()
        print(f"Created user: {user}")

    # Create Ticket
    if Ticket.objects.filter(organization=org).count() == 0:
         # Need project first
         from apps.tickets.models import Project
         project = Project.objects.create(
             name='Test Project',
             key='TEST',
             organization=org
         )
         Ticket.objects.create(
             ticket_id='TEST-1',
             project=project,
             organization=org,
             subject='Test Ticket',
             status='open',
             priority='high',
             sender_email='sender@example.com'
         )
         print("Created test ticket")

    # Request
    factory = APIRequestFactory()
    request = factory.get(f'/api/{subdomain}/admin/dashboard/')
    request.organization = org # Simulate Middleware
    force_authenticate(request, user=user)
    
    view = AdminDashboardView.as_view()
    response = view(request, company_name=subdomain)
    
    print(f"Response Status: {response.status_code}")
    if response.status_code == 200:
        print("Response Data:", response.data)
        required_keys = ['total_tickets', 'status_distribution', 'priority_distribution', 
                         'active_users', 'sla_breaches', 'avg_resolution_hours', 'ticket_trends']
        missing = [key for key in required_keys if key not in response.data]
        if not missing:
            print("✓ SUCCESS: Response contains expected data")
            print(f"  - SLA Breaches: {response.data['sla_breaches']}")
            print(f"  - Active Users: {response.data['active_users']}")
            print(f"  - Avg Resolution: {response.data['avg_resolution_hours']}h")
            print(f"  - Trends Keys: {list(response.data['ticket_trends'].keys())}")
        else:
             print(f"✗ FAILURE: Missing keys: {missing}")
    else:
        print("✗ FAILURE: View returned error")

if __name__ == '__main__':
    verify_dashboard_view()
