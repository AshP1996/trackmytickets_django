"""
Test Agent and Customer User Login and Functionality
Tests different user roles and their permissions
"""
import os
import sys
import django
import requests

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User, Organization

BASE_URL = "http://localhost:9000"

def test_user_login(email, password, role_name):
    """Test login for a specific user"""
    print(f"\n{'='*70}")
    print(f"Testing {role_name.upper()} Login: {email}")
    print('='*70)
    
    # Login
    login_url = f"{BASE_URL}/api/demo/auth/login/"
    login_data = {"email": email, "password": password}
    
    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            data = response.json()
            token = data.get('access')
            user_data = data.get('user', {})
            
            print(f"✓ Login successful")
            print(f"  User: {user_data.get('email')}")
            print(f"  Role: {user_data.get('role')}")
            print(f"  Department: {user_data.get('department_name', 'N/A')}")
            
            # Test permissions
            test_user_permissions(token, role_name, user_data)
            
            return token
        else:
            print(f"✗ Login failed: {response.status_code}")
            print(f"  Error: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Login error: {e}")
        return None

def test_user_permissions(token, role_name, user_data):
    """Test what the user can access"""
    print(f"\n[Testing {role_name} Permissions]")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Get own profile
    try:
        response = requests.get(f"{BASE_URL}/api/demo/auth/me/", headers=headers)
        if response.status_code == 200:
            print("  ✓ Can access own profile")
        else:
            print(f"  ✗ Cannot access own profile: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Profile error: {e}")
    
    # Test 2: List tickets
    try:
        response = requests.get(f"{BASE_URL}/api/demo/tickets/", headers=headers)
        if response.status_code == 200:
            tickets = response.json()
            ticket_list = tickets.get('results', tickets) if isinstance(tickets, dict) else tickets
            count = len(ticket_list) if isinstance(ticket_list, list) else 0
            print(f"  ✓ Can list tickets: {count} tickets visible")
            
            # Show first ticket if available
            if count > 0 and isinstance(ticket_list, list):
                first_ticket = ticket_list[0]
                print(f"    Sample: {first_ticket.get('ticket_id')} - {first_ticket.get('subject', 'N/A')[:40]}")
        else:
            print(f"  ✗ Cannot list tickets: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Tickets error: {e}")
    
    # Test 3: Create ticket (should work for all roles)
    try:
        ticket_data = {
            "subject": f"Test ticket from {role_name}",
            "description": f"This is a test ticket created by {role_name}",
            "priority": "medium"
        }
        response = requests.post(f"{BASE_URL}/api/demo/tickets/", json=ticket_data, headers=headers)
        if response.status_code == 201:
            ticket = response.json()
            print(f"  ✓ Can create tickets: {ticket.get('ticket_id')}")
            
            # Cleanup - delete the test ticket
            ticket_id = ticket.get('id')
            if ticket_id:
                requests.delete(f"{BASE_URL}/api/demo/tickets/{ticket_id}/", headers=headers)
        else:
            print(f"  ✗ Cannot create tickets: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Create ticket error: {e}")
    
    # Test 4: List projects
    try:
        response = requests.get(f"{BASE_URL}/api/demo/projects/", headers=headers)
        if response.status_code == 200:
            projects = response.json()
            project_list = projects.get('results', projects.get('projects', projects))
            count = len(project_list) if isinstance(project_list, list) else 0
            print(f"  ✓ Can list projects: {count} projects visible")
        else:
            print(f"  ✗ Cannot list projects: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Projects error: {e}")
    
    # Test 5: List users (admin/manager only)
    try:
        response = requests.get(f"{BASE_URL}/api/demo/users/", headers=headers)
        if response.status_code == 200:
            users = response.json()
            user_list = users.get('results', users) if isinstance(users, dict) else users
            count = len(user_list) if isinstance(user_list, list) else 0
            print(f"  ✓ Can list users: {count} users visible")
        elif response.status_code == 403:
            print(f"  ⚠ Cannot list users: Permission denied (expected for {role_name})")
        else:
            print(f"  ✗ Cannot list users: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Users error: {e}")
    
    # Test 6: List departments
    try:
        response = requests.get(f"{BASE_URL}/api/demo/departments/", headers=headers)
        if response.status_code == 200:
            departments = response.json()
            dept_list = departments.get('results', departments) if isinstance(departments, dict) else departments
            count = len(dept_list) if isinstance(dept_list, list) else 0
            print(f"  ✓ Can list departments: {count} departments visible")
        else:
            print(f"  ✗ Cannot list departments: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Departments error: {e}")
    
    # Test 7: Create project (admin/manager only)
    if role_name in ['admin', 'manager']:
        try:
            project_data = {
                "name": f"Test Project {role_name}",
                "key": f"TEST{role_name.upper()}",
                "description": f"Test project by {role_name}"
            }
            response = requests.post(f"{BASE_URL}/api/demo/projects/", json=project_data, headers=headers)
            if response.status_code == 201:
                project = response.json()
                print(f"  ✓ Can create projects: {project.get('key')}")
                
                # Cleanup
                project_id = project.get('id')
                if project_id:
                    requests.delete(f"{BASE_URL}/api/demo/projects/{project_id}/", headers=headers)
            else:
                print(f"  ✗ Cannot create projects: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Create project error: {e}")

def get_user_info_from_db():
    """Get user information from database"""
    print("\n" + "="*70)
    print("DEMO ORGANIZATION USERS")
    print("="*70)
    
    try:
        # Try both possible organization names
        try:
            org = Organization.objects.get(name='demo')
        except Organization.DoesNotExist:
            org = Organization.objects.get(name='Demo Corp')
        
        users = User.objects.filter(organization=org).order_by('role')
        
        print(f"\nOrganization: {org.name}")
        print(f"Total Users: {users.count()}\n")
        
        user_list = []
        for user in users:
            print(f"Email: {user.email}")
            print(f"  Role: {user.role}")
            print(f"  Department: {user.department.name if user.department else 'N/A'}")
            print(f"  Active: {user.is_active}")
            print()
            
            user_list.append({
                'email': user.email,
                'role': user.role,
                'password': 'admin123'  # Default password from setup script
            })
        
        return user_list
    except Organization.DoesNotExist:
        print("✗ Demo organization not found!")
        print("  Available organizations:")
        for org in Organization.objects.all():
            print(f"    - {org.name} (subdomain: {org.subdomain})")
        return []
    except Exception as e:
        print(f"✗ Error getting users: {e}")
        return []

def main():
    print("="*70)
    print("AGENT AND CUSTOMER USER LOGIN TEST")
    print("="*70)
    
    # Get users from database
    users = get_user_info_from_db()
    
    if not users:
        print("\n✗ No users found. Run setup_demo_data.py first.")
        return
    
    # Test each user
    for user in users:
        test_user_login(user['email'], user['password'], user['role'])
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("""
Expected Behavior by Role:

ADMIN:
  ✓ Full access to all features
  ✓ Can create/edit/delete tickets, projects, users, departments
  ✓ Can view all tickets and projects
  ✓ Access to admin panel

MANAGER:
  ✓ Can create/edit tickets and projects
  ✓ Can view all tickets in their department
  ✓ Can assign tickets to agents
  ✓ Limited admin access

AGENT:
  ✓ Can view and respond to assigned tickets
  ✓ Can create tickets
  ✓ Can view tickets in their department
  ✗ Cannot create projects or manage users

CUSTOMER:
  ✓ Can create tickets
  ✓ Can view only their own tickets
  ✓ Can comment on their tickets
  ✗ Cannot access admin features
  ✗ Cannot view other users' tickets
    """)
    
    print("="*70)
    print("To test in browser:")
    print("="*70)
    print("1. Go to http://localhost:9000/demo/login")
    print("2. Try logging in with each user:")
    for user in users:
        print(f"   - {user['email']} / {user['password']} ({user['role']})")
    print("3. Check what features are accessible for each role")
    print("="*70)

if __name__ == '__main__':
    main()
