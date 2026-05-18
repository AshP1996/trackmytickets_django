#!/usr/bin/env python3
"""
Setup comprehensive test organizations with full data
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod_override')
os.environ.setdefault('SECRET_KEY', 'EAl1GuKGVqU4WALJrd8tqcROFPBARgPlQwEs6Xe16lBeBtRoysZ0HeAYhyKy3zEOYl0')
os.environ.setdefault('DB_PASSWORD', 'TrackMyTickets2026!')
os.environ.setdefault('DB_PORT', '5433')

django.setup()

from apps.accounts.models import Organization, User, Department, PlatformAdmin
from apps.tickets.models import Ticket, Project
from django.utils import timezone

def create_platform_admin():
    """Create platform admin"""
    print("\n=== Creating Platform Admin ===")
    
    admin, created = PlatformAdmin.objects.get_or_create(
        email='admin@luminoai.online'
    )
    if created or not admin.check_password('Admin@2026'):
        admin.set_password('Admin@2026')
        admin.save()
        print(f"✓ Platform Admin: admin@luminoai.online / Admin@2026")
    else:
        print(f"✓ Platform Admin exists: admin@luminoai.online")
    
    return admin

def create_acme_corp():
    """Create ACME Corp organization with full data"""
    print("\n=== Creating ACME Corp ===")
    
    # Create organization
    org, created = Organization.objects.get_or_create(
        subdomain='acme',
        defaults={
            'name': 'ACME Corporation',
            'email': 'contact@acme.com',
            'is_active': True
        }
    )
    print(f"{'✓ Created' if created else '✓ Exists'}: {org.name}")
    
    # Create departments
    departments = {
        'IT': Department.objects.get_or_create(organization=org, name='IT Support')[0],
        'HR': Department.objects.get_or_create(organization=org, name='Human Resources')[0],
        'Sales': Department.objects.get_or_create(organization=org, name='Sales')[0],
        'Support': Department.objects.get_or_create(organization=org, name='Customer Support')[0],
    }
    print(f"✓ Created {len(departments)} departments")
    
    # Create project
    project, _ = Project.objects.get_or_create(
        organization=org,
        key='SUP',
        defaults={
            'name': 'Support Tickets',
            'description': 'General support tickets',
            'is_active': True
        }
    )
    print(f"✓ Created project: {project.name}")
    
    # Create users
    users = []
    
    # Admin
    admin = create_user(org, 'admin@acme.com', 'ACME Admin', 'admin', None, 'Admin@123')
    users.append(admin)
    
    # Department Heads
    it_head = create_user(org, 'head.it@acme.com', 'John Smith', 'department_head', 'IT Support', 'Head@123')
    hr_head = create_user(org, 'head.hr@acme.com', 'Sarah Johnson', 'department_head', 'Human Resources', 'Head@123')
    sales_head = create_user(org, 'head.sales@acme.com', 'Mike Wilson', 'department_head', 'Sales', 'Head@123')
    support_head = create_user(org, 'head.support@acme.com', 'Emily Davis', 'department_head', 'Customer Support', 'Head@123')
    users.extend([it_head, hr_head, sales_head, support_head])
    
    # Agents
    it_agent1 = create_user(org, 'agent.it1@acme.com', 'Tom Anderson', 'agent', 'IT Support', 'Agent@123')
    it_agent2 = create_user(org, 'agent.it2@acme.com', 'Lisa Brown', 'agent', 'IT Support', 'Agent@123')
    support_agent1 = create_user(org, 'agent.support1@acme.com', 'David Lee', 'agent', 'Customer Support', 'Agent@123')
    support_agent2 = create_user(org, 'agent.support2@acme.com', 'Anna Martinez', 'agent', 'Customer Support', 'Agent@123')
    users.extend([it_agent1, it_agent2, support_agent1, support_agent2])
    
    # Customers
    customer1 = create_user(org, 'customer1@client.com', 'Robert Taylor', 'customer', None, 'Customer@123')
    customer2 = create_user(org, 'customer2@client.com', 'Jennifer White', 'customer', None, 'Customer@123')
    customer3 = create_user(org, 'customer3@client.com', 'Michael Harris', 'customer', None, 'Customer@123')
    users.extend([customer1, customer2, customer3])
    
    print(f"✓ Created {len(users)} users")
    
    # Create sample tickets
    create_sample_tickets(org, project, customer1, customer2, it_agent1, support_agent1, departments['IT'])
    
    return org

def create_globex_inc():
    """Create Globex Inc organization"""
    print("\n=== Creating Globex Inc ===")
    
    org, created = Organization.objects.get_or_create(
        subdomain='globex',
        defaults={
            'name': 'Globex Inc',
            'email': 'info@globex.com',
            'is_active': True
        }
    )
    print(f"{'✓ Created' if created else '✓ Exists'}: {org.name}")
    
    # Create departments
    departments = {
        'Engineering': Department.objects.get_or_create(organization=org, name='Engineering')[0],
        'Marketing': Department.objects.get_or_create(organization=org, name='Marketing')[0],
        'Operations': Department.objects.get_or_create(organization=org, name='Operations')[0],
    }
    print(f"✓ Created {len(departments)} departments")
    
    # Create project
    project, _ = Project.objects.get_or_create(
        organization=org,
        key='ENG',
        defaults={
            'name': 'Engineering Support',
            'description': 'Engineering support tickets',
            'is_active': True
        }
    )
    
    # Create users
    users = []
    
    admin = create_user(org, 'admin@globex.com', 'Globex Admin', 'admin', None, 'Admin@123')
    users.append(admin)
    
    eng_head = create_user(org, 'head.eng@globex.com', 'Alex Chen', 'department_head', 'Engineering', 'Head@123')
    mkt_head = create_user(org, 'head.marketing@globex.com', 'Maria Garcia', 'department_head', 'Marketing', 'Head@123')
    users.extend([eng_head, mkt_head])
    
    eng_agent = create_user(org, 'agent.eng1@globex.com', 'Chris Wong', 'agent', 'Engineering', 'Agent@123')
    users.append(eng_agent)
    
    customer = create_user(org, 'customer1@partner.com', 'Patricia Moore', 'customer', None, 'Customer@123')
    users.append(customer)
    
    print(f"✓ Created {len(users)} users")
    
    return org

def create_user(org, email, full_name, role, department, password):
    """Helper to create a user"""
    user, created = User.objects.get_or_create(
        email=email,
        organization=org,
        defaults={
            'full_name': full_name,
            'role': role,
            'department': department,
            'is_active': True
        }
    )
    if created or not user.check_password(password):
        user.set_password(password)
        user.save()
    return user

def create_sample_tickets(org, project, customer1, customer2, it_agent, support_agent, it_dept):
    """Create sample tickets"""
    print("✓ Creating sample tickets...")
    
    tickets_data = [
        {
            'subject': 'Cannot access email account',
            'description': 'I am unable to login to my email account. Getting authentication error.',
            'sender_email': customer1.email,
            'sender_name': customer1.full_name,
            'assigned_to': it_agent,
            'status': 'in_progress',
            'priority': 'high',
            'department': it_dept
        },
        {
            'subject': 'Printer not working',
            'description': 'Office printer on 3rd floor is not responding.',
            'sender_email': customer2.email,
            'sender_name': customer2.full_name,
            'assigned_to': it_agent,
            'status': 'open',
            'priority': 'medium',
            'department': it_dept
        },
        {
            'subject': 'Need help with software installation',
            'description': 'Need assistance installing the new CRM software.',
            'sender_email': customer1.email,
            'sender_name': customer1.full_name,
            'assigned_to': support_agent,
            'status': 'open',
            'priority': 'low',
            'department': it_dept
        },
        {
            'subject': 'VPN connection issues',
            'description': 'Cannot connect to company VPN from home.',
            'sender_email': customer2.email,
            'sender_name': customer2.full_name,
            'assigned_to': None,
            'status': 'open',
            'priority': 'high',
            'department': it_dept
        },
    ]
    
    for i, ticket_data in enumerate(tickets_data, 1):
        ticket_id = f"{project.key}-{i}"
        Ticket.objects.get_or_create(
            organization=org,
            ticket_id=ticket_id,
            defaults={
                'project': project,
                'subject': ticket_data['subject'],
                'description': ticket_data['description'],
                'sender_email': ticket_data['sender_email'],
                'sender_name': ticket_data['sender_name'],
                'assigned_to': ticket_data['assigned_to'],
                'status': ticket_data['status'],
                'priority': ticket_data['priority'],
                'department': ticket_data['department'],
                'created_at': timezone.now()
            }
        )
    
    print(f"✓ Created {len(tickets_data)} sample tickets")

def main():
    print("="*60)
    print("Setting Up Production Test Data")
    print("="*60)
    
    # Create platform admin
    create_platform_admin()
    
    # Create organizations
    acme = create_acme_corp()
    globex = create_globex_inc()
    
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    
    # Print summary
    print("\n📊 Summary:")
    print(f"  Organizations: {Organization.objects.count()}")
    print(f"  Total Users: {User.objects.count()}")
    print(f"  Total Departments: {Department.objects.count()}")
    print(f"  Total Tickets: {Ticket.objects.count()}")
    
    print("\n✅ All test data created successfully!")

if __name__ == '__main__':
    main()
