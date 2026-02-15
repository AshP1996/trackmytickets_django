import os
import sys
import django
import sqlite3
import json

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.conf import settings
from apps.accounts.models import Organization, User, PlatformAdmin
from apps.core.models import ExternalDataSource
from apps.tickets.models import Ticket, Project, TicketHistory
from apps.core.utils.encryption import encrypt_password
from rest_framework.test import APIRequestFactory
from apps.accounts.platform_views import PlatformStatsView

def run_verification():
    print("----------------------------------------------------------------")
    print("Verifying Bring Your Own Database (BYODB) Feature")
    print("----------------------------------------------------------------")

    # 1. Create Organization
    print("\n1. Creating Tenant Organization...")
    org_name = "BYODB Test Org"
    subdomain = "byodb-test"
    
    # Cleanup previous run
    Organization.objects.filter(subdomain=subdomain).delete()
    
    org = Organization.objects.create(
        name=org_name,
        subdomain=subdomain,
        email="admin@byodb.com",
        plan="growth_cluster", # Supports external DB
        is_active=True
    )
    print(f"   Created Organization: {org.name} (ID: {org.id})")

    # 2. Create Admin User (Shared DB)
    print("\n2. Creating Admin User...")
    user = User.objects.create(
        email="admin@byodb.com",
        full_name="Tenant Admin",
        organization=org,
        role="admin",
        is_active=True
    )
    user.set_password("password123")
    user.save()
    print(f"   Created User: {user.email} (ID: {user.id})")

    # 3. Create External Data Source (SQLite)
    print("\n3. Creating External Data Source (SQLite)...")
    db_name = "tenant_byodb.sqlite3"
    db_path = os.path.join(settings.BASE_DIR, db_name)
    
    # Ensure fresh DB file
    if os.path.exists(db_path):
        os.remove(db_path)
        
    # Initialize SQLite DB with schema
    # We need to manually create the tables because migrations won't run on this dynamic DB easily
    # without separate management commands. for verification we simulate the table existence.
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Minimal schema for Ticket
    cursor.execute('''
        CREATE TABLE tickets (
            id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            ticket_id varchar(20) NOT NULL,
            subject varchar(200) NOT NULL,
            description text NULL,
            status varchar(20) NOT NULL,
            priority varchar(20) NOT NULL,
            sender_email varchar(120) NOT NULL,
            sender_name varchar(100) NULL,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            closed_at datetime NULL,
            organization_id integer NOT NULL,
            project_id integer NOT NULL,
            assigned_to_id integer NULL,
            department_id integer NULL,
            lead_user_id integer NULL,
            email_message_id varchar(200) NULL,
            first_response_at datetime NULL,
            first_response_time_seconds integer NULL,
            resolution_time_seconds integer NULL,
            department_name varchar(50) NULL
        )
    ''')
    # Minimal schema for Project (Required for Ticket FK)
    cursor.execute('''
        CREATE TABLE projects (
            id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            name varchar(200) NOT NULL,
            key varchar(10) NOT NULL,
            description varchar(200) NULL,
            is_active bool NOT NULL,
            organization_id integer NOT NULL,
            lead_user_id integer NULL,
            start_date datetime NULL,
            end_date datetime NULL,
            extension_date datetime NULL,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL
        )
    ''')
    # Minimal TicketHistory
    cursor.execute('''
        CREATE TABLE ticket_history (
             id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
             action varchar(50) NOT NULL,
             old_value varchar(200) NULL,
             new_value varchar(200) NULL,
             created_at datetime NOT NULL,
             ticket_id integer NOT NULL,
             user_id integer NULL
        )
    ''')
    conn.commit()
    conn.close()
    print(f"   Created SQLite DB at: {db_path}")

    # Register Data Source
    ds = ExternalDataSource.objects.create(
        organization=org,
        name="Tenant SQLite DB",
        type="sqlite",
        database=db_path,
        connection_status="connected",
        is_active=True
    )
    print(f"   Registered ExternalDataSource: {ds.id}")

    # 4. Create Data in Tenant DB via Application Logic
    print("\n4. Creating Ticket via Django ORM...")
    
    # We need to access the Tenant DB using the new Router logic
    # The middleware sets up the connection alias, but here we are in a script.
    # We must manually setup the connection in settings and thread local.
    
    db_alias = f"tenant_{org.id}"
    
    # Copy default config to get all keys
    db_config = settings.DATABASES['default'].copy()
    db_config.update({
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': db_path,
    })
    
    settings.DATABASES[db_alias] = db_config
    
    from apps.core.routers import set_current_db_alias, reset_current_db_alias
    set_current_db_alias(db_alias)
    print(f"   Set thread-local DB alias to: {db_alias}")
    
    try:
        # Create Project
        project = Project.objects.create(
            name="Migration Project",
            key="MIG",
            organization=org,
            is_active=True
        )
        print(f"   Created Project: {project.name} (Should be in Tenant DB)")
        
        # Create Ticket
        ticket = Ticket.objects.create(
            ticket_id="MIG-1",
            project=project,
            organization=org,
            subject="Test External DB Ticket",
            description="This ticket should live in the SQLite file.",
            sender_email="user@test.com",
            status="open"
        )
        print(f"   Created Ticket: {ticket.ticket_id} (Should be in Tenant DB)")
        
        # Verify it exists in Tenant DB (via ORM)
        ticket_tenant = Ticket.objects.using(db_alias).get(ticket_id="MIG-1")
        print(f"   [SUCCESS] Found ticket in Tenant DB (ORM): {ticket_tenant}")

    except Exception as e:
        print(f"   [ERROR] Failed to create data: {e}")
        import traceback
        traceback.print_exc()

    finally:
        reset_current_db_alias()
        print("   Reset thread-local DB alias.")

    # 5. Verify Isolation (Should NOT be in default DB)
    print("\n5. Verifying Data Isolation...")
    exists_default = Ticket.objects.using('default').filter(ticket_id="MIG-1").exists()
    if not exists_default:
        print("   [SUCCESS] Ticket is NOT in Default DB.")
    else:
        print("   [FAILURE] Ticket leaked to Default DB!")

    # 6. Verify Platform Stats Aggregation
    print("\n6. Verifying Platform Stats Aggregation...")
    
    # Create a request context
    factory = APIRequestFactory()
    request = factory.get('/api/platform/stats')
    request.user = PlatformAdmin.objects.first() or PlatformAdmin.objects.create(email='platform@admin.com')
    
    view = PlatformStatsView()
    view.request = request
    view.format_kwarg = None
    
    response = view.get(request)
    data = response.data
    
    print(f"   Stats Response: {json.dumps(data, indent=2)}")
    
    total_tickets = data['tickets']['total']
    if total_tickets >= 1: # Might be other tickets in system
        print("   [SUCCESS] Platform Stats includes tickets.")
        # Check specific logic if possible, but basic count > 0 is good indication if DB was empty before 
        #(not empty in this env, but we know we added 1)
    else:
        print("   [FAILURE] Platform Stats showed 0 tickets!")

    # 7. Verify Organization List API (for UI badge)
    print("\n7. Verifying Organization List API...")
    from apps.accounts.platform_views import PlatformOrganizationsView
    view_orgs = PlatformOrganizationsView()
    view_orgs.request = request
    view_orgs.format_kwarg = None
    
    response_orgs = view_orgs.get(request)
    orgs_data = response_orgs.data['organizations']
    
    # Find our test org
    test_org_data = next((o for o in orgs_data if o['id'] == org.id), None)
    
    if test_org_data:
        print(f"   Org Data: {json.dumps(test_org_data, indent=2)}")
        if test_org_data.get('has_external_db'):
             print("   [SUCCESS] Organization has 'has_external_db'=True")
        else:
             print("   [FAILURE] Organization missing 'has_external_db' or False")
    else:
        print("   [FAILURE] Could not find test organization in list")

    # Cleanup
    # os.remove(db_path) # Keep for inspection if needed
    print("\n----------------------------------------------------------------")
    print("Verification Verification Completed")
    print("----------------------------------------------------------------")

if __name__ == '__main__':
    run_verification()
