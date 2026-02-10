import sys
import os
import django

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User, Organization, Department

def list_org_users():
    try:
        # Find the organization
        org = Organization.objects.get(subdomain='newtestco')
        print(f"Organization: {org.name} ({org.subdomain})")
        print(f"=" * 60)
        
        # List all departments
        departments = Department.objects.filter(organization=org)
        print(f"\nDepartments ({departments.count()}):")
        for dept in departments:
            print(f"  - {dept.name}")
        
        # List all users
        users = User.objects.filter(organization=org)
        print(f"\nUsers ({users.count()}):")
        for user in users:
            if hasattr(user, 'department') and user.department:
                if isinstance(user.department, str):
                    dept_name = user.department
                else:
                    dept_name = user.department.name
            else:
                dept_name = "No Department"
            print(f"  - {user.full_name} ({user.email})")
            print(f"    Role: {user.role}, Department: {dept_name}, Active: {user.is_active}")
                
    except Organization.DoesNotExist:
        print("❌ Organization 'newtestco' NOT found")

if __name__ == "__main__":
    list_org_users()
