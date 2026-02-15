import os
import sys
import django
import requests
import json
import time
from django.conf import settings
from django.core.management import call_command

# ==================================================================================
# PART 1: SETUP (Django ORM)
# ==================================================================================

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod_override')
django.setup()

from apps.accounts.models import Organization, User
from apps.core.models import ExternalDataSource

BASE_URL = "http://localhost:8000/api"

def setup_omega():
    print("\n[SETUP] Provisioning Omega Corp...")
    
    # 1. Create Organization
    org, created = Organization.objects.get_or_create(
        subdomain='omega',
        defaults={
            'name': 'Omega Corp',
            'email': 'admin@omega.com',
            'plan': 'pro',
            'is_active': True
        }
    )
    if created: print(f"  [+] Created Org: {org.name}")
    else: print(f"  [.] Org exists: {org.name}")

    # 2. Tenant DB
    db_path = "/tmp/omega.db"
    ds, ds_created = ExternalDataSource.objects.get_or_create(
        organization=org,
        name='Omega SQLite DB',
        defaults={
            'type': 'sqlite',
            'database': db_path,
            'is_active': True,
            'connection_status': 'connected'
        }
    )
    if ds_created: print(f"  [+] Created DB Source: {db_path}")
    
    # 3. Migrate DB
    print("  [>] Migrating Tenant DB...")
    db_alias = 'tenant_omega'
    db_config = settings.DATABASES['default'].copy()
    db_config['ENGINE'] = 'django.db.backends.sqlite3'
    db_config['NAME'] = db_path
    db_config['OPTIONS'] = {}
    settings.DATABASES[db_alias] = db_config
    
    try:
        call_command('migrate', database=db_alias, verbosity=0)
        print("  [+] Migration successful")
    except Exception as e:
        print(f"  [!] Migration failed: {e}")
        return False

    # 4. Create Users
    users = [
        {'email': 'admin@omega.com', 'role': 'admin', 'name': 'Omega Admin'},
        {'email': 'manager@omega.com', 'role': 'manager', 'name': 'Omega Manager'},
        {'email': 'agent@omega.com', 'role': 'agent', 'name': 'Omega Agent'},
        {'email': 'customer@omega.com', 'role': 'customer', 'name': 'Omega Customer'},
    ]
    
    for u in users:
        if not User.objects.filter(email=u['email'], organization=org).exists():
            user = User.objects.create(
                email=u['email'],
                organization=org,
                full_name=u['name'],
                role=u['role'],
                is_active=True
            )
            user.set_password('password123')
            user.save()
            print(f"  [+] Created User: {u['email']} ({u['role']})")
        else:
            print(f"  [.] User exists: {u['email']}")
            
    return True

# ==================================================================================
# PART 2: TEST FLOW (API Requests)
# ==================================================================================

class APIClient:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.token = None
        self.headers = {'Content-Type': 'application/json'}
        self.base_url = f"{BASE_URL}/omega"
        
    def login(self):
        url = f"{self.base_url}/auth/login/"
        resp = requests.post(url, json={'email': self.email, 'password': self.password})
        if resp.status_code == 200:
            self.token = resp.json()['access_token']
            self.headers['Authorization'] = f"Bearer {self.token}"
            return True
        print(f"  [!] Login failed for {self.email}: {resp.text}")
        return False
        
    def get(self, endpoint):
        return requests.get(f"{self.base_url}/{endpoint}", headers=self.headers)
        
    def post(self, endpoint, data):
        return requests.post(f"{self.base_url}/{endpoint}", json=data, headers=self.headers)
        
    def put(self, endpoint, data):
        return requests.put(f"{self.base_url}/{endpoint}", json=data, headers=self.headers)
        
    def patch(self, endpoint, data):
        return requests.patch(f"{self.base_url}/{endpoint}", json=data, headers=self.headers)

def run_test_scenario():
    print("\n[TEST] Starting Workflow Simulation...")
    
    # Clients
    admin = APIClient('admin@omega.com', 'password123')
    manager = APIClient('manager@omega.com', 'password123')
    agent = APIClient('agent@omega.com', 'password123')
    customer = APIClient('customer@omega.com', 'password123')
    
    # 1. Login all
    print("  [1] Logging in users...")
    if not all([admin.login(), manager.login(), agent.login(), customer.login()]):
        print("  [!] Failed to login users.")
        return

    # 1.5 Admin fetches users to find Manager ID
    print("  [1.5] Admin fetching users...")
    resp = admin.get('auth/users/')
    if resp.status_code != 200:
        print(f"  [!] Failed to fetch users: {resp.text}")
        return
    users = resp.json()['results']
    manager_user = next((u for u in users if u['email'] == 'manager@omega.com'), None)
    if not manager_user:
        print("  [!] Manager user not found")
        return
        
    # 2. Admin Creates Project
    print("  [2] Admin creating project 'Omega Migration'...")
    import random
    suffix = random.randint(1000, 9999)
    proj_key = f"OMG{suffix}"
    
    resp = admin.post('projects/', {
        "name": f"Omega Migration {suffix}",
        "key": proj_key,
        "description": "Migration to new system",
        "start_date": "2026-03-01",
        "end_date": "2026-06-30",
        "lead_user": manager_user['id']
    })
    if resp.status_code != 201:
        print(f"  [!] Project creation failed: {resp.text}")
        return
    project = resp.json()
    project_id = project['id']
    print(f"  [+] Project created: {project['name']} (ID: {project_id})")
    
    # 3. Customer Creates Ticket
    print("  [3] Customer creating ticket...")
    resp = customer.post('tickets/', {
        "subject": "Login page is slow",
        "description": "It takes 5 seconds to load.",
        "priority": "high",
        "project": project_id
    })
    if resp.status_code != 201:
        print(f"  [!] Ticket creation failed: {resp.text}")
        return
    ticket = resp.json()
    ticket_id = ticket['id']
    print(f"  [+] Ticket created: {ticket['ticket_id']}")
    
    # 4. Admin Checks Dashboard
    print("  [4] Admin checking dashboard...")
    resp = admin.get('tickets/stats/')
    stats = resp.json()
    if stats['total'] >= 1:
        print(f"  [+] Admin sees {stats['total']} tickets.")
    else:
        print(f"  [!] Admin sees incorrect stats: {stats}")
        
    # 5. Manager Assigns to Agent
    # Need User ID of agent
    # In a real app, manager would search users. Here we cheat and get ID from setup or assume.
    # We can fetch user list as manager
    resp = manager.get('auth/users/')
    users = resp.json()['results']
    agent_user = next((u for u in users if u['email'] == 'agent@omega.com'), None)
    if not agent_user:
        print("  [!] Agent user not found in list")
        return
        
    print(f"  [5] Manager assigning ticket to Agent {agent_user['id']}...")
    resp = manager.post(f'tickets/{ticket_id}/assign/', {'user_id': agent_user['id']})
    if resp.status_code == 200:
        print("  [+] Ticket assigned successfully")
    else:
        print(f"  [!] Assign failed: {resp.text}")
        
    # 6. Agent Adds Comment
    print("  [6] Agent adding internal comment...")
    resp = agent.post(f'tickets/{ticket_id}/comments/', {
        "comment": "Investigating the slow query log.",
        "is_internal": True
    })
    if resp.status_code == 201:
        print("  [+] Comment added")
    else:
        print(f"  [!] Comment failed: {resp.text}")
        
    # 7. Agent Resolves Ticket
    print("  [7] Agent resolving ticket...")
    resp = agent.patch(f'tickets/{ticket_id}/', {
        "status": "resolved"
    })
    if resp.status_code == 200 and resp.json()['status'] == 'resolved':
        print("  [+] Ticket resolved")
    else:
        print(f"  [!] Resolve failed: {resp.text}")
        
    # 8. Verify agent stats
    print("  [8] Verifying Agent Stats...")
    resp = agent.get('tickets/stats/')
    stats = resp.json()
    # Agent should see 1 assigned
    if stats.get('my_assigned') == 1:
         print("  [+] Agent stats correct: 1 assigned")
    else:
         print(f"  [!] Agent stats incorrect: {stats}")

    # 9. Verify Notifications
    print("  [9] Verifying Notifications...")
    resp = agent.get('notifications/')
    if resp.status_code == 200:
        notifs = resp.json()
        count = notifs.get('count', len(notifs.get('results', []))) # Handle pagination or list
        if count > 0:
            print(f"  [+] Agent has {count} notifications")
        else:
            print(f"  [!] Agent has 0 notifications (Expected > 0)")
    else:
        print(f"  [!] Failed to fetch notifications: {resp.text}")

    print("\n[SUCCESS] Full System Test Completed!")

if __name__ == '__main__':
    if setup_omega():
        run_test_scenario()
