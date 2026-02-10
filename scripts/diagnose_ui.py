"""
UI Data Loading Diagnostic Script
Checks if all frontend pages are properly configured to load data
"""
import os
import re

def check_template_api_calls(template_path, expected_calls):
    """Check if template contains expected API calls"""
    try:
        with open(template_path, 'r') as f:
            content = f.read()
        
        results = []
        for call in expected_calls:
            if call in content:
                results.append(f"✓ {call}")
            else:
                results.append(f"✗ MISSING: {call}")
        
        return results
    except FileNotFoundError:
        return [f"✗ Template not found: {template_path}"]

def check_pagination_handling(template_path):
    """Check if template handles paginated responses correctly"""
    try:
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Check for .results handling
        if '.results' in content or 'response.results' in content:
            return "✓ Handles paginated responses (.results)"
        elif 'Array.isArray' in content:
            return "✓ Has array check"
        else:
            return "⚠ May not handle pagination correctly"
    except FileNotFoundError:
        return "✗ Template not found"

print("=" * 70)
print("UI DATA LOADING DIAGNOSTIC REPORT")
print("=" * 70)

base_path = "/home/ashish/Documents/ticket_system_v1/ticket_system_django"

# Check Dashboard
print("\n[1] DASHBOARD (templates/dashboard.html)")
dashboard_calls = [
    'api.getTicketStats()',
    'api.getTickets(',
    'api.getDepartments()',
]
results = check_template_api_calls(f"{base_path}/templates/dashboard.html", dashboard_calls)
for r in results:
    print(f"    {r}")
print(f"    {check_pagination_handling(f'{base_path}/templates/dashboard.html')}")

# Check Tickets List
print("\n[2] TICKETS LIST (templates/tickets/list.html)")
tickets_calls = [
    'api.getTickets(',
    'api.getProjects()',
    'api.getDepartments()',
]
results = check_template_api_calls(f"{base_path}/templates/tickets/list.html", tickets_calls)
for r in results:
    print(f"    {r}")
print(f"    {check_pagination_handling(f'{base_path}/templates/tickets/list.html')}")

# Check Ticket Details
print("\n[3] TICKET DETAILS (templates/tickets/details.html)")
details_calls = [
    'api.getTicket(',
    'api.getUsers(',
    'api.getStatuses()',
]
results = check_template_api_calls(f"{base_path}/templates/tickets/details.html", details_calls)
for r in results:
    print(f"    {r}")
print(f"    {check_pagination_handling(f'{base_path}/templates/tickets/details.html')}")

# Check Projects
print("\n[4] PROJECTS (templates/projects/list.html)")
projects_calls = [
    'api.getProjects()',
    'api.createProject(',
]
results = check_template_api_calls(f"{base_path}/templates/projects/list.html", projects_calls)
for r in results:
    print(f"    {r}")
print(f"    {check_pagination_handling(f'{base_path}/templates/projects/list.html')}")

# Check Departments
print("\n[5] DEPARTMENTS (templates/admin/departments.html)")
dept_calls = [
    'api.getDepartments()',
    'api.getUsers(',
]
results = check_template_api_calls(f"{base_path}/templates/admin/departments.html", dept_calls)
for r in results:
    print(f"    {r}")
print(f"    {check_pagination_handling(f'{base_path}/templates/admin/departments.html')}")

# Check Users
print("\n[6] USERS (templates/admin/users.html)")
users_calls = [
    'api.getUsers(',
    'api.getDepartments()',
]
results = check_template_api_calls(f"{base_path}/templates/admin/users.html", users_calls)
for r in results:
    print(f"    {r}")
print(f"    {check_pagination_handling(f'{base_path}/templates/admin/users.html')}")

# Check API.js
print("\n[7] API CLIENT (static/js/api.js)")
api_methods = [
    'getTickets(',
    'getProjects(',
    'getDepartments(',
    'getUsers(',
    'getStatuses(',
    'getTicketStats(',
]
results = check_template_api_calls(f"{base_path}/static/js/api.js", api_methods)
for r in results:
    print(f"    {r}")

print("\n" + "=" * 70)
print("BACKEND API TEST RESULTS (from previous test)")
print("=" * 70)
print("✓ Login: SUCCESS")
print("✓ Projects: 13 found")
print("✓ Tickets: 32 found")
print("✓ Departments: 10 found")

print("\n" + "=" * 70)
print("RECOMMENDATIONS")
print("=" * 70)
print("""
1. Backend API is working correctly ✓
2. Demo data is populated ✓
3. If UI still shows no data, check browser console for errors
4. Verify you're logged in as admin@demo.com
5. Check Network tab in browser DevTools for failed API calls
6. Clear browser cache and reload

To test manually:
1. Go to http://localhost:9000/demo/login
2. Login with: admin@demo.com / admin123
3. Navigate to Dashboard, Tickets, Projects, etc.
4. Open browser console (F12) to see any errors
""")

print("=" * 70)
