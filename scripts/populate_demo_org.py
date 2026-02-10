
import os
import sys
import django
import random
from datetime import timedelta
from django.utils import timezone

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import Organization, User, Department
from apps.tickets.models import Project, Ticket, TicketHistory
from apps.comments.models import Comment

def populate_demo_data():
    print("Populating 'demo' organization with rich data...")

    try:
        org = Organization.objects.get(subdomain='demo')
    except Organization.DoesNotExist:
        print("[ERROR] 'demo' organization does not exist. Run setup_demo_data.py first.")
        return

    # 1. Departments
    departments = {}
    dept_names = ['Support', 'Engineering', 'Sales']
    for name in dept_names:
        dept, created = Department.objects.get_or_create(
            organization=org,
            name=name,
            defaults={'is_active': True}
        )
        departments[name] = dept
        print(f"[{'CREATED' if created else 'EXISTS'}] Department: {name}")

    # 2. Users
    users = {}
    user_data = [
        {'email': 'manager@demo.com', 'name': 'Demo Manager', 'role': 'manager'},
        {'email': 'agent@demo.com', 'name': 'Demo Agent', 'role': 'agent'},
        {'email': 'customer@demo.com', 'name': 'Demo Customer', 'role': 'customer'},
    ]

    for u in user_data:
        user, created = User.objects.get_or_create(
            email=u['email'],
            organization=org,
            defaults={
                'full_name': u['name'],
                'role': u['role'],
                'is_active': True
            }
        )
        if created:
            user.set_password('password123')
            user.save()
            print(f"[CREATED] User: {u['email']} ({u['role']})")
        else:
            print(f"[EXISTS] User: {u['email']}")
        users[u['role']] = user
    
    # Add Admin to users dict
    try:
        users['admin'] = User.objects.get(email='admin@demo.com', organization=org)
    except User.DoesNotExist:
        print("[WARN] Admin user not found, skipping admin assignment")

    # 3. Projects
    projects = {}
    project_data = [
        {'name': 'Customer Support', 'key': 'SUP', 'desc': 'External customer issues'},
        {'name': 'Internal IT', 'key': 'IT', 'desc': 'Internal hardware/software requests'},
        {'name': 'Website Redesign', 'key': 'WEB', 'desc': 'New corporate website project'}
    ]

    for p in project_data:
        proj, created = Project.objects.get_or_create(
            organization=org,
            key=p['key'],
            defaults={
                'name': p['name'],
                'description': p['desc'],
                'lead_user': users.get('manager'),
                'is_active': True
            }
        )
        projects[p['key']] = proj
        print(f"[{'CREATED' if created else 'EXISTS'}] Project: {p['name']} ({p['key']})")

    # 4. Tickets
    ticket_specs = [
        {'subject': 'Unable to login to portal', 'priority': 'high', 'status': 'open', 'proj': 'SUP', 'dept': 'Support'},
        {'subject': 'Feature request: Dark mode', 'priority': 'low', 'status': 'open', 'proj': 'WEB', 'dept': 'Engineering'},
        {'subject': 'Printer on 2nd floor jammed', 'priority': 'medium', 'status': 'in_progress', 'proj': 'IT', 'dept': 'Support'},
        {'subject': 'Q3 Sales Report Discrepancy', 'priority': 'critical', 'status': 'open', 'proj': 'SUP', 'dept': 'Sales'},
        {'subject': 'Update copyright year', 'priority': 'low', 'status': 'closed', 'proj': 'WEB', 'dept': 'Engineering'},
        {'subject': 'VPN connection unstable', 'priority': 'high', 'status': 'resolved', 'proj': 'IT', 'dept': 'Engineering'},
        {'subject': 'New employee onboarding', 'priority': 'medium', 'status': 'open', 'proj': 'IT', 'dept': 'Support'},
        {'subject': 'Fix css bug on landing page', 'priority': 'medium', 'status': 'in_progress', 'proj': 'WEB', 'dept': 'Engineering'},
    ]

    print("Creating/Updating tickets...")
    for spec in ticket_specs:
        project = projects.get(spec['proj'])
        if not project: continue

        # Generate ID directly to match logic if needed, but let view/model handle it usually. 
        # Here we just look for existing subject to avoid dupes or create new.
        
        # We need to simulate ID generation if we want consistency or just let it auto-increment if logic allows
        # But our Model has custom ID logic. Let's use get_or_create with a placeholder and then fix ID if created.
        
        # Checking if ticket exists by subject (simple heuristic)
        existing = Ticket.objects.filter(organization=org, project=project, subject=spec['subject']).first()
        
        if existing:
            ticket = existing
            # print(f"[EXISTS] Ticket: {ticket.ticket_id}")
        else:
            # Generate ID
            ticket_id = Ticket.generate_ticket_id(project.key, project.id)
            
            # Assign random user sometimes
            assignee = users.get('agent') if random.choice([True, False]) else None
            
            ticket = Ticket.objects.create(
                organization=org,
                project=project,
                ticket_id=ticket_id,
                subject=spec['subject'],
                description=f"Detailed description for {spec['subject']}...\n\nLorem ipsum dolor sit amet.",
                priority=spec['priority'],
                status=spec['status'],
                department=departments.get(spec['dept']),
                sender_email=users.get('customer').email if users.get('customer') else 'customer@example.com',
                sender_name=users.get('customer').full_name if users.get('customer') else 'Customer',
                assigned_to=assignee,
                created_at=timezone.now() - timedelta(days=random.randint(0, 30))
            )
            print(f"[CREATED] Ticket: {ticket.ticket_id} - {ticket.subject}")

            # Add History
            TicketHistory.objects.create(
                ticket=ticket,
                user=users.get('admin'),
                action='created',
                new_value='Ticket created'
            )

            # Add Comment
            if random.choice([True, False]):
                Comment.objects.create(
                    ticket=ticket,
                    user=users.get('agent') or users.get('admin'),
                    comment="Looking into this now.",
                    is_internal=False
                )

    print("\n[SUCCESS] Demo data population complete!")

if __name__ == '__main__':
    populate_demo_data()
