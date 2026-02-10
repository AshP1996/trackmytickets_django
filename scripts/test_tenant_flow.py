import os
import sys
import django
import json
from django.test import Client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User, Organization

def test_tenant_flow():
    print("Testing Tenant Flow...")
    
    # 1. Setup Data
    org_subdomain = 'demo'
    email = 'admin@demo.com'
    password = 'password123'
    
    # Ensure org and user exist (setup_demo_data should have run, but let's be safe)
    try:
        org = Organization.objects.get(subdomain=org_subdomain)
        user = User.objects.get(email=email, organization=org)
        if not user.check_password(password):
            user.set_password(password)
            user.save()
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}. Please run setup_demo_data.py first.")
        return

    c = Client()
    
    # 2. Login
    print(f"\n[1] Testing Login to {org_subdomain}...")
    login_url = f'/api/{org_subdomain}/auth/login/'
    resp = c.post(login_url, 
                  {'email': email, 'password': password}, 
                  content_type='application/json')
    
    if resp.status_code != 200:
        print(f"[FAIL] Login failed: {resp.status_code} {resp.content}")
        return

    data = resp.json()
    token = data.get('access_token')
    headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
    print(f"[OK] Login successful.")

    # 3. Get Me
    print(f"\n[2] Testing /auth/me...")
    resp = c.get(f'/api/{org_subdomain}/auth/me/', **headers)
    if resp.status_code == 200:
        print(f"[OK] Me: {resp.json().get('email')}")
    else:
        print(f"[FAIL] Me failed: {resp.status_code}")

    # 4. Projects CRUD
    print(f"\n[3] Testing Projects CRUD...")
    import time
    timestamp = int(time.time())
    # Create
    project_data = {'name': f'Test Project {timestamp}', 'key': f'TST{timestamp}'[-5:], 'description': 'Test Desc'}
    resp = c.post(f'/api/{org_subdomain}/projects/', project_data, content_type='application/json', **headers)
    if resp.status_code == 201:
        project_id = resp.json()['id']
        print(f"[OK] Created Project: {project_id}")
    else:
        print(f"[FAIL] Create Project failed: {resp.status_code} {resp.content}")
        return

    # List
    resp = c.get(f'/api/{org_subdomain}/projects/', **headers)
    if resp.status_code == 200 and len(resp.json()) > 0:
        print(f"[OK] Listed Projects: Found {len(resp.json())}")
    else:
        print(f"[FAIL] List Projects: {resp.status_code}")

    # 5. Tickets CRUD
    print(f"\n[4] Testing Tickets CRUD...")
    # Create
    ticket_data = {
        'subject': 'Test Ticket', 
        'description': 'This is a test ticket', 
        'priority': 'high', 
        'project': project_id
    }
    resp = c.post(f'/api/{org_subdomain}/tickets/', ticket_data, content_type='application/json', **headers)
    
    ticket_id_internal = None
    if resp.status_code == 201:
        t_data = resp.json()
        ticket_id_internal = t_data['id']
        print(f"[OK] Created Ticket: {t_data.get('ticket_id')} (ID: {ticket_id_internal})")
    else:
        print(f"[FAIL] Create Ticket failed: {resp.status_code} {resp.content}")

    # List
    resp = c.get(f'/api/{org_subdomain}/tickets/', **headers)
    if resp.status_code == 200:
         print(f"[OK] Listed Tickets: Found {len(resp.json())}")

    # 6. Departments CRUD
    print(f"\n[5] Testing Departments CRUD...")
    
    # Create Department
    dept_data = {'name': f'IT Support {timestamp}'}
    # URL is /api/demo/auth/departments/ because it is in accounts app
    dept_url = f'/api/{org_subdomain}/auth/departments/'
    
    resp = c.post(dept_url, dept_data, content_type='application/json', **headers)
    if resp.status_code == 201:
        print(f"[OK] Created Department: {resp.json()['name']}")
        dept_id = resp.json()['id']
    else:
        print(f"[FAIL] Create Department failed: {resp.status_code} {resp.content}")

    # List Departments
    resp = c.get(dept_url, **headers)
    if resp.status_code == 200:
        print(f"[OK] Listed Departments: Found {len(resp.json())}")
    else:
        print(f"[FAIL] List Departments: {resp.status_code}")
         
    # Clean up
    print(f"\n[6] Cleanup...")
    from apps.tickets.models import Project, Ticket
    if ticket_id_internal:
        Ticket.objects.filter(id=ticket_id_internal).delete()
        print("Deleted Test Ticket")
    Project.objects.filter(id=project_id).delete()
    print("Deleted Test Project")
    
if __name__ == '__main__':
    test_tenant_flow()
