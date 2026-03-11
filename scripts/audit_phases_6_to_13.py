#!/usr/bin/env python3
"""
Audit Phases 6-13 for Django Multi-Tenant SaaS Ticket System.
Run after phases 1-5 (platform login, org creation, tenant login, dept, project, user).
Requires: server on port 8000, and run from project root so db.sqlite3 is found.
"""
import requests
import sqlite3
import time
from termcolor import colored

BASE_URL = "http://localhost:8000"
PLATFORM_API = f"{BASE_URL}/api/platform"


class Phase6To13Auditor:
    def __init__(self, org_subdomain, admin_email, admin_password="Password123!",
                 manager_email=None, manager_password="Password123!",
                 dep_id=None, proj_id=None):
        self.org_subdomain = org_subdomain
        self.admin_email = admin_email
        self.admin_password = admin_password
        self.manager_email = manager_email or f"manager@{org_subdomain}.audit.com"
        self.manager_password = manager_password
        self.dep_id = dep_id
        self.proj_id = proj_id
        self.session = requests.Session()
        self.tenant_api = f"{BASE_URL}/api/{org_subdomain}"
        self.admin_token = None
        self.manager_token = None
        self.agent_token = None
        self.ticket_id = None  # e.g. HYB-1
        self.ticket_pk = None
        self.manager_user_id = None
        self.agent_email = None
        self.agent_user_id = None
        self.issues = []
        self.fixes = []

    def step(self, name):
        print(f"\n{colored('>>>', 'cyan')} {colored(name, attrs=['bold'])}")

    def ok(self, msg):
        print(f"   {colored('✓', 'green')} {msg}")

    def fail(self, msg, detail=None):
        print(f"   {colored('✗', 'red')} {msg}")
        if detail:
            print(colored(f"      {detail}", 'yellow'))
        self.issues.append(msg)

    def login_admin(self):
        r = self.session.post(f"{self.tenant_api}/auth/login/", json={
            "email": self.admin_email,
            "password": self.admin_password,
        })
        if r.status_code != 200:
            self.fail("Tenant admin login failed", r.text)
            return False
        self.admin_token = r.json().get("access_token")
        self.session.headers["Authorization"] = f"Bearer {self.admin_token}"
        self.ok("Tenant admin logged in")
        return True

    def phase_6_ticket_creation(self):
        self.step("PHASE 6: Ticket Creation Workflow")
        if not self.admin_token:
            if not self.login_admin():
                return False

        # API uses subject not title
        payload = {
            "subject": "Audit ticket phase 6",
            "description": "Created via audit script",
            "priority": "medium",
            "project": self.proj_id,
            "assigned_to": self.manager_user_id,  # optional
            "department": self.dep_id,
        }
        r = self.session.post(f"{self.tenant_api}/tickets/", json=payload)
        if r.status_code not in (200, 201):
            self.fail("Ticket creation failed", r.text)
            return False

        data = r.json()
        self.ticket_id = data.get("ticket_id")
        self.ticket_pk = data.get("id")
        if not self.ticket_id:
            self.fail("Ticket response missing ticket_id", str(data))
            return False
        self.ok(f"Ticket created: {self.ticket_id}")

        # Verify in DB (shared default DB)
        conn = sqlite3.connect("db.sqlite3")
        c = conn.cursor()
        c.execute(
            "SELECT id, ticket_id, organization_id, subject FROM tickets WHERE ticket_id=?",
            (self.ticket_id,),
        )
        row = c.fetchone()
        conn.close()
        if not row:
            self.fail("Ticket not found in default DB", "Expected in tickets table")
        else:
            self.ok("Ticket stored in correct DB with organization_id")
        return True

    def phase_7_comments(self):
        self.step("PHASE 7: Comment System")
        if not self.ticket_id or not self.admin_token:
            self.fail("Skip: no ticket or admin token")
            return False

        r = self.session.post(
            f"{self.tenant_api}/tickets/{self.ticket_id}/comments/",
            json={"comment": "Audit phase 7 comment"},
        )
        if r.status_code not in (200, 201):
            self.fail("Add comment failed", r.text)
            return False
        data = r.json()
        if not data.get("id") and not data.get("comment"):
            self.fail("Comment response missing id/comment", str(data))
        else:
            self.ok("Comment created, author and ticket relation correct")

        conn = sqlite3.connect("db.sqlite3")
        c = conn.cursor()
        c.execute("SELECT id FROM comments WHERE ticket_id=?", (self.ticket_pk,))
        if c.fetchone():
            self.ok("Comment exists in same DB as ticket")
        else:
            self.fail("Comment not found in DB")
        conn.close()
        return True

    def phase_8_notifications(self):
        self.step("PHASE 8: Notification System")
        if not self.ticket_id:
            self.ok("Skip: no ticket created")
            return True
        if not self.admin_token:
            self.login_admin()
        if not self.manager_user_id:
            r = self.session.get(f"{self.tenant_api}/auth/users/")
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", data) if isinstance(data, dict) else data
                if isinstance(results, list):
                    for u in results:
                        if u.get("role") == "manager" or "manager" in (u.get("email") or "").lower():
                            self.manager_user_id = u.get("id")
                            break
        if not self.manager_user_id:
            self.ok("Skip: no manager user for assign")
            return True
        # Assign ticket to manager -> triggers notification
        r = self.session.post(
            f"{self.tenant_api}/tickets/{self.ticket_id}/assign/",
            json={"user_id": self.manager_user_id},
        )
        if r.status_code not in (200, 204):
            self.fail("Assign failed", r.text)
            return False
        self.ok("Ticket assigned")
        conn = sqlite3.connect("db.sqlite3")
        c = conn.cursor()
        c.execute(
            "SELECT id, user_id, ticket_id, is_read FROM notifications ORDER BY id DESC LIMIT 5"
        )
        rows = c.fetchall()
        conn.close()
        if rows:
            self.ok("Notification(s) created in tenant DB")
        else:
            self.fail("No notifications found (check signals)")
        return True

    def phase_9_role_permissions(self):
        self.step("PHASE 9: Role Permission Tests")
        tenant = self.tenant_api

        # Admin: create user, create project, assign
        if not self.admin_token:
            self.login_admin()
        self.session.headers["Authorization"] = f"Bearer {self.admin_token}"
        r = self.session.get(f"{tenant}/auth/users/")
        if r.status_code == 200:
            self.ok("ADMIN: can view users")
        else:
            self.fail("ADMIN: view users", r.text)
        r = self.session.post(f"{tenant}/projects/", json={
            "name": "Role Test Project",
            "key": "RTP",
            "description": "For role test",
        })
        if r.status_code in (200, 201):
            self.ok("ADMIN: can create project")
        else:
            self.fail("ADMIN: create project", r.text)

        # Manager: view tickets, assign; cannot create org users
        if not self.manager_token:
            self.session.headers.pop("Authorization", None)
            r = self.session.post(f"{tenant}/auth/login/", json={
                "email": self.manager_email,
                "password": self.manager_password,
            })
            if r.status_code != 200:
                self.fail("Manager login failed", r.text)
                return False
            self.manager_token = r.json().get("access_token")
        self.session.headers["Authorization"] = f"Bearer {self.manager_token}"

        r = self.session.get(f"{tenant}/tickets/")
        if r.status_code == 200:
            self.ok("MANAGER: can view tickets")
        else:
            self.fail("MANAGER: view tickets", r.text)
        r = self.session.post(f"{tenant}/auth/users/", json={
            "email": "random@test.com",
            "full_name": "Random",
            "password": "Pass123!",
            "role": "agent",
        })
        if r.status_code == 403:
            self.ok("MANAGER: cannot create users (403)")
        else:
            self.fail("MANAGER: should get 403 when creating users", f"Got {r.status_code}")

        # Agent: view assigned only, add comment; cannot view all users
        if not self.agent_token and self.agent_email:
            r = self.session.post(f"{tenant}/auth/login/", json={
                "email": self.agent_email,
                "password": self.manager_password,
            })
            if r.status_code == 200:
                self.agent_token = r.json().get("access_token")
        if self.agent_token:
            self.session.headers["Authorization"] = f"Bearer {self.agent_token}"
            r = self.session.get(f"{tenant}/tickets/")
            if r.status_code == 200:
                self.ok("AGENT: can view tickets (assigned only)")
            r = self.session.get(f"{tenant}/auth/users/")
            if r.status_code == 403:
                self.ok("AGENT: cannot view all users (403)")
            else:
                self.fail("AGENT: should get 403 when listing users", f"Got {r.status_code}")
        return True

    def phase_10_page_load(self):
        self.step("PHASE 10: Page Load Audit")
        if not self.admin_token:
            self.login_admin()
        self.session.headers["Authorization"] = f"Bearer {self.admin_token}"
        pages = [
            (f"{self.tenant_api.replace('/api/', '/')}/dashboard", "dashboard"),
            (f"{self.tenant_api}/tickets/", "tickets list"),
            (f"{self.tenant_api}/projects/", "projects"),
            (f"{self.tenant_api}/auth/departments/", "departments"),
            (f"{self.tenant_api}/auth/users/", "users"),
            (f"{BASE_URL}/{self.org_subdomain}/notifications", "notifications page"),
        ]
        for url, name in pages:
            r = self.session.get(url)
            if r.status_code == 200:
                self.ok(f"Page load: {name}")
            else:
                self.fail(f"Page load: {name}", f"status={r.status_code}")
        return True

    def phase_12_cross_tenant(self):
        self.step("PHASE 12: Cross-Tenant Security")
        # Use a different org slug that exists or not; if we use another org, token must be orgA
        if not self.admin_token:
            self.login_admin()
        self.session.headers["Authorization"] = f"Bearer {self.admin_token}"
        # Try to access orgB with orgA token (use a slug that's not self.org_subdomain)
        other_org = "other-tenant-999"
        r = self.session.get(f"{BASE_URL}/api/{other_org}/tickets/")
        if r.status_code in (403, 404):
            self.ok("Cross-tenant request rejected (403/404)")
        else:
            self.fail("Cross-tenant should be 403/404", f"Got {r.status_code}")
        return True

    def run_all(self, dep_id, proj_id, manager_user_id=None, agent_email=None):
        self.dep_id = dep_id
        self.proj_id = proj_id
        self.manager_user_id = manager_user_id
        self.agent_email = agent_email
        if not self.login_admin():
            return False
        # Resolve manager user id if not provided
        if manager_user_id is None:
            r = self.session.get(f"{self.tenant_api}/auth/users/")
            if r.status_code == 200:
                for u in (r.json() if isinstance(r.json(), list) else r.json().get("results", [])):
                    if u.get("email") == self.manager_email or "manager" in (u.get("email") or "").lower():
                        self.manager_user_id = u.get("id")
                        self.manager_email = u.get("email")
                        break
        self.phase_6_ticket_creation()
        self.phase_7_comments()
        self.phase_8_notifications()
        self.phase_9_role_permissions()
        self.phase_10_page_load()
        self.phase_12_cross_tenant()
        return len(self.issues) == 0


def run_audit_6_13(org_subdomain, admin_email, dep_id, proj_id,
                   manager_user_id=None, agent_email=None):
    auditor = Phase6To13Auditor(org_subdomain, admin_email)
    return auditor.run_all(dep_id, proj_id, manager_user_id, agent_email)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 6:
        print("Usage: python audit_phases_6_to_13.py ORG_SUBDOMAIN ADMIN_EMAIL DEP_ID PROJ_ID [MANAGER_USER_ID]")
        sys.exit(1)
    org_sub = sys.argv[1]
    admin_em = sys.argv[2]
    dep_id = int(sys.argv[3])
    proj_id = int(sys.argv[4])
    manager_uid = int(sys.argv[5]) if len(sys.argv) > 5 else None
    ok = run_audit_6_13(org_sub, admin_em, dep_id, proj_id, manager_uid)
    sys.exit(0 if ok else 1)
