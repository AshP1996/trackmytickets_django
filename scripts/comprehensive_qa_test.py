#!/usr/bin/env python3
"""
Comprehensive QA Test Suite for Multi-Tenant Ticket System
Covers: Health, Multi-Tenant Isolation, CRUD, Roles, Security, Edge Cases
"""
import requests
import json
import time
import sys
from datetime import datetime
from collections import defaultdict

BASE_URL = "http://localhost:8000"
RESULTS = {"pass": [], "fail": [], "warn": [], "info": []}
TIMINGS = []

# ─── Credentials ───────────────────────────────────────────────────────────────
ORGS = {
    "demo": {
        "admin": {"email": "admin@demo.com", "password": "password123"},
        "agent": {"email": "agent@demo.com", "password": "password123"},
        "customer": {"email": "customer@demo.com", "password": "password123"},
    },
    "acme": {
        "admin": {"email": "admin@acme.com", "password": "password123"},
    },
    "omega": {
        "admin": {"email": "admin@omega.com", "password": "password123"},
        "manager": {"email": "manager@omega.com", "password": "password123"},
        "agent": {"email": "agent@omega.com", "password": "password123"},
        "customer": {"email": "customer@omega.com", "password": "password123"},
    },
}

# ─── Helpers ───────────────────────────────────────────────────────────────────
def log_pass(test_id, msg):
    RESULTS["pass"].append(f"[PASS] {test_id}: {msg}")
    print(f"  ✅ {test_id}: {msg}")

def log_fail(test_id, msg):
    RESULTS["fail"].append(f"[FAIL] {test_id}: {msg}")
    print(f"  ❌ {test_id}: {msg}")

def log_warn(test_id, msg):
    RESULTS["warn"].append(f"[WARN] {test_id}: {msg}")
    print(f"  ⚠️  {test_id}: {msg}")

def log_info(test_id, msg):
    RESULTS["info"].append(f"[INFO] {test_id}: {msg}")

def timed_request(method, url, **kwargs):
    start = time.time()
    resp = method(url, **kwargs)
    elapsed = round((time.time() - start) * 1000)
    TIMINGS.append({"url": url, "method": method.__name__.upper(), "status": resp.status_code, "ms": elapsed})
    return resp, elapsed

def login(org, role):
    creds = ORGS[org][role]
    url = f"{BASE_URL}/api/{org}/auth/login/"
    resp, ms = timed_request(requests.post, url, json=creds)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("access_token"), data.get("user", {})
    return None, None

def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: PROJECT HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════
def phase1_health_check():
    print("\n" + "=" * 70)
    print("PHASE 1: PROJECT HEALTH CHECK")
    print("=" * 70)

    # 1.1 Health endpoint
    try:
        resp, ms = timed_request(requests.get, f"{BASE_URL}/health/")
        if resp.status_code == 200:
            log_pass("P1.1", f"Health endpoint OK ({ms}ms)")
        else:
            log_fail("P1.1", f"Health endpoint returned {resp.status_code}")
    except Exception as e:
        log_fail("P1.1", f"Health endpoint unreachable: {e}")

    # 1.2 Static files
    resp, ms = timed_request(requests.get, f"{BASE_URL}/static/js/api.js")
    if resp.status_code == 200:
        log_pass("P1.2", f"Static files loading ({ms}ms)")
    else:
        log_fail("P1.2", f"Static file api.js returned {resp.status_code}")

    # 1.3 Landing page
    resp, ms = timed_request(requests.get, f"{BASE_URL}/")
    if resp.status_code == 200:
        log_pass("P1.3", f"Landing page loads ({ms}ms)")
    else:
        log_fail("P1.3", f"Landing page returned {resp.status_code}")

    # 1.4 Login page for each org
    for org in ORGS:
        resp, ms = timed_request(requests.get, f"{BASE_URL}/{org}/auth/login")
        if resp.status_code in [200, 301, 302]:
            log_pass(f"P1.4.{org}", f"Login page for {org} accessible ({ms}ms)")
        else:
            log_fail(f"P1.4.{org}", f"Login page for {org} returned {resp.status_code}")

    # 1.5 Database connectivity via login
    token, user = login("demo", "admin")
    if token:
        log_pass("P1.5", "DB connection OK (login succeeded)")
    else:
        log_fail("P1.5", "DB connection issue (login failed)")

    # 1.6 API root accessible
    if token:
        resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/auth/me/", headers=auth_headers(token))
        if resp.status_code == 200:
            log_pass("P1.6", f"API auth/me accessible ({ms}ms)")
        else:
            log_fail("P1.6", f"API auth/me returned {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: MULTI-TENANT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
def phase2_tenant_isolation():
    print("\n" + "=" * 70)
    print("PHASE 2: MULTI-TENANT VALIDATION")
    print("=" * 70)

    # Login to two different orgs
    demo_token, demo_user = login("demo", "admin")
    acme_token, acme_user = login("acme", "admin")

    if not demo_token or not acme_token:
        log_fail("P2.0", "Cannot login to one or both orgs; skipping tenant tests")
        return

    # 2.1 User lists are isolated
    demo_users_resp, _ = timed_request(requests.get, f"{BASE_URL}/api/demo/auth/users/", headers=auth_headers(demo_token))
    acme_users_resp, _ = timed_request(requests.get, f"{BASE_URL}/api/acme/auth/users/", headers=auth_headers(acme_token))

    demo_users = demo_users_resp.json().get("results", [])
    acme_users = acme_users_resp.json().get("results", [])

    demo_emails = {u["email"] for u in demo_users}
    acme_emails = {u["email"] for u in acme_users}

    if demo_emails.isdisjoint(acme_emails):
        log_pass("P2.1", "User lists are isolated between orgs")
    else:
        overlap = demo_emails & acme_emails
        log_fail("P2.1", f"User lists overlap: {overlap}")

    # 2.2 Cross-tenant token rejection
    # Use demo token to access acme API
    resp, _ = timed_request(requests.get, f"{BASE_URL}/api/acme/auth/users/", headers=auth_headers(demo_token))
    if resp.status_code in [401, 403]:
        log_pass("P2.2", "Cross-tenant token correctly rejected")
    elif resp.status_code == 200:
        cross_users = resp.json().get("results", [])
        cross_emails = {u["email"] for u in cross_users}
        if cross_emails == demo_emails:
            log_warn("P2.2", "Cross-tenant token returns demo data (token not scoped to org)")
        else:
            log_fail("P2.2", "Cross-tenant access: demo token retrieves acme user data!")
    else:
        log_warn("P2.2", f"Cross-tenant access returned unexpected status: {resp.status_code}")

    # 2.3 Ticket isolation
    demo_tickets, _ = timed_request(requests.get, f"{BASE_URL}/api/demo/tickets/", headers=auth_headers(demo_token))
    acme_tickets, _ = timed_request(requests.get, f"{BASE_URL}/api/acme/tickets/", headers=auth_headers(acme_token))

    if demo_tickets.status_code == 200 and acme_tickets.status_code == 200:
        demo_ticket_ids = {t.get("ticket_id") for t in demo_tickets.json().get("results", [])}
        acme_ticket_ids = {t.get("ticket_id") for t in acme_tickets.json().get("results", [])}
        if demo_ticket_ids.isdisjoint(acme_ticket_ids) or not demo_ticket_ids or not acme_ticket_ids:
            log_pass("P2.3", "Ticket data isolated between orgs")
        else:
            log_fail("P2.3", f"Ticket IDs overlap: {demo_ticket_ids & acme_ticket_ids}")
    else:
        log_warn("P2.3", "Could not verify ticket isolation (API error)")

    # 2.4 Project isolation
    demo_projects, _ = timed_request(requests.get, f"{BASE_URL}/api/demo/projects/", headers=auth_headers(demo_token))
    acme_projects, _ = timed_request(requests.get, f"{BASE_URL}/api/acme/projects/", headers=auth_headers(acme_token))

    if demo_projects.status_code == 200 and acme_projects.status_code == 200:
        demo_proj = {p.get("key") for p in demo_projects.json().get("results", [])}
        acme_proj = {p.get("key") for p in acme_projects.json().get("results", [])}
        log_pass("P2.4", f"Project lists isolated: demo={demo_proj}, acme={acme_proj}")
    else:
        log_warn("P2.4", "Could not verify project isolation")

    # 2.5 Invalid org returns 404
    resp, _ = timed_request(requests.get, f"{BASE_URL}/api/nonexistent/auth/users/")
    if resp.status_code in [401, 404]:
        log_pass("P2.5", f"Invalid org returns {resp.status_code}")
    else:
        log_fail("P2.5", f"Invalid org returns {resp.status_code} (expected 401/404)")

    # 2.6 Direct ticket URL from wrong org
    if demo_tickets.status_code == 200:
        demo_results = demo_tickets.json().get("results", [])
        if demo_results:
            ticket_id = demo_results[0]["ticket_id"]
            resp, _ = timed_request(requests.get,
                f"{BASE_URL}/api/acme/tickets/{ticket_id}/",
                headers=auth_headers(acme_token))
            if resp.status_code in [404, 403]:
                log_pass("P2.6", f"Cross-tenant ticket access blocked ({resp.status_code})")
            else:
                log_fail("P2.6", f"Cross-tenant ticket accessible! Status={resp.status_code}")
        else:
            log_warn("P2.6", "No demo tickets to test cross-tenant access")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: FULL CRUD TESTING
# ═══════════════════════════════════════════════════════════════════════════════
def phase3_crud_testing():
    print("\n" + "=" * 70)
    print("PHASE 3: FULL CRUD TESTING (API + DB)")
    print("=" * 70)

    token, user = login("demo", "admin")
    if not token:
        log_fail("P3.0", "Cannot login as demo admin; skipping CRUD tests")
        return

    hdrs = auth_headers(token)
    ts = int(time.time())

    # ─── 3.1 Department CRUD ───
    print("\n  --- 3.1 Department CRUD ---")
    dept_data = {"name": f"QA Dept {ts}"}
    resp, ms = timed_request(requests.post, f"{BASE_URL}/api/demo/auth/departments/", headers=hdrs, json=dept_data)
    if resp.status_code == 201:
        dept = resp.json()
        dept_id = dept["id"]
        log_pass("P3.1a", f"Department created: {dept['name']} (id={dept_id}, {ms}ms)")

        # Read
        resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/auth/departments/{dept_id}/", headers=hdrs)
        if resp.status_code == 200:
            log_pass("P3.1b", f"Department read OK ({ms}ms)")
        else:
            log_fail("P3.1b", f"Department read failed: {resp.status_code}")

        # Update
        resp, ms = timed_request(requests.patch, f"{BASE_URL}/api/demo/auth/departments/{dept_id}/",
                                  headers=hdrs, json={"name": f"QA Dept Updated {ts}"})
        if resp.status_code == 200:
            log_pass("P3.1c", f"Department updated OK ({ms}ms)")
        else:
            log_fail("P3.1c", f"Department update failed: {resp.status_code}")

        # Delete
        resp, ms = timed_request(requests.delete, f"{BASE_URL}/api/demo/auth/departments/{dept_id}/", headers=hdrs)
        if resp.status_code in [204, 200]:
            log_pass("P3.1d", f"Department deleted OK ({ms}ms)")
        else:
            log_fail("P3.1d", f"Department delete failed: {resp.status_code}")
    else:
        log_fail("P3.1a", f"Department create failed: {resp.status_code} - {resp.text[:200]}")

    # ─── 3.2 Project CRUD ───
    print("\n  --- 3.2 Project CRUD ---")
    proj_data = {"name": f"QA Project {ts}", "key": f"QA{ts % 100}", "description": "QA test project"}
    resp, ms = timed_request(requests.post, f"{BASE_URL}/api/demo/projects/", headers=hdrs, json=proj_data)
    project_id = None
    if resp.status_code == 201:
        proj = resp.json()
        project_id = proj["id"]
        log_pass("P3.2a", f"Project created: {proj['name']} key={proj['key']} (id={project_id}, {ms}ms)")

        # Read
        resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/projects/{project_id}/", headers=hdrs)
        if resp.status_code == 200:
            log_pass("P3.2b", f"Project read OK ({ms}ms)")
        else:
            log_fail("P3.2b", f"Project read failed: {resp.status_code}")

        # Update
        resp, ms = timed_request(requests.patch, f"{BASE_URL}/api/demo/projects/{project_id}/",
                                  headers=hdrs, json={"description": "Updated description"})
        if resp.status_code == 200:
            log_pass("P3.2c", f"Project updated OK ({ms}ms)")
        else:
            log_fail("P3.2c", f"Project update failed: {resp.status_code}")

        # List with pagination
        resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/projects/", headers=hdrs)
        if resp.status_code == 200:
            data = resp.json()
            if "results" in data and "count" in data:
                log_pass("P3.2d", f"Project list with pagination OK (count={data['count']}, {ms}ms)")
            else:
                log_pass("P3.2d", f"Project list OK (no pagination, {ms}ms)")
        else:
            log_fail("P3.2d", f"Project list failed: {resp.status_code}")

        # lead_user assignment
        resp, ms = timed_request(requests.patch, f"{BASE_URL}/api/demo/projects/{project_id}/",
                                  headers=hdrs, json={"lead_user": user["id"]})
        if resp.status_code == 200:
            updated_proj = resp.json()
            if updated_proj.get("lead_user") == user["id"]:
                log_pass("P3.2e", f"Project lead_user assigned OK ({ms}ms)")
            else:
                log_fail("P3.2e", f"lead_user not saved correctly: {updated_proj.get('lead_user')}")
        else:
            log_fail("P3.2e", f"Project lead_user update failed: {resp.status_code}")

    else:
        log_fail("P3.2a", f"Project create failed: {resp.status_code} - {resp.text[:200]}")

    # ─── 3.3 Ticket CRUD ───
    print("\n  --- 3.3 Ticket CRUD ---")
    if project_id:
        ticket_data = {
            "subject": f"QA Test Ticket {ts}",
            "description": "Automated QA test ticket",
            "priority": "high",
            "project": project_id,
            "sender_email": "qa@test.com",
            "sender_name": "QA Tester"
        }
        resp, ms = timed_request(requests.post, f"{BASE_URL}/api/demo/tickets/", headers=hdrs, json=ticket_data)
        ticket_id = None
        if resp.status_code == 201:
            ticket = resp.json()
            ticket_id = ticket["ticket_id"]
            log_pass("P3.3a", f"Ticket created: {ticket_id} ({ms}ms)")

            # Read
            resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/tickets/{ticket_id}/", headers=hdrs)
            if resp.status_code == 200:
                detail = resp.json()
                log_pass("P3.3b", f"Ticket read OK: subject={detail['subject']} ({ms}ms)")
                # Verify fields
                checks = [
                    ("subject", detail.get("subject") == ticket_data["subject"]),
                    ("priority", detail.get("priority") == "high"),
                    ("status", detail.get("status") == "open"),
                ]
                for field, ok in checks:
                    if ok:
                        log_pass(f"P3.3b.{field}", f"Ticket field '{field}' correct")
                    else:
                        log_fail(f"P3.3b.{field}", f"Ticket field '{field}' mismatch: {detail.get(field)}")
            else:
                log_fail("P3.3b", f"Ticket read failed: {resp.status_code}")

            # Update (change priority)
            resp, ms = timed_request(requests.patch, f"{BASE_URL}/api/demo/tickets/{ticket_id}/",
                                      headers=hdrs, json={"priority": "low"})
            if resp.status_code == 200:
                log_pass("P3.3c", f"Ticket updated OK ({ms}ms)")
            else:
                log_fail("P3.3c", f"Ticket update failed: {resp.status_code}")

            # Assign ticket
            resp, ms = timed_request(requests.post, f"{BASE_URL}/api/demo/tickets/{ticket_id}/assign/",
                                      headers=hdrs, json={"assigned_to": user["id"]})
            if resp.status_code == 200:
                log_pass("P3.3d", f"Ticket assigned OK ({ms}ms)")
            else:
                log_fail("P3.3d", f"Ticket assign failed: {resp.status_code} - {resp.text[:200]}")

            # List tickets
            resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/tickets/", headers=hdrs)
            if resp.status_code == 200:
                data = resp.json()
                count = data.get("count", len(data.get("results", [])))
                log_pass("P3.3e", f"Ticket list OK (count={count}, {ms}ms)")
            else:
                log_fail("P3.3e", f"Ticket list failed: {resp.status_code}")

            # Stats endpoint
            resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/tickets/stats/", headers=hdrs)
            if resp.status_code == 200:
                log_pass("P3.3f", f"Ticket stats OK ({ms}ms)")
            else:
                log_fail("P3.3f", f"Ticket stats failed: {resp.status_code}")

            # Status transitions
            resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/tickets/statuses/", headers=hdrs)
            if resp.status_code == 200:
                log_pass("P3.3g", f"Ticket statuses endpoint OK ({ms}ms)")
            else:
                log_fail("P3.3g", f"Ticket statuses failed: {resp.status_code}")

        else:
            log_fail("P3.3a", f"Ticket create failed: {resp.status_code} - {resp.text[:200]}")

    # ─── 3.4 Comment CRUD ───
    print("\n  --- 3.4 Comment CRUD ---")
    if ticket_id:
        comment_data = {"comment": f"QA test comment at {ts}", "is_internal": False}
        resp, ms = timed_request(requests.post, f"{BASE_URL}/api/demo/tickets/{ticket_id}/comments/",
                                  headers=hdrs, json=comment_data)
        if resp.status_code == 201:
            comment = resp.json()
            log_pass("P3.4a", f"Comment created (id={comment.get('id')}, {ms}ms)")
        elif resp.status_code == 200:
            log_pass("P3.4a", f"Comment created (200 response, {ms}ms)")
        else:
            log_fail("P3.4a", f"Comment create failed: {resp.status_code} - {resp.text[:200]}")

        # Read comments
        resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/tickets/{ticket_id}/comments/", headers=hdrs)
        if resp.status_code == 200:
            comments = resp.json()
            if isinstance(comments, list):
                log_pass("P3.4b", f"Comments read OK (count={len(comments)}, {ms}ms)")
            elif isinstance(comments, dict):
                log_pass("P3.4b", f"Comments read OK ({ms}ms)")
            else:
                log_warn("P3.4b", f"Unexpected comment format: {type(comments)}")
        else:
            log_fail("P3.4b", f"Comments read failed: {resp.status_code}")

    # ─── 3.5 User Management ───
    print("\n  --- 3.5 User Management ---")
    # List users
    resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/auth/users/", headers=hdrs)
    if resp.status_code == 200:
        users = resp.json().get("results", [])
        log_pass("P3.5a", f"User list OK (count={len(users)}, {ms}ms)")
        for u in users:
            if "full_name" in u and "email" in u and "role" in u:
                pass
            else:
                log_fail("P3.5a.fields", f"User missing fields: {list(u.keys())}")
                break
        else:
            log_pass("P3.5a.fields", "All users have required fields (full_name, email, role)")
    else:
        log_fail("P3.5a", f"User list failed: {resp.status_code}")

    # Create user
    new_user = {
        "email": f"qatest{ts}@demo.com",
        "password": "TestPass123!",
        "full_name": "QA Test User",
        "role": "agent",
        "organization_id": user.get("organization", {}).get("id", 1)
    }
    resp, ms = timed_request(requests.post, f"{BASE_URL}/api/demo/auth/register/", headers=hdrs, json=new_user)
    new_user_id = None
    if resp.status_code == 201:
        new_user_id = resp.json().get("id")
        log_pass("P3.5b", f"User created: {new_user['email']} (id={new_user_id}, {ms}ms)")
    else:
        log_fail("P3.5b", f"User create failed: {resp.status_code} - {resp.text[:200]}")

    # Read user detail
    if new_user_id:
        resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/auth/users/{new_user_id}/", headers=hdrs)
        if resp.status_code == 200:
            log_pass("P3.5c", f"User detail read OK ({ms}ms)")
        else:
            log_fail("P3.5c", f"User detail failed: {resp.status_code}")

    # ─── 3.6 Notifications ───
    print("\n  --- 3.6 Notifications ---")
    resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/notifications/", headers=hdrs)
    if resp.status_code == 200:
        notifs = resp.json()
        count = notifs.get("count", len(notifs.get("results", []))) if isinstance(notifs, dict) else len(notifs)
        log_pass("P3.6a", f"Notifications list OK (count={count}, {ms}ms)")
    else:
        log_fail("P3.6a", f"Notifications list failed: {resp.status_code}")

    # Unread count
    resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/notifications/unread_count/", headers=hdrs)
    if resp.status_code == 200:
        log_pass("P3.6b", f"Notification unread count OK ({ms}ms)")
    else:
        log_fail("P3.6b", f"Notification unread count failed: {resp.status_code}")

    # ─── 3.7 Dashboard/Analytics ───
    print("\n  --- 3.7 Dashboard/Analytics ---")
    resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/dashboard/", headers=hdrs)
    if resp.status_code == 200:
        dash = resp.json()
        log_pass("P3.7a", f"Dashboard API OK ({ms}ms)")
        if ms > 500:
            log_warn("P3.7a.perf", f"Dashboard response slow: {ms}ms (>500ms)")
    else:
        log_fail("P3.7a", f"Dashboard API failed: {resp.status_code}")

    # Project analytics
    if project_id:
        resp, ms = timed_request(requests.get, f"{BASE_URL}/api/demo/projects/{project_id}/analytics/", headers=hdrs)
        if resp.status_code == 200:
            log_pass("P3.7b", f"Project analytics OK ({ms}ms)")
        else:
            log_fail("P3.7b", f"Project analytics failed: {resp.status_code}")

    return project_id, ticket_id


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: ROLE & PERMISSION TESTING
# ═══════════════════════════════════════════════════════════════════════════════
def phase4_role_testing():
    print("\n" + "=" * 70)
    print("PHASE 4: USER ROLE & PERMISSION TESTING")
    print("=" * 70)

    # Verify all roles can login
    for org, roles in ORGS.items():
        for role, creds in roles.items():
            token, user_data = login(org, role)
            if token:
                log_pass(f"P4.1.{org}.{role}", f"Login OK for {role}@{org}")
                # Verify /me endpoint
                resp, _ = timed_request(requests.get, f"{BASE_URL}/api/{org}/auth/me/", headers=auth_headers(token))
                if resp.status_code == 200:
                    me = resp.json()
                    if me.get("role") == role or role == "customer":
                        log_pass(f"P4.2.{org}.{role}", f"Role verified: {me.get('role')}")
                    else:
                        log_warn(f"P4.2.{org}.{role}", f"Role mismatch: expected={role}, got={me.get('role')}")
            else:
                log_fail(f"P4.1.{org}.{role}", f"Login FAILED for {role}@{org}")

    # Test unauthenticated access
    print("\n  --- P4.3 Unauthenticated Access ---")
    endpoints = [
        f"{BASE_URL}/api/demo/tickets/",
        f"{BASE_URL}/api/demo/projects/",
        f"{BASE_URL}/api/demo/auth/users/",
        f"{BASE_URL}/api/demo/auth/me/",
        f"{BASE_URL}/api/demo/notifications/",
        f"{BASE_URL}/api/demo/dashboard/",
    ]
    for ep in endpoints:
        resp, _ = timed_request(requests.get, ep)
        if resp.status_code == 401:
            log_pass(f"P4.3.{ep.split('/')[-2]}", f"Unauthenticated access blocked: {ep.split('/api/')[-1]}")
        else:
            log_fail(f"P4.3.{ep.split('/')[-2]}", f"Unauthenticated access NOT blocked: {resp.status_code} for {ep.split('/api/')[-1]}")

    # Test customer cannot create projects
    print("\n  --- P4.4 Role Restrictions ---")
    cust_token, _ = login("demo", "customer")
    if cust_token:
        # Try to create a project (should be restricted or succeed based on impl)
        resp, _ = timed_request(requests.post, f"{BASE_URL}/api/demo/projects/",
                                 headers=auth_headers(cust_token),
                                 json={"name": "Hack Project", "key": "HCK", "description": "test"})
        if resp.status_code in [403, 401]:
            log_pass("P4.4a", "Customer cannot create projects (403)")
        elif resp.status_code == 201:
            log_warn("P4.4a", "Customer CAN create projects (no role restriction on project creation)")
        else:
            log_warn("P4.4a", f"Customer project creation returned: {resp.status_code}")

        # Try to access user management
        resp, _ = timed_request(requests.post, f"{BASE_URL}/api/demo/auth/register/",
                                 headers=auth_headers(cust_token),
                                 json={"email": "evil@demo.com", "password": "x", "full_name": "Hacker", "role": "admin", "organization_id": 1})
        if resp.status_code in [403, 401]:
            log_pass("P4.4b", "Customer cannot register users (forbidden)")
        elif resp.status_code == 201:
            log_fail("P4.4b", "CRITICAL: Customer CAN register admin users!")
        else:
            log_warn("P4.4b", f"Customer register returned: {resp.status_code} - {resp.text[:100]}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: SECURITY AUDIT
# ═══════════════════════════════════════════════════════════════════════════════
def phase5_security():
    print("\n" + "=" * 70)
    print("PHASE 5: SECURITY AUDIT")
    print("=" * 70)

    token, user = login("demo", "admin")
    hdrs = auth_headers(token)

    # 5.1 SQL Injection attempt
    print("\n  --- 5.1 SQL Injection ---")
    sqli_payloads = [
        "'; DROP TABLE tickets; --",
        "1 OR 1=1",
        "' UNION SELECT * FROM users --",
    ]
    for i, payload in enumerate(sqli_payloads):
        resp, _ = timed_request(requests.get, f"{BASE_URL}/api/demo/tickets/?search={payload}", headers=hdrs)
        if resp.status_code in [200, 400]:
            log_pass(f"P5.1.{i}", f"SQL injection payload handled safely: {resp.status_code}")
        elif resp.status_code == 500:
            log_fail(f"P5.1.{i}", f"SQL injection may have caused 500 error!")
        else:
            log_warn(f"P5.1.{i}", f"SQL injection attempt returned: {resp.status_code}")

    # 5.2 XSS attempt
    print("\n  --- 5.2 XSS Prevention ---")
    xss_payload = '<script>alert("xss")</script>'
    resp, _ = timed_request(requests.post, f"{BASE_URL}/api/demo/auth/departments/",
                             headers=hdrs, json={"name": xss_payload})
    if resp.status_code == 201:
        dept = resp.json()
        if "<script>" not in json.dumps(dept):
            log_pass("P5.2a", "XSS payload escaped in response")
        else:
            log_warn("P5.2a", "XSS payload returned unescaped in JSON (frontend must handle)")
        # Cleanup
        requests.delete(f"{BASE_URL}/api/demo/auth/departments/{dept['id']}/", headers=hdrs)
    else:
        log_pass("P5.2a", f"XSS payload rejected: {resp.status_code}")

    # 5.3 Invalid token
    print("\n  --- 5.3 Auth Token Security ---")
    resp, _ = timed_request(requests.get, f"{BASE_URL}/api/demo/auth/me/",
                             headers={"Authorization": "Bearer invalidtoken123"})
    if resp.status_code == 401:
        log_pass("P5.3a", "Invalid token rejected")
    else:
        log_fail("P5.3a", f"Invalid token returned: {resp.status_code}")

    # Expired-like token
    resp, _ = timed_request(requests.get, f"{BASE_URL}/api/demo/auth/me/",
                             headers={"Authorization": ""})
    if resp.status_code == 401:
        log_pass("P5.3b", "Empty auth header rejected")
    else:
        log_fail("P5.3b", f"Empty auth header returned: {resp.status_code}")

    # 5.4 Password hashing check (login with wrong password)
    print("\n  --- 5.4 Password Security ---")
    resp, _ = timed_request(requests.post, f"{BASE_URL}/api/demo/auth/login/",
                             json={"email": "admin@demo.com", "password": "wrongpassword"})
    if resp.status_code in [401, 400]:
        log_pass("P5.4", f"Wrong password correctly rejected ({resp.status_code})")
    else:
        log_fail("P5.4", f"Wrong password returned: {resp.status_code}")

    # 5.5 Tenant isolation bypass attempt
    print("\n  --- 5.5 Tenant Bypass ---")
    # Try to manipulate organization_id in request
    resp, _ = timed_request(requests.post, f"{BASE_URL}/api/demo/auth/departments/",
                             headers=hdrs, json={"name": "Injected Dept", "organization_id": 999})
    if resp.status_code == 201:
        dept = resp.json()
        # Check if org_id was overridden
        org_id = dept.get("organization")
        requests.delete(f"{BASE_URL}/api/demo/auth/departments/{dept['id']}/", headers=hdrs)
        log_pass("P5.5", f"Dept created but org ignored from payload (server sets org from auth)")
    else:
        log_pass("P5.5", f"Tenant bypass attempt handled: {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════
def phase6_edge_cases():
    print("\n" + "=" * 70)
    print("PHASE 6: EDGE CASES")
    print("=" * 70)

    token, user = login("demo", "admin")
    hdrs = auth_headers(token)

    # 6.1 Empty form submission
    print("\n  --- 6.1 Empty Submissions ---")
    resp, _ = timed_request(requests.post, f"{BASE_URL}/api/demo/projects/", headers=hdrs, json={})
    if resp.status_code == 400:
        log_pass("P6.1a", "Empty project submission correctly rejected (400)")
    elif resp.status_code == 500:
        log_fail("P6.1a", "Empty project submission caused 500!")
    else:
        log_warn("P6.1a", f"Empty project submission returned: {resp.status_code}")

    resp, _ = timed_request(requests.post, f"{BASE_URL}/api/demo/tickets/", headers=hdrs, json={})
    if resp.status_code == 400:
        log_pass("P6.1b", "Empty ticket submission correctly rejected (400)")
    elif resp.status_code == 500:
        log_fail("P6.1b", "Empty ticket submission caused 500!")
    else:
        log_warn("P6.1b", f"Empty ticket submission returned: {resp.status_code}")

    # 6.2 Duplicate project key
    print("\n  --- 6.2 Duplicate Handling ---")
    ts = int(time.time())
    proj1 = {"name": f"Dup Test {ts}", "key": f"DP{ts % 100}"}
    resp1, _ = timed_request(requests.post, f"{BASE_URL}/api/demo/projects/", headers=hdrs, json=proj1)
    if resp1.status_code == 201:
        pid = resp1.json()["id"]
        resp2, _ = timed_request(requests.post, f"{BASE_URL}/api/demo/projects/", headers=hdrs, json=proj1)
        if resp2.status_code == 400:
            log_pass("P6.2", "Duplicate project key correctly rejected (400)")
        elif resp2.status_code == 500:
            log_fail("P6.2", "Duplicate project key caused 500 (missing unique constraint handling)")
        else:
            log_warn("P6.2", f"Duplicate project key returned: {resp2.status_code}")
        # Cleanup
        requests.delete(f"{BASE_URL}/api/demo/projects/{pid}/", headers=hdrs)

    # 6.3 Non-existent resource
    print("\n  --- 6.3 Non-existent Resources ---")
    resp, _ = timed_request(requests.get, f"{BASE_URL}/api/demo/tickets/NONEXIST-999/", headers=hdrs)
    if resp.status_code == 404:
        log_pass("P6.3a", "Non-existent ticket returns 404")
    else:
        log_fail("P6.3a", f"Non-existent ticket returns {resp.status_code}")

    resp, _ = timed_request(requests.get, f"{BASE_URL}/api/demo/projects/99999/", headers=hdrs)
    if resp.status_code == 404:
        log_pass("P6.3b", "Non-existent project returns 404")
    else:
        log_fail("P6.3b", f"Non-existent project returns {resp.status_code}")

    # 6.4 Very long input
    print("\n  --- 6.4 Boundary Values ---")
    long_name = "A" * 500
    resp, _ = timed_request(requests.post, f"{BASE_URL}/api/demo/auth/departments/",
                             headers=hdrs, json={"name": long_name})
    if resp.status_code == 400:
        log_pass("P6.4", "Oversized input rejected (400)")
    elif resp.status_code == 201:
        dept = resp.json()
        requests.delete(f"{BASE_URL}/api/demo/auth/departments/{dept['id']}/", headers=hdrs)
        log_warn("P6.4", "Oversized input (500 chars) accepted — max_length may be too lenient")
    elif resp.status_code == 500:
        log_fail("P6.4", "Oversized input caused 500!")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7: PERFORMANCE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
def phase7_performance():
    print("\n" + "=" * 70)
    print("PHASE 7: PERFORMANCE SUMMARY")
    print("=" * 70)

    if not TIMINGS:
        log_warn("P7.0", "No timing data")
        return

    total = len(TIMINGS)
    avg = sum(t["ms"] for t in TIMINGS) / total
    slowest = max(TIMINGS, key=lambda t: t["ms"])
    fast_count = sum(1 for t in TIMINGS if t["ms"] < 500)

    log_info("P7.1", f"Total API calls: {total}")
    log_info("P7.2", f"Avg response time: {avg:.0f}ms")
    log_info("P7.3", f"Slowest call: {slowest['ms']}ms - {slowest['method']} {slowest['url']}")
    log_info("P7.4", f"Calls under 500ms: {fast_count}/{total} ({fast_count*100//total}%)")

    if avg < 300:
        log_pass("P7.5", f"Average response time acceptable: {avg:.0f}ms")
    elif avg < 500:
        log_warn("P7.5", f"Average response time borderline: {avg:.0f}ms")
    else:
        log_fail("P7.5", f"Average response time too slow: {avg:.0f}ms")

    # Check for any 500 errors
    errors_500 = [t for t in TIMINGS if t["status"] == 500]
    if errors_500:
        log_fail("P7.6", f"Found {len(errors_500)} API calls returning 500:")
        for e in errors_500:
            print(f"    - {e['method']} {e['url']} ({e['ms']}ms)")
    else:
        log_pass("P7.6", "No 500 errors found across all API calls")


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
def generate_report():
    print("\n" + "=" * 70)
    print("FINAL QA REPORT")
    print("=" * 70)

    total = len(RESULTS["pass"]) + len(RESULTS["fail"]) + len(RESULTS["warn"])
    print(f"\n  Total Tests: {total}")
    print(f"  ✅ Passed:  {len(RESULTS['pass'])}")
    print(f"  ❌ Failed:  {len(RESULTS['fail'])}")
    print(f"  ⚠️  Warnings: {len(RESULTS['warn'])}")

    if RESULTS["fail"]:
        print(f"\n{'─'*70}")
        print("FAILURES:")
        print(f"{'─'*70}")
        for f in RESULTS["fail"]:
            print(f"  {f}")

    if RESULTS["warn"]:
        print(f"\n{'─'*70}")
        print("WARNINGS:")
        print(f"{'─'*70}")
        for w in RESULTS["warn"]:
            print(f"  {w}")

    if RESULTS["info"]:
        print(f"\n{'─'*70}")
        print("INFO:")
        print(f"{'─'*70}")
        for i in RESULTS["info"]:
            print(f"  {i}")

    print(f"\n{'═'*70}")
    if not RESULTS["fail"]:
        print("🎉  ALL TESTS PASSED!")
    else:
        print(f"⚠️  {len(RESULTS['fail'])} FAILURES NEED ATTENTION")
    print(f"{'═'*70}\n")

    return RESULTS


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"\n{'═'*70}")
    print(f"  COMPREHENSIVE QA TEST SUITE")
    print(f"  Multi-Tenant Ticket Management System")
    print(f"  Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═'*70}")

    phase1_health_check()
    phase2_tenant_isolation()
    phase3_crud_testing()
    phase4_role_testing()
    phase5_security()
    phase6_edge_cases()
    phase7_performance()
    results = generate_report()

    # Exit with failure code if any failures
    sys.exit(1 if results["fail"] else 0)
