import os
import django
import sys

# Setup django
sys.path.append('/home/ashish/Documents/ticket_system_v1/ticket_system_django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User, Organization

def create_test_users():
    try:
        tenant = Organization.objects.get(subdomain='demo')
    except Organization.DoesNotExist:
        print("Demo tenant not found. Cannot create users.")
        return

    # Create Manager
    manager_email = 'testmanager1@demo.com'
    manager, created_manager = User.objects.get_or_create(
        email=manager_email,
        defaults={
            'full_name': 'Test Manager',
            'role': 'manager',
            'department': 'Eng',
            'is_active': True,
            'organization_id': tenant.id
        }
    )
    if created_manager:
        manager.set_password('password123')
        manager.save()
        print(f"Created Manager: {manager_email} / password123")
    else:
        # Reset password to ensure it matches
        manager.set_password('password123')
        manager.save()
        print(f"Found existing Manager: {manager_email}. Password reset to 'password123'.")

    # Create Agent
    agent_email = 'testagent1@demo.com'
    agent, created_agent = User.objects.get_or_create(
        email=agent_email,
        defaults={
            'full_name': 'Test Agent',
            'role': 'agent',
            'department': 'Eng',
            'is_active': True,
            'organization_id': tenant.id
        }
    )
    if created_agent:
        agent.set_password('password123')
        agent.save()
        print(f"Created Agent: {agent_email} / password123")
    else:
        # Reset password to ensure it matches
        agent.set_password('password123')
        agent.save()
        print(f"Found existing Agent: {agent_email}. Password reset to 'password123'.")

    # Print summary format for the user
    print("\n--- Test Users Ready ---")
    print(f"Manager Login: {manager_email} / password123")
    print(f"Agent Login: {agent_email} / password123")
    print("Please use the above credentials to test on http://localhost:8000/demo/login")

if __name__ == '__main__':
    create_test_users()
