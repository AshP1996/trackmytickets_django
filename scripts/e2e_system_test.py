import os
import sys
import django
import json
import logging
from datetime import timedelta

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.test import RequestFactory
from django.conf import settings
from apps.accounts.models import Organization, User, PlatformAdmin, Department
from apps.tickets.models import Ticket, Project, TicketHistory
from apps.comments.models import Comment
from apps.notifications.models import Notification
from apps.core.models import Enquiry, ExternalDataSource
from apps.accounts.platform_views import PlatformOrganizationsView, PlatformStatsView
from rest_framework.test import APIRequestFactory, force_authenticate

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemTester:
    def __init__(self):
        self.factory = APIRequestFactory()
        self.platform_admin = None
        self.org_standard = None
        self.org_byodb = None
        self.admin_standard = None
        self.admin_byodb = None
        self.agent_standard = None

    def setup_platform_admin(self):
        logger.info("[SETUP] Creating Platform Admin...")
        self.platform_admin, _ = PlatformAdmin.objects.get_or_create(email="tester_platform@admin.com")
        self.platform_admin.set_password("pass")
        self.platform_admin.save()

    def test_platform_flow(self):
        logger.info("\n=== SCENARIO 1: PLATFORM ADMIN FLOW ===")
        
        # 1. Login (Simulation via API call logic)
        # We assume auth works if we can make authenticated calls
        
        # 2. Get Stats
        logger.info("   -> Fetching Platform Stats...")
        view = PlatformStatsView.as_view()
        request = self.factory.get('/api/platform/stats')
        force_authenticate(request, user=self.platform_admin)
        response = view(request)
        if response.status_code == 200:
            logger.info(f"   [SUCCESS] Stats fetched: {json.dumps(response.data, indent=2)}")
        else:
            logger.error(f"   [FAILURE] Stats fetch failed: {response.status_code}")

        # 3. Create Standard Organization
        logger.info("   -> Creating Standard Organization...")
        view_orgs = PlatformOrganizationsView.as_view()
        data = {
            "name": "Standard Test Org",
            "subdomain": "std-test-org",
            "email": "contact@std.com",
            "admin_email": "admin@std.com",
            "admin_name": "Std Admin",
            "admin_password": "password123",
            "plan": "starter_trial"
        }
        # Cleanup
        Organization.objects.filter(subdomain=data['subdomain']).delete()
        
        request = self.factory.post('/api/platform/organizations', data, format='json')
        force_authenticate(request, user=self.platform_admin)
        response = view_orgs(request)
        
        if response.status_code == 201:
            self.org_standard = Organization.objects.get(subdomain=data['subdomain'])
            self.admin_standard = User.objects.get(email=data['admin_email'])
            logger.info(f"   [SUCCESS] Created Standard Org: {self.org_standard.name} (ID: {self.org_standard.id})")
        else:
            logger.error(f"   [FAILURE] Create Org failed: {response.data}")

    def test_org_admin_flow(self):
        logger.info("\n=== SCENARIO 2: ORG ADMIN FLOW (Standard DB) ===")
        if not self.org_standard:
            logger.error("   [SKIP] No Standard Org created.")
            return

        # Simulate Middleware setting organization
        request_context = {'organization': self.org_standard}

        # 1. Create Department
        logger.info("   -> Creating Department...")
        dept = Department.objects.create(
            name="Support",
            organization=self.org_standard
        )
        logger.info(f"   [SUCCESS] Department Created: {dept.name}")

        # 2. Create Agent User
        logger.info("   -> Creating Agent User...")
        self.agent_standard = User.objects.create(
            email="agent@std.com",
            full_name="Agent Smith",
            organization=self.org_standard,
            role="agent",
            department=dept.name
        )
        self.agent_standard.set_password("agentpass")
        self.agent_standard.save()
        logger.info(f"   [SUCCESS] Agent Created: {self.agent_standard.email}")

        # 3. Create Project
        logger.info("   -> Creating Project...")
        project = Project.objects.create(
            name="Main Project",
            key="MAIN",
            organization=self.org_standard,
            lead_user=self.admin_standard
        )
        logger.info(f"   [SUCCESS] Project Created: {project.name}")

    def test_ticket_flow(self):
        logger.info("\n=== SCENARIO 3: TICKET LIFECYCLE & NOTIFICATIONS ===")
        if not self.org_standard: return

        # 1. Create Ticket
        logger.info("   -> Creating Ticket...")
        project = Project.objects.get(organization=self.org_standard, key="MAIN")
        ticket = Ticket.objects.create(
            ticket_id="MAIN-1",
            project=project,
            organization=self.org_standard,
            subject="Help me!",
            description="System is down.",
            sender_email="customer@example.com",
            status="open"
        )
        logger.info(f"   [SUCCESS] Ticket Created: {ticket.ticket_id}")

        # 2. Add Comment (by Agent)
        logger.info("   -> Agent Adding Comment...")
        comment = Comment.objects.create(
            ticket=ticket,
            user=self.agent_standard,
            comment="Looking into it.",
            is_internal=False
        )
        logger.info(f"   [SUCCESS] Comment Added: {comment.id}")

        # 3. Verify Notification Storage
        logger.info("   -> Generating Notification and verifying storage...")
        # Simulate notification logic
        notification = Notification.objects.create(
            user=self.admin_standard, # Notify admin
            actor=self.agent_standard,
            ticket=ticket,
            type="comment",
            message=f"New comment on {ticket.ticket_id}"
        )
        
        # Check DB alias
        db_alias = notification._state.db
        logger.info(f"   [INFO] Notification saved to DB alias: {db_alias}")
        
        # Verify it is in 'default' for Standard Org
        exists_default = Notification.objects.using('default').filter(id=notification.id).exists()
        if exists_default:
            logger.info("   [SUCCESS] Notification found in Default DB (Correct for Standard Org)")
        else:
            logger.error("   [FAILURE] Notification NOT found in Default DB!")

    def test_byodb_flow(self):
        logger.info("\n=== SCENARIO 4: BYODB FLOW ===")
        
        # 1. Create BYODB Org
        logger.info("   -> Creating BYODB Org...")
        org_name = "BYODB Auto Test"
        subdomain = "byodb-auto"
        Organization.objects.filter(subdomain=subdomain).delete()
        
        self.org_byodb = Organization.objects.create(
            name=org_name,
            subdomain=subdomain,
            email="admin@byodb.com",
            plan="growth_cluster",
            is_active=True
        )
        
        # 2. Setup SQLite DB
        db_path = os.path.join(settings.BASE_DIR, "test_byodb_auto.sqlite3")
        import sqlite3
        if os.path.exists(db_path): os.remove(db_path)
        
        # Init Schema (Same as verify_byodb.py)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE tickets (id integer PRIMARY KEY AUTOINCREMENT, ticket_id varchar(20), subject varchar(200), description text, status varchar(20), priority varchar(20), sender_email varchar(120), sender_name varchar(100), created_at datetime, updated_at datetime, closed_at datetime, organization_id integer, project_id integer, assigned_to_id integer, department_id integer, lead_user_id integer, email_message_id varchar(200), first_response_at datetime, first_response_time_seconds integer, resolution_time_seconds integer, department_name varchar(50))')
        cursor.execute('CREATE TABLE projects (id integer PRIMARY KEY AUTOINCREMENT, name varchar(200), key varchar(10), description varchar(200), is_active bool, organization_id integer, lead_user_id integer, start_date datetime, end_date datetime, extension_date datetime, created_at datetime, updated_at datetime)')
        cursor.execute('CREATE TABLE notifications (id integer PRIMARY KEY AUTOINCREMENT, user_id integer, actor_id integer, ticket_id integer, type varchar(50), message varchar(500), is_read bool, link varchar(500), created_at datetime)')
        conn.commit()
        conn.close()
        
        ExternalDataSource.objects.create(
            organization=self.org_byodb,
            name="Auto SQLite",
            type="sqlite",
            database=db_path,
            connection_status="connected",
            is_active=True
        )
        logger.info(f"   [SUCCESS] BYODB Org & DB configured: {db_path}")

        # 3. Create Ticket in BYODB
        logger.info("   -> Creating Ticket in BYODB...")
        
        # Manually configure router context (simulating middleware)
        db_alias = f"tenant_{self.org_byodb.id}"
        # Copy default config to ensure all keys present
        db_config = settings.DATABASES['default'].copy()
        db_config.update({
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_path,
        })
        settings.DATABASES[db_alias] = db_config
        
        from apps.core.routers import set_current_db_alias, reset_current_db_alias
        set_current_db_alias(db_alias)
        
        try:
            # Create Project & Ticket
            project = Project.objects.create(name="Byo Proj", key="BYO", organization=self.org_byodb)
            ticket = Ticket.objects.create(
                ticket_id="BYO-1",
                project=project,
                organization=self.org_byodb,
                subject="Data Isolation Test",
                status="open"
            )
            logger.info(f"   [SUCCESS] Ticket Created in BYODB: {ticket.ticket_id}")
            
            # 4. Create Notification in BYODB
            logger.info("   -> Creating Notification in BYODB...")
            # Create a user for notification (User is in Default DB)
            # We need a user ID that exists or just mock it since db_constraint=False
            # But better to use a real user object to satisfy Django ORM
            
            # create a dummy user
            notify_user = User.objects.create(
                email="notify@byodb.com", 
                full_name="Notify User", 
                organization=self.org_byodb
            )
            
            # Notification is Tenant DB. Relation to User is Cross-DB (allowed by router)
            notif = Notification.objects.create(
                user=notify_user, 
                ticket=ticket,
                type="test",
                message="Data Isolation Check"
            )
            logger.info(f"   [SUCCESS] Notification Created: {notif.id}")
            
            # Verify Isolation
            # Check by content, not just ID, as ID=1 likely exists in Default DB
            exists_default = Notification.objects.using('default').filter(
                id=notif.id, 
                message="Data Isolation Check"
            ).exists()
            
            if not exists_default:
                logger.info("   [SUCCESS] Notification NOT found in Default DB (Correct Isolation)")
            else:
                logger.error("   [FAILURE] Notification LEAKED to Default DB!")
                
        except Exception as e:
            logger.error(f"   [FAILURE] BYODB Operation failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            reset_current_db_alias()

    def run_all(self):
        self.setup_platform_admin()
        self.test_platform_flow()
        self.test_org_admin_flow()
        self.test_ticket_flow()
        self.test_byodb_flow()
        logger.info("\n=== TEST SUITE COMPLETED ===")

if __name__ == "__main__":
    tester = SystemTester()
    tester.run_all()
