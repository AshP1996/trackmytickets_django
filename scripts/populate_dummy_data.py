import os
import django
import random
from datetime import timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.accounts.models import UserRole, Department, Organization
from apps.tickets.models import Ticket, Project
from apps.comments.models import Comment

User = get_user_model()

def create_dummy_data():
    print("Starting data population...")

    # Ensure organization exists
    org, created = Organization.objects.get_or_create(
        name="TechFlow Solutions",
        defaults={"subdomain": "techflow", "email": "admin@techflow.com"}
    )
    if created:
        print(f"Created organization: {org.name}")
    else:
        print(f"Using existing organization: {org.name}")

    # Create Departments
    departments = [
        "Marketing", "Legal", "Finance", "Operations", "Product", "Security"
    ]
    
    dept_objs = []
    for dept_name in departments:
        dept, created = Department.objects.get_or_create(
            name=dept_name,
            organization=org
        )
        if created:
            print(f"Created department: {dept_name}")
        dept_objs.append(dept)

    # Create Users
    # 1. Department Heads / Managers
    managers = []
    for dept in dept_objs:
        email = f"head.{dept.name.lower()}@techflow.com"
        # User model uses email as username equivalent, no username field
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": f"Head {dept.name}",
                "role": "manager",
                "organization": org,
                "department": str(dept.id), # Model has CharField for department? Or is it name? 
                                            # Viewing models.py: department = models.CharField(max_length=50...)
                                            # But logic usually expects ID for joins, or Name?
                                            # Given generic usage, let's store Name for now if it's CharField,
                                            # OR check if it really should be FK. 
                                            # Utils.js and other parts seem to load departments by ID.
                                            # Let's check how it's used. detailed.html uses department_id.
                                            # But User model has charfield. 
                                            # I will store the ID as string to be safe if that's the convention, 
                                            # or name if it's just display. 
                                            # Let's use ID as string since we have Department objects.
                "is_active": True,
                "is_onboarded": True
            }
        )
        if created:
            user.set_password("password123")
            user.department = str(dept.id) # Explicitly set department ID string
            user.save()
            print(f"Created manager: {user.email}")
        managers.append(user)

    # 2. Agents
    agents = []
    for i in range(1, 6):
        email = f"agent.support{i}@techflow.com"
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": f"Support Agent {i}",
                "role": "agent",
                "organization": org,
                "is_active": True,
                "is_onboarded": True,
                # Assign to first department "Marketing" for now
                "department": str(dept_objs[0].id)
            }
        )
        if created:
            user.set_password("password123")
            user.save()
            print(f"Created agent: {user.email}")
        agents.append(user)

    # 3. Customers
    customers = []
    for i in range(1, 11):
        email = f"customer{i}@client.com"
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": f"Client User {i}",
                "role": "customer",
                "organization": org,
                "is_active": True,
                "is_onboarded": True
            }
        )
        if created:
            user.set_password("password123")
            user.save()
            print(f"Created customer: {user.email}")
        customers.append(user)

    # Create Projects
    project_names = ["Website Redesign", "Mobile App v2", "Internal Audit", "Cloud Migration", "Q1 Hiring"]
    projects = []
    for pname in project_names:
        proj, created = Project.objects.get_or_create(
            name=pname,
            organization=org,
            defaults={
                "key": pname.split()[0].upper()[:3],
                "description": f"Project for {pname}"
            }
        )
        if created:
            print(f"Created project: {pname}")
        projects.append(proj)

    # Create Tickets
    priorities = ['low', 'medium', 'high', 'critical']
    statuses = ['open', 'in_progress', 'waiting', 'resolved', 'closed']
    
    # Existing users to assign/report
    all_assignables = managers + agents
    
    print("Creating tickets...")
    for i in range(1, 21):
        customer = random.choice(customers)
        project = random.choice(projects)
        priority = random.choice(priorities)
        status = random.choice(statuses)
        
        assignee = None
        if status != 'open':
            assignee = random.choice(all_assignables)

        ticket = Ticket.objects.create(
            ticket_id = Ticket.generate_ticket_id(project.key, project.id),
            subject=f"Issue {i}: {random.choice(['Login failed', 'Page crash', 'Feature request', 'Bug report', 'Access denied'])} in {project.name}",
            description=f"Detailed description for issue {i}. This needs attention.",
            priority=priority,
            status=status,
            sender_email=customer.email,
            sender_name=customer.full_name,
            assigned_to=assignee,
            organization=org,
            project=project,
            created_at=timezone.now() - timedelta(days=random.randint(0, 30))
        )
        
        # Add a comment
        if random.choice([True, False]):
            Comment.objects.create(
                ticket=ticket,
                user=assignee if assignee else customer,
                comment="Looking into this now.",
                created_at=timezone.now(),
                is_internal=False
            )

    print("Data population complete!")

if __name__ == "__main__":
    create_dummy_data()
