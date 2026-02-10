import sys
import os
import django

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User, Organization

def check_new_org_admin():
    try:
        # Find the organization
        org = Organization.objects.get(subdomain='newtestco')
        print(f"Organization found: {org.name}")
        print(f"Organization ID: {org.id}")
        print(f"Is active: {org.is_active}")
        
        # Find the admin user
        admin = User.objects.filter(organization=org, email='admin@newtestco.com').first()
        
        if admin:
            print(f"\nAdmin user found:")
            print(f"Email: {admin.email}")
            print(f"Full name: {admin.full_name}")
            print(f"Role: {admin.role}")
            print(f"Is active: {admin.is_active}")
            print(f"Has usable password: {admin.has_usable_password()}")
            
            # Try to verify the password
            if admin.check_password('admin123'):
                print("\n✅ Password 'admin123' is CORRECT")
            else:
                print("\n❌ Password 'admin123' is INCORRECT")
                print("Resetting password to 'admin123'...")
                admin.set_password('admin123')
                admin.save()
                print("✅ Password has been reset")
        else:
            print(f"\n❌ Admin user NOT found for email: admin@newtestco.com")
            print("\nAll users in this organization:")
            users = User.objects.filter(organization=org)
            for user in users:
                print(f"  - {user.email} ({user.role})")
                
    except Organization.DoesNotExist:
        print("❌ Organization 'newtestco' NOT found")
        print("\nAll organizations:")
        orgs = Organization.objects.all()
        for org in orgs:
            print(f"  - {org.subdomain}: {org.name}")

if __name__ == "__main__":
    check_new_org_admin()
