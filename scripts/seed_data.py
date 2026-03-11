
import os
import sys
import django
from django.utils import timezone

sys.path.append('/home/ashish/Documents/ticket_system_v1/ticket_system_django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.accounts.models import Organization, User, PlatformAdmin
from apps.tickets.models import Ticket, Project
# from apps.core.models import TenantAwareModel # Not needed or doesn't exist

def run():
    print("Seeding data...")

    # 1. Platform Admin
    admin_email = "admin@platform.com"
    if not PlatformAdmin.objects.filter(email=admin_email).exists():
        # create_superuser is not implemented for PlatformAdmin according to models.py?
        # Check models.py again. PlatformAdmin inherits AbstractBaseUser and uses BaseUserManager.
        # But BaseUserManager.create_superuser usually expects fields.
        # Let's use objects.create() with set_password for PlatformAdmin if it relies on default manager.
        u = PlatformAdmin(email=admin_email, is_active=True)
        u.set_password("adminpassword")
        u.save()
        print(f"Created Platform Admin: {admin_email}")
    else:
        print(f"Platform Admin {admin_email} exists.")

    # 2. Organization: Acme
    org_name = "Acme Corp"
    subdomain = "acme"
    org, created = Organization.objects.get_or_create(
        subdomain=subdomain,
        defaults={'name': org_name, 'email': 'contact@acme.com', 'plan': 'growth_cluster'}
    )
    if created:
        print(f"Created Org: {org_name}")
    else:
        print(f"Org {org_name} exists.")

    # 3. Users in Acme
    users_data = [
        ("manager@acme.com", "Alice Manager", "manager"),
        ("agent@acme.com", "Bob Agent", "agent"),
        ("customer@acme.com", "Charlie Customer", "customer"),
    ]

    for email, name, role in users_data:
        if not User.objects.filter(email=email).exists():
            User.objects.create_user(
                email=email,
                organization_id=org.id,
                password="password123",
                full_name=name,
                role=role,
                is_active=True
            )
            print(f"Created User: {email} ({role})")
        else:
            print(f"User {email} exists.")

    # 4. Project in Acme
    project, p_created = Project.objects.get_or_create(
        organization=org,
        key="SUP",
        defaults={'name': 'Support', 'description': 'General Support'}
    )
    
    # 5. Tickets
    # 5. Tickets
    current_count = Ticket.objects.filter(organization=org).count()
    if current_count < 30:
        tickets_to_create = 30 - current_count
        print(f"Creating {tickets_to_create} more tickets...")
        agent = User.objects.get(email="agent@acme.com")
        customer = User.objects.get(email="customer@acme.com")
        
        for i in range(current_count, 30):
            t = Ticket.objects.create(
                organization=org,
                project=project,
                subject=f"Test Ticket {i}",
                description="This is a test ticket.",
                priority="medium",
                status="open",
                created_by=customer,
                sender_email=customer.email,
                sender_name=customer.full_name,
                assigned_to=agent
            )
            # Generate ID manually if signals don't (assuming they do, but let's be safe or rely on save)
            # Ticket.generate_ticket_id usually called in view or save method if overridden
            if not t.ticket_id:
                t.ticket_id = f"SUP-{1000+i}"
                t.save()
            print(f"Created Ticket: {t.ticket_id}")

    print("Seeding complete.")

if __name__ == "__main__":
    run()
