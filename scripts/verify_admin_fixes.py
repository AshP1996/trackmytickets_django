import os
import django
import sys
import json

# Setup Django environment
sys.path.append('/home/ashish/Documents/ticket_system_v1/ticket_system_django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.tickets.models import Project, Ticket
from apps.accounts.models import User, Organization, Department
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.tickets.views import ProjectViewSet

def test_analytics_endpoint():
    print("Testing Analytics Endpoint...")
    factory = APIRequestFactory()
    
    # Get a project and user
    org = Organization.objects.filter(subdomain='demo').first()
    if not org:
        print("FAIL: Demo organization not found")
        return

    project = Project.objects.filter(organization=org).first()
    if not project:
        print("FAIL: No project found in Demo org")
        return
        
    user = User.objects.filter(organization=org, role='admin').first()
    
    # Create request
    view = ProjectViewSet.as_view({'get': 'analytics'})
    request = factory.get(f'/api/projects/{project.id}/analytics')
    request.organization = org
    force_authenticate(request, user=user)
    
    response = view(request, pk=project.id)
    
    if response.status_code == 200:
        data = response.data
        if 'project' in data and 'daily_progress' in data and 'team_stats' in data:
            print("PASS: Analytics endpoint returned expected structure.")
        else:
            print(f"FAIL: Unexpected structure: {data.keys()}")
    else:
        print(f"FAIL: Status code {response.status_code}")
        print(response.data)

def test_department_user_flow():
    print("\nTesting Department/User Creation Flow...")
    org = Organization.objects.filter(subdomain='demo').first()
    
    # 1. Create Department without Assignee (Simulating the deadlock fix)
    dept_name = "TestDeadlockDept"
    dept = Department.objects.create(name=dept_name, organization=org, default_assignee=None)
    print(f"PASS: Created Department '{dept_name}' without assignee.")
    
    # 2. Create User with that Department Name (Simulating the frontend fix)
    user_email = "testdedlock@example.com"
    user = User.objects.create_user(
        email=user_email,
        organization_id=org.id,
        full_name="Test Deadlock User",
        department=dept_name, # Storing Name, as per CharField
        role="agent"
    )
    print(f"PASS: Created User '{user_email}' with department '{user.department}'.")
    
    # 3. Assign User to Department
    dept.default_assignee = user
    dept.save()
    print(f"PASS: Assigned User to Department default assignee.")
    
    # Cleanup
    dept.delete()
    user.delete()
    print("Cleanup complete.")

if __name__ == "__main__":
    try:
        test_analytics_endpoint()
        test_department_user_flow()
    except Exception as e:
        print(f"ERROR: {e}")
