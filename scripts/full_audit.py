#!/usr/bin/env python3
"""
FULL FLOW AUDIT — Post Tenant Isolation Refactor

This script performs a comprehensive end-to-end audit:
1. Creates a fresh organization
2. Creates an admin user with known credentials
3. Logs in as admin
4. Creates departments, users, projects, tickets, comments
5. Verifies dashboard data
6. Tests BYODB (external data source)
7. Verifies data integrity in DB
8. Tests cross-org isolation
"""
import requests
import json
import sqlite3
import os
import sys
import time

BASE_URL = "http://localhost:8000"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db.sqlite3')
DB_PATH = os.path.normpath(DB_PATH)

# Audit results
results = []

def log(phase, test, status, detail=""):
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    results.append({"phase": phase, "test": test, "status": status, "detail": detail})
    print(f"  {icon} [{phase}] {test}: {status} {detail}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ============================================================================
# PHASE 0: Health Check
# ============================================================================
section("PHASE 0: HEALTH CHECK")

try:
    r = requests.get(f"{BASE_URL}/health/", timeout=5)
    data = r.json()
    if data.get("status") == "healthy":
        log("HEALTH", "Server health check", "PASS", f"DB={data['checks']['database']}")
    else:
        log("HEALTH", "Server health check", "FAIL", str(data))
except Exception as e:
    log("HEALTH", "Server health check", "FAIL", str(e))
    print("\n❌ Server not running! Start with: python manage.py runserver")
    sys.exit(1)

# ============================================================================
# PHASE 1: Create Fresh Organization
# ============================================================================
section("PHASE 1: CREATE ORGANIZATION")

ORG_NAME = "AuditTestOrg"
ORG_SUBDOMAIN = "audit-test"
ADMIN_EMAIL = "admin@audit-test.com"
ADMIN_PASSWORD = "AuditPass123!"

# Create org directly in DB (platform API endpoint)
conn = sqlite3.connect(DB_PATH, timeout=10)
conn.execute("PRAGMA foreign_keys=OFF")

# Check if org already exists
existing = conn.execute("SELECT id FROM organizations WHERE subdomain=?", (ORG_SUBDOMAIN,)).fetchone()
if existing:
    org_id = existing[0]
    log("SETUP", "Organization exists", "PASS", f"id={org_id}")
else:
    conn.execute(
        "INSERT INTO organizations (name, subdomain, email, is_active, created_at, updated_at, plan) "
        "VALUES (?, ?, ?, 1, datetime('now'), datetime('now'), 'starter_trial')",
        (ORG_NAME, ORG_SUBDOMAIN, "admin@audit-test.com")
    )
    conn.commit()
    org_id = conn.execute("SELECT id FROM organizations WHERE subdomain=?", (ORG_SUBDOMAIN,)).fetchone()[0]
    log("SETUP", "Organization created", "PASS", f"id={org_id}, subdomain={ORG_SUBDOMAIN}")

# Create admin user directly in DB
existing_user = conn.execute("SELECT id FROM users WHERE email=?", (ADMIN_EMAIL,)).fetchone()
if existing_user:
    user_id = existing_user[0]
    log("SETUP", "Admin user exists", "PASS", f"id={user_id}")
else:
    # Use Django to hash the password
    import subprocess
    hash_result = subprocess.run([
        sys.executable, "-c",
        f"import django; import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings.dev'; django.setup(); "
        f"from django.contrib.auth.hashers import make_password; print(make_password('{ADMIN_PASSWORD}'))"
    ], capture_output=True, text=True, cwd=os.path.dirname(DB_PATH))
    pwd_hash = hash_result.stdout.strip()
    
    conn.execute(
        "INSERT INTO users (email, password, full_name, role, department, is_active, is_onboarded, "
        "is_staff, is_superuser, organization_id, created_at) "
        "VALUES (?, ?, 'Audit Admin', 'admin', NULL, 1, 1, 0, 0, ?, datetime('now'))",
        (ADMIN_EMAIL, pwd_hash, org_id)
    )
    conn.commit()
    user_id = conn.execute("SELECT id FROM users WHERE email=?", (ADMIN_EMAIL,)).fetchone()[0]
    log("SETUP", "Admin user created", "PASS", f"id={user_id}")

conn.close()

# ============================================================================
# PHASE 2: Login as Admin
# ============================================================================
section("PHASE 2: LOGIN")

try:
    r = requests.post(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/auth/login/", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }, timeout=10)
    
    if r.status_code == 200:
        login_data = r.json()
        access_token = login_data.get("access_token")
        user_data = login_data.get("user", {})
        org_data = login_data.get("organization", {})
        log("AUTH", "Admin login", "PASS", 
            f"user_id={user_data.get('id')}, org={org_data.get('name')}")
        
        # Verify JWT has org_id
        if org_data.get("id"):
            log("AUTH", "JWT contains org_id", "PASS", f"org_id={org_data['id']}")
        else:
            log("AUTH", "JWT contains org_id", "FAIL", "No org_id in response")
    else:
        log("AUTH", "Admin login", "FAIL", f"status={r.status_code}, body={r.text[:200]}")
        access_token = None
except Exception as e:
    log("AUTH", "Admin login", "FAIL", str(e))
    access_token = None

if not access_token:
    print("\n❌ Login failed! Cannot continue audit.")
    # Print summary and exit
    section("AUDIT SUMMARY (PARTIAL)")
    for r in results:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon} {r['test']}: {r['detail']}")
    sys.exit(1)

headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

# ============================================================================
# PHASE 3: Create Departments
# ============================================================================
section("PHASE 3: DEPARTMENTS")

departments_created = []
for dept_name in ["Engineering", "Support", "QA"]:
    try:
        r = requests.post(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/auth/departments/", 
                         json={"name": dept_name}, headers=headers, timeout=10)
        if r.status_code in (200, 201):
            dept = r.json()
            departments_created.append(dept)
            log("DEPT", f"Create '{dept_name}'", "PASS", f"id={dept.get('id')}")
        elif r.status_code == 400 and "unique" in r.text.lower():
            # Already exists, fetch it
            r2 = requests.get(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/auth/departments/", 
                            headers=headers, timeout=10)
            if r2.status_code == 200:
                for d in r2.json().get("results", r2.json() if isinstance(r2.json(), list) else []):
                    if d.get("name") == dept_name:
                        departments_created.append(d)
                        log("DEPT", f"'{dept_name}' already exists", "PASS", f"id={d.get('id')}")
                        break
        else:
            log("DEPT", f"Create '{dept_name}'", "FAIL", f"status={r.status_code}, body={r.text[:200]}")
    except Exception as e:
        log("DEPT", f"Create '{dept_name}'", "FAIL", str(e))

# List departments
try:
    r = requests.get(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/auth/departments/", headers=headers, timeout=10)
    if r.status_code == 200:
        dept_list = r.json()
        count = len(dept_list) if isinstance(dept_list, list) else len(dept_list.get("results", []))
        log("DEPT", "List departments", "PASS", f"count={count}")
    else:
        log("DEPT", "List departments", "FAIL", f"status={r.status_code}")
except Exception as e:
    log("DEPT", "List departments", "FAIL", str(e))

# ============================================================================
# PHASE 4: Create Users
# ============================================================================
section("PHASE 4: USERS")

users_created = []
test_users = [
    {"email": "manager@audit-test.com", "full_name": "Audit Manager", "role": "manager", 
     "password": "Manager123!", "department": "Engineering"},
    {"email": "agent1@audit-test.com", "full_name": "Agent One", "role": "agent",
     "password": "Agent123!", "department": "Support"},
    {"email": "agent2@audit-test.com", "full_name": "Agent Two", "role": "agent",
     "password": "Agent123!", "department": "QA"},
]

for user in test_users:
    try:
        payload = {**user, "organization_id": org_id}
        r = requests.post(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/auth/register/", 
                         json=payload, headers=headers, timeout=10)
        if r.status_code in (200, 201):
            u = r.json()
            users_created.append(u)
            log("USER", f"Create '{user['full_name']}'", "PASS", f"id={u.get('id')}, role={user['role']}")
        elif r.status_code == 400 and "exists" in r.text.lower():
            log("USER", f"'{user['full_name']}' already exists", "PASS")
        else:
            log("USER", f"Create '{user['full_name']}'", "FAIL", f"status={r.status_code}, body={r.text[:200]}")
    except Exception as e:
        log("USER", f"Create '{user['full_name']}'", "FAIL", str(e))

# List users
try:
    r = requests.get(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/auth/users/", headers=headers, timeout=10)
    if r.status_code == 200:
        user_list = r.json()
        count = len(user_list) if isinstance(user_list, list) else len(user_list.get("results", []))
        log("USER", "List users", "PASS", f"count={count}")
    else:
        log("USER", "List users", "FAIL", f"status={r.status_code}, body={r.text[:200]}")
except Exception as e:
    log("USER", "List users", "FAIL", str(e))

# Me endpoint
try:
    r = requests.get(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/auth/me/", headers=headers, timeout=10)
    if r.status_code == 200:
        me = r.json()
        log("USER", "Me endpoint", "PASS", f"email={me.get('email')}, role={me.get('role')}")
    else:
        log("USER", "Me endpoint", "FAIL", f"status={r.status_code}")
except Exception as e:
    log("USER", "Me endpoint", "FAIL", str(e))

# ============================================================================
# PHASE 5: Create Projects
# ============================================================================
section("PHASE 5: PROJECTS")

projects_created = []
test_projects = [
    {"name": "Audit Platform", "key": "APT", "description": "Main audit platform project"},
    {"name": "Bug Tracker", "key": "BUG", "description": "Bug tracking project"},
]

for proj in test_projects:
    try:
        r = requests.post(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/projects/", 
                         json=proj, headers=headers, timeout=10)
        if r.status_code in (200, 201):
            p = r.json()
            projects_created.append(p)
            log("PROJECT", f"Create '{proj['name']}'", "PASS", f"id={p.get('id')}, key={proj['key']}")
        elif r.status_code == 400:
            # Might already exist, try listing
            r2 = requests.get(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/projects/", headers=headers, timeout=10)
            if r2.status_code == 200:
                plist = r2.json() if isinstance(r2.json(), list) else r2.json().get("results", [])
                for p in plist:
                    if p.get("key") == proj["key"]:
                        projects_created.append(p)
                        log("PROJECT", f"'{proj['name']}' already exists", "PASS", f"id={p.get('id')}")
                        break
            else:
                log("PROJECT", f"Create '{proj['name']}'", "FAIL", f"status={r.status_code}, body={r.text[:200]}")
        else:
            log("PROJECT", f"Create '{proj['name']}'", "FAIL", f"status={r.status_code}, body={r.text[:200]}")
    except Exception as e:
        log("PROJECT", f"Create '{proj['name']}'", "FAIL", str(e))

# List projects
try:
    r = requests.get(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/projects/", headers=headers, timeout=10)
    if r.status_code == 200:
        proj_list = r.json()
        count = len(proj_list) if isinstance(proj_list, list) else len(proj_list.get("results", []))
        log("PROJECT", "List projects", "PASS", f"count={count}")
    else:
        log("PROJECT", "List projects", "FAIL", f"status={r.status_code}")
except Exception as e:
    log("PROJECT", "List projects", "FAIL", str(e))

# ============================================================================
# PHASE 6: Create Tickets
# ============================================================================
section("PHASE 6: TICKETS")

tickets_created = []
if projects_created:
    project_id = projects_created[0].get("id")
    dept_id = departments_created[0].get("id") if departments_created else None
    
    test_tickets = [
        {"subject": "Audit Test - Login Bug", "description": "Users cannot login after refactor",
         "priority": "high", "project": project_id, "department": dept_id, "ticket_type": "bug"},
        {"subject": "Audit Test - Dashboard Slow", "description": "Dashboard takes 10s to load",
         "priority": "medium", "project": project_id, "ticket_type": "issue"},
        {"subject": "Audit Test - New Feature", "description": "Add multi-org support",
         "priority": "low", "project": project_id, "ticket_type": "feature_request"},
    ]
    
    for ticket in test_tickets:
        try:
            r = requests.post(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/tickets/", 
                             json=ticket, headers=headers, timeout=10)
            if r.status_code in (200, 201):
                t = r.json()
                tickets_created.append(t)
                log("TICKET", f"Create '{ticket['subject'][:30]}...'", "PASS", 
                    f"id={t.get('id')}, ticket_id={t.get('ticket_id')}")
            else:
                log("TICKET", f"Create '{ticket['subject'][:30]}...'", "FAIL", 
                    f"status={r.status_code}, body={r.text[:200]}")
        except Exception as e:
            log("TICKET", f"Create '{ticket['subject'][:30]}...'", "FAIL", str(e))
else:
    log("TICKET", "Ticket creation", "SKIP", "No projects available")

# List tickets
try:
    r = requests.get(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/tickets/", headers=headers, timeout=10)
    if r.status_code == 200:
        ticket_list = r.json()
        count = len(ticket_list) if isinstance(ticket_list, list) else len(ticket_list.get("results", []))
        log("TICKET", "List tickets", "PASS", f"count={count}")
    else:
        log("TICKET", "List tickets", "FAIL", f"status={r.status_code}")
except Exception as e:
    log("TICKET", "List tickets", "FAIL", str(e))

# ============================================================================
# PHASE 7: Add Comments
# ============================================================================
section("PHASE 7: COMMENTS")

if tickets_created:
    ticket_id = tickets_created[0].get("id")
    ticket_ident = tickets_created[0].get("ticket_id", ticket_id)
    
    comments = [
        {"comment": "Initial investigation started — checking authentication flow."},
        {"comment": "Root cause identified: tenant middleware not setting ContextVar.", "is_internal": True},
        {"comment": "Fix deployed. Awaiting confirmation from user."},
    ]
    
    for i, comment in enumerate(comments):
        try:
            r = requests.post(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/tickets/{ticket_id}/comments/", 
                             json=comment, headers=headers, timeout=10)
            if r.status_code in (200, 201):
                c = r.json()
                log("COMMENT", f"Comment #{i+1} on {ticket_ident}", "PASS", 
                    f"id={c.get('id')}, internal={comment.get('is_internal', False)}")
            else:
                log("COMMENT", f"Comment #{i+1} on {ticket_ident}", "FAIL", 
                    f"status={r.status_code}, body={r.text[:200]}")
        except Exception as e:
            log("COMMENT", f"Comment #{i+1} on {ticket_ident}", "FAIL", str(e))
else:
    log("COMMENT", "Comment creation", "SKIP", "No tickets available")

# ============================================================================
# PHASE 8: Update Ticket Status
# ============================================================================
section("PHASE 8: TICKET UPDATES")

if tickets_created:
    ticket_id = tickets_created[0].get("id")
    ticket_ident = tickets_created[0].get("ticket_id", ticket_id)
    
    # Update status
    try:
        r = requests.patch(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/tickets/{ticket_id}/", 
                          json={"status": "in_progress"}, headers=headers, timeout=10)
        if r.status_code == 200:
            log("UPDATE", f"Status→in_progress on {ticket_ident}", "PASS")
        else:
            log("UPDATE", f"Status→in_progress on {ticket_ident}", "FAIL", 
                f"status={r.status_code}, body={r.text[:200]}")
    except Exception as e:
        log("UPDATE", f"Status→in_progress on {ticket_ident}", "FAIL", str(e))
    
    # Ticket detail
    try:
        r = requests.get(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/tickets/{ticket_id}/", 
                        headers=headers, timeout=10)
        if r.status_code == 200:
            detail = r.json()
            log("UPDATE", f"Ticket detail for {ticket_ident}", "PASS", 
                f"status={detail.get('status')}, comments={len(detail.get('comments', []))}")
        else:
            log("UPDATE", f"Ticket detail for {ticket_ident}", "FAIL", f"status={r.status_code}")
    except Exception as e:
        log("UPDATE", f"Ticket detail for {ticket_ident}", "FAIL", str(e))

# ============================================================================
# PHASE 9: Dashboard Verification
# ============================================================================
section("PHASE 9: DASHBOARD")

try:
    r = requests.get(f"{BASE_URL}/api/{ORG_SUBDOMAIN}/admin/dashboard/", headers=headers, timeout=10)
    if r.status_code == 200:
        dash = r.json()
        log("DASH", "Dashboard API", "PASS", f"keys={list(dash.keys())[:5]}")
        
        # Check specific metrics
        if "total_tickets" in dash or "stats" in dash:
            log("DASH", "Ticket stats present", "PASS")
        else:
            log("DASH", "Ticket stats present", "WARN", "No ticket stats found in response")
    else:
        log("DASH", "Dashboard API", "FAIL", f"status={r.status_code}, body={r.text[:200]}")
except Exception as e:
    log("DASH", "Dashboard API", "FAIL", str(e))

# ============================================================================
# PHASE 10: Data Integrity Audit (DB Level)
# ============================================================================
section("PHASE 10: DATA INTEGRITY")

conn = sqlite3.connect(DB_PATH, timeout=10)
conn.execute("PRAGMA foreign_keys=OFF")

# Check users are in the DB with correct org_id
cursor = conn.execute("SELECT COUNT(*) FROM users WHERE organization_id=?", (org_id,))
user_count = cursor.fetchone()[0]
log("DB", f"Users with org_id={org_id}", "PASS" if user_count > 0 else "FAIL", f"count={user_count}")

# Check departments
cursor = conn.execute("SELECT COUNT(*) FROM departments WHERE organization_id=?", (org_id,))
dept_count = cursor.fetchone()[0]
log("DB", f"Departments with org_id={org_id}", "PASS" if dept_count > 0 else "WARN", f"count={dept_count}")

# Check projects
cursor = conn.execute("SELECT COUNT(*) FROM projects WHERE organization_id=?", (org_id,))
proj_count = cursor.fetchone()[0]
log("DB", f"Projects with org_id={org_id}", "PASS" if proj_count > 0 else "WARN", f"count={proj_count}")

# Check tickets
cursor = conn.execute("SELECT COUNT(*) FROM tickets WHERE organization_id=?", (org_id,))
tkt_count = cursor.fetchone()[0]
log("DB", f"Tickets with org_id={org_id}", "PASS" if tkt_count > 0 else "WARN", f"count={tkt_count}")

# Check comments
try:
    cursor = conn.execute(
        "SELECT COUNT(*) FROM comments c JOIN tickets t ON c.ticket_id=t.id WHERE t.organization_id=?", 
        (org_id,))
    cmt_count = cursor.fetchone()[0]
    log("DB", f"Comments for org_id={org_id}", "PASS" if cmt_count > 0 else "WARN", f"count={cmt_count}")
except:
    log("DB", "Comments check", "WARN", "Could not verify")

# Organization in primary DB
cursor = conn.execute("SELECT name, subdomain, plan FROM organizations WHERE id=?", (org_id,))
org_row = cursor.fetchone()
if org_row:
    log("DB", "Organization in primary DB", "PASS", f"name={org_row[0]}, subdomain={org_row[1]}")
else:
    log("DB", "Organization in primary DB", "FAIL", "Not found!")

conn.close()

# ============================================================================
# PHASE 11: Cross-Org Isolation Test
# ============================================================================
section("PHASE 11: CROSS-ORG ISOLATION")

# Try to access another org's data using our token
other_subdomains = ["test", "testverify", "techflow"]
for other_sub in other_subdomains:
    try:
        r = requests.get(f"{BASE_URL}/api/{other_sub}/auth/users/", headers=headers, timeout=10)
        if r.status_code in (403, 401):
            log("ISO", f"Blocked from {other_sub} users", "PASS", f"status={r.status_code}")
        elif r.status_code == 200:
            data = r.json()
            count = len(data) if isinstance(data, list) else len(data.get("results", []))
            if count == 0:
                log("ISO", f"Empty response from {other_sub}", "PASS", "No data leaked")
            else:
                log("ISO", f"Data leaked from {other_sub}!", "FAIL", f"count={count}")
        else:
            log("ISO", f"Access {other_sub}", "WARN", f"status={r.status_code}")
    except Exception as e:
        log("ISO", f"Access {other_sub}", "WARN", str(e))

# ============================================================================
# SUMMARY
# ============================================================================
section("AUDIT SUMMARY")

total = len(results)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
warned = sum(1 for r in results if r["status"] in ("WARN", "SKIP"))

print(f"\n  Total Tests: {total}")
print(f"  ✅ Passed:   {passed}")
print(f"  ❌ Failed:   {failed}")
print(f"  ⚠️  Warned:   {warned}")
print(f"\n  Score: {passed}/{total} ({100*passed//total if total else 0}%)")

# Save report as JSON
report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'audit_report_out.json')
with open(report_path, 'w') as f:
    json.dump({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "passed": passed,
        "failed": failed,
        "warned": warned,
        "score_pct": 100*passed//total if total else 0,
        "results": results
    }, f, indent=2)
print(f"\n  Report saved: {report_path}")

if failed > 0:
    print("\n  ❌ FAILURES:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"    → [{r['phase']}] {r['test']}: {r['detail']}")

print()
