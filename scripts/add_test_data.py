
import os
import sys
import django
from django.utils import timezone
from datetime import timedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User, PlatformAdmin, Organization, Department
from apps.tickets.models import Project, Ticket, TicketHistory

def create_test_data():
    print("Starting test data creation...")

    # 1. Create Platform Admin
    admin_email = "admin@platform.com"
    if not PlatformAdmin.objects.filter(email=admin_email).exists():
        admin = PlatformAdmin(email=admin_email)
        admin.set_password("adminpassword")
        admin.save()
        print(f"Created Platform Admin: {admin_email} / adminpassword")
    else:
        print(f"Platform Admin {admin_email} already exists.")

    # 2. Create Organization
    org_name = "Demo Corp"
    org_subdomain = "demo"
    if not Organization.objects.filter(subdomain=org_subdomain).exists():
        org = Organization.objects.create(
            name=org_name,
            subdomain=org_subdomain,
            email="contact@democorp.com",
            plan="pro"
        )
        print(f"Created Organization: {org_name} ({org_subdomain})")
    else:
        org = Organization.objects.get(subdomain=org_subdomain)
        print(f"Organization {org_name} already exists.")

    # 3. Create Users
    users_data = [
        {"email": "admin@democorp.com", "name": "Admin User", "role": "admin", "password": "password123"},
        {"email": "head@democorp.com", "name": "Head User", "role": "manager", "password": "password123"},
        {"email": "agent@democorp.com", "name": "Agent User", "role": "agent", "password": "password123"},
        {"email": "user@democorp.com", "name": "Regular User", "role": "customer", "password": "password123"} # Assuming customer/regular user role logic
    ]

    for u_data in users_data:
        if not User.objects.filter(email=u_data["email"]).exists():
            user = User.objects.create_user(
                email=u_data["email"], 
                organization_id=org.id, 
                password=u_data["password"],
                full_name=u_data["name"],
                role=u_data["role"]
            )
            print(f"Created User: {u_data['email']} / {u_data['password']} ({u_data['role']})")
        else:
            print(f"User {u_data['email']} already exists.")

    # 4. Create Departments
    departments = ["Support", "IT", "Sales"]
    for dep_name in departments:
        if not Department.objects.filter(name=dep_name, organization=org).exists():
            Department.objects.create(name=dep_name, organization=org)
            print(f"Created Department: {dep_name}")
        else:
            print(f"Department {dep_name} already exists.")

    # 5. Create Project
    project_key = "SUP"
    if not Project.objects.filter(key=project_key, organization=org).exists():
        project = Project.objects.create(
            name="Support Project",
            key=project_key,
            organization=org,
            description="Main support project for tickets"
        )
        print(f"Created Project: {project.name} ({project.key})")
    else:
        project = Project.objects.get(key=project_key, organization=org)
        print(f"Project {project.name} already exists.")

    # 6. Create Tickets
    agent = User.objects.get(email="agent@democorp.com")
    department = Department.objects.get(name="Support", organization=org)

    tickets_data = [
        {"subject": "Cannot login to dashboard", "status": "open", "priority": "high"},
        {"subject": "Feature request: Dark mode", "status": "open", "priority": "low"},
        {"subject": "Bug verification", "status": "in_progress", "priority": "medium"},
        {"subject": "Resolved issue", "status": "resolved", "priority": "medium"}
    ]

    for i, t_data in enumerate(tickets_data):
        # Check if similar ticket exists to avoid dups on re-run (simple check)
        if not Ticket.objects.filter(subject=t_data["subject"], organization=org).exists():
            ticket_id = Ticket.generate_ticket_id(project.key, project.id)
            ticket = Ticket.objects.create(
                ticket_id=ticket_id,
                project=project,
                organization=org,
                subject=t_data["subject"],
                description=f"Description for {t_data['subject']}",
                status=t_data["status"],
                priority=t_data["priority"],
                department=department,
                sender_email="customer@example.com",
                sender_name="Customer Name",
                assigned_to=agent if t_data["status"] != "open" else None
            )
            print(f"Created Ticket: {ticket.ticket_id} - {ticket.subject}")
            
            # Add some history
            TicketHistory.objects.create(
                ticket=ticket,
                action="created",
                created_at=timezone.now() - timedelta(days=1)
            )
        else:
            print(f"Ticket '{t_data['subject']}' already exists.")

    print("Test data creation completed.")

if __name__ == '__main__':
    create_test_data()
