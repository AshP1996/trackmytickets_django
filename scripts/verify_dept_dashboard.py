import os
import sys
import django
from django.conf import settings

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from apps.accounts.views import DepartmentHeadStatsView, DepartmentHeadTicketsView, DepartmentHeadEmployeesView
from apps.accounts.models import User, Organization, Department
from apps.tickets.models import Ticket, Project

def verify_dept_dashboard():
    print("Verifying Department Head Dashboard APIs...")
    
    # 1. Setup Data
    org_name = 'Test Org'
    subdomain = 'testverify'
    try:
        org = Organization.objects.get(subdomain=subdomain)
    except Organization.DoesNotExist:
        org = Organization.objects.create(name=org_name, subdomain=subdomain, email='test@example.com', plan='pro', is_active=True)
        
    # Department
    try:
        dept = Department.objects.get(name='IT Support', organization=org)
    except Department.DoesNotExist:
        dept = Department.objects.create(name='IT Support', organization=org)
        
    # Dept Head User
    email = 'head@testverify.com'
    try:
        user = User.objects.get(email=email)
        user.department = dept.name # Use string name
        user.save()
    except User.DoesNotExist:
        user = User.objects.create(email=email, full_name='Head User', organization=org, role='head', department=dept.name, is_active=True)
        user.set_password('password')
        user.save()
        
    # Employee User
    emp_email = 'emp@testverify.com'
    try:
        emp = User.objects.get(email=emp_email)
        emp.department = dept.name
        emp.save()
    except User.DoesNotExist:
        emp = User.objects.create(email=emp_email, full_name='Employee User', organization=org, role='agent', department=dept.name, is_active=True)
        emp.save()

    # Ticket
    if Ticket.objects.filter(organization=org, department=dept).count() == 0:
         project, _ = Project.objects.get_or_create(name='Test Proj', key='TP', organization=org)
         Ticket.objects.create(ticket_id='TP-1', project=project, organization=org, subject='Dept Ticket', status='open', priority='medium', department=dept)
         Ticket.objects.create(ticket_id='TP-2', project=project, organization=org, subject='Assigned Ticket', status='in_progress', priority='high', department=dept, assigned_to=emp)

    factory = APIRequestFactory()
    
    # 2. Test Stats
    print("\n--- Testing Stats ---")
    req = factory.get(f'/api/{subdomain}/auth/department-head/stats/')
    req.organization = org
    force_authenticate(req, user=user)
    view = DepartmentHeadStatsView.as_view()
    resp = view(req, company_name=subdomain)
    if resp.status_code == 200:
        print("✓ Stats OK:", resp.data.keys())
    else:
        print("✗ Stats Failed:", resp.status_code, resp.data)

    # 3. Test Tickets
    print("\n--- Testing Tickets ---")
    req = factory.get(f'/api/{subdomain}/auth/department-head/tickets/')
    req.organization = org
    force_authenticate(req, user=user)
    view = DepartmentHeadTicketsView.as_view()
    resp = view(req, company_name=subdomain)
    if resp.status_code == 200:
        print("✓ Tickets OK:", len(resp.data['tickets']), "tickets found")
    else:
        print("✗ Tickets Failed:", resp.status_code, resp.data)

    # 4. Test Employees
    print("\n--- Testing Employees ---")
    req = factory.get(f'/api/{subdomain}/auth/department-head/employees/')
    req.organization = org
    force_authenticate(req, user=user)
    view = DepartmentHeadEmployeesView.as_view()
    resp = view(req, company_name=subdomain)
    if resp.status_code == 200:
        print("✓ Employees OK:", len(resp.data), "employees found")
    else:
        print("✗ Employees Failed:", resp.status_code, resp.data)

if __name__ == '__main__':
    verify_dept_dashboard()
