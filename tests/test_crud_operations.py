"""
Pytest Test Cases for Multi-Tenant Ticket System CRUD Operations
Run: docker-compose exec web python -m pytest tests/test_crud_operations.py -v
"""
import pytest
import requests
import time

BASE_URL = "http://localhost:8000"


class TestConfig:
    """Shared test configuration and helpers."""
    
    @staticmethod
    def login(org, email, password="password123"):
        resp = requests.post(f"{BASE_URL}/api/{org}/auth/login/", json={
            "email": email, "password": password
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()
        return data["access_token"], data["user"]

    @staticmethod
    def headers(token):
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ════════════════════════════════════════════════════════════════════════
# AUTHENTICATION TESTS
# ════════════════════════════════════════════════════════════════════════
class TestAuthentication:
    
    def test_login_success(self):
        token, user = TestConfig.login("demo", "admin@demo.com")
        assert token is not None
        assert user["email"] == "admin@demo.com"

    def test_login_wrong_password(self):
        resp = requests.post(f"{BASE_URL}/api/demo/auth/login/", json={
            "email": "admin@demo.com", "password": "wrongpass"
        })
        assert resp.status_code in [401, 400]

    def test_login_nonexistent_user(self):
        resp = requests.post(f"{BASE_URL}/api/demo/auth/login/", json={
            "email": "fake@demo.com", "password": "password123"
        })
        assert resp.status_code in [401, 400]

    def test_login_wrong_org(self):
        resp = requests.post(f"{BASE_URL}/api/nonexistent/auth/login/", json={
            "email": "admin@demo.com", "password": "password123"
        })
        assert resp.status_code in [401, 404]

    def test_me_endpoint(self):
        token, _ = TestConfig.login("demo", "admin@demo.com")
        resp = requests.get(f"{BASE_URL}/api/demo/auth/me/", headers=TestConfig.headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@demo.com"
        assert "full_name" in data
        assert "role" in data

    def test_unauthenticated_access_blocked(self):
        endpoints = [
            f"{BASE_URL}/api/demo/tickets/",
            f"{BASE_URL}/api/demo/projects/",
            f"{BASE_URL}/api/demo/auth/users/",
            f"{BASE_URL}/api/demo/auth/me/",
            f"{BASE_URL}/api/demo/notifications/",
        ]
        for ep in endpoints:
            resp = requests.get(ep)
            assert resp.status_code == 401, f"Unauthenticated access not blocked: {ep}"

    def test_invalid_token_rejected(self):
        resp = requests.get(f"{BASE_URL}/api/demo/auth/me/",
                           headers={"Authorization": "Bearer invalidtoken123"})
        assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════════════
# DEPARTMENT CRUD TESTS
# ════════════════════════════════════════════════════════════════════════
class TestDepartmentCRUD:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token, self.user = TestConfig.login("demo", "admin@demo.com")
        self.hdrs = TestConfig.headers(self.token)
        self.ts = int(time.time())

    def test_create_department(self):
        resp = requests.post(f"{BASE_URL}/api/demo/auth/departments/",
                            headers=self.hdrs, json={"name": f"Test Dept {self.ts}"})
        assert resp.status_code == 201
        dept = resp.json()
        assert dept["name"] == f"Test Dept {self.ts}"
        # Cleanup
        requests.delete(f"{BASE_URL}/api/demo/auth/departments/{dept['id']}/", headers=self.hdrs)

    def test_read_department(self):
        # Create
        resp = requests.post(f"{BASE_URL}/api/demo/auth/departments/",
                            headers=self.hdrs, json={"name": f"Read Dept {self.ts}"})
        dept = resp.json()
        # Read
        resp = requests.get(f"{BASE_URL}/api/demo/auth/departments/{dept['id']}/", headers=self.hdrs)
        assert resp.status_code == 200
        assert resp.json()["name"] == f"Read Dept {self.ts}"
        # Cleanup
        requests.delete(f"{BASE_URL}/api/demo/auth/departments/{dept['id']}/", headers=self.hdrs)

    def test_update_department(self):
        resp = requests.post(f"{BASE_URL}/api/demo/auth/departments/",
                            headers=self.hdrs, json={"name": f"Update Dept {self.ts}"})
        dept = resp.json()
        resp = requests.patch(f"{BASE_URL}/api/demo/auth/departments/{dept['id']}/",
                             headers=self.hdrs, json={"name": "Updated Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"
        requests.delete(f"{BASE_URL}/api/demo/auth/departments/{dept['id']}/", headers=self.hdrs)

    def test_delete_department(self):
        resp = requests.post(f"{BASE_URL}/api/demo/auth/departments/",
                            headers=self.hdrs, json={"name": f"Delete Dept {self.ts}"})
        dept = resp.json()
        resp = requests.delete(f"{BASE_URL}/api/demo/auth/departments/{dept['id']}/", headers=self.hdrs)
        assert resp.status_code in [200, 204]

    def test_list_departments(self):
        resp = requests.get(f"{BASE_URL}/api/demo/auth/departments/", headers=self.hdrs)
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════════════════
# PROJECT CRUD TESTS
# ════════════════════════════════════════════════════════════════════════
class TestProjectCRUD:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token, self.user = TestConfig.login("demo", "admin@demo.com")
        self.hdrs = TestConfig.headers(self.token)
        self.ts = int(time.time())

    def test_create_project(self):
        resp = requests.post(f"{BASE_URL}/api/demo/projects/",
                            headers=self.hdrs, json={
                                "name": f"Test Project {self.ts}",
                                "key": f"TP{self.ts % 100}",
                                "description": "Test project"
                            })
        assert resp.status_code == 201
        proj = resp.json()
        assert proj["name"] == f"Test Project {self.ts}"
        assert proj["key"] == f"TP{self.ts % 100}"

    def test_read_project(self):
        resp = requests.post(f"{BASE_URL}/api/demo/projects/",
                            headers=self.hdrs, json={
                                "name": f"Read Project {self.ts}", "key": f"RP{self.ts % 100}"
                            })
        proj = resp.json()
        resp = requests.get(f"{BASE_URL}/api/demo/projects/{proj['id']}/", headers=self.hdrs)
        assert resp.status_code == 200

    def test_update_project(self):
        resp = requests.post(f"{BASE_URL}/api/demo/projects/",
                            headers=self.hdrs, json={
                                "name": f"Update Project {self.ts}", "key": f"UP{self.ts % 100}"
                            })
        proj = resp.json()
        resp = requests.patch(f"{BASE_URL}/api/demo/projects/{proj['id']}/",
                             headers=self.hdrs, json={"description": "Updated!"})
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated!"

    def test_assign_lead_user(self):
        resp = requests.post(f"{BASE_URL}/api/demo/projects/",
                            headers=self.hdrs, json={
                                "name": f"Lead Project {self.ts}", "key": f"LP{self.ts % 100}"
                            })
        proj = resp.json()
        resp = requests.patch(f"{BASE_URL}/api/demo/projects/{proj['id']}/",
                             headers=self.hdrs, json={"lead_user": self.user["id"]})
        assert resp.status_code == 200
        assert resp.json()["lead_user"] == self.user["id"]

    def test_project_analytics(self):
        resp = requests.get(f"{BASE_URL}/api/demo/projects/", headers=self.hdrs)
        projects = resp.json().get("results", [])
        if projects:
            pid = projects[0]["id"]
            resp = requests.get(f"{BASE_URL}/api/demo/projects/{pid}/analytics/", headers=self.hdrs)
            assert resp.status_code == 200

    def test_empty_project_rejected(self):
        resp = requests.post(f"{BASE_URL}/api/demo/projects/", headers=self.hdrs, json={})
        assert resp.status_code == 400

    def test_nonexistent_project_404(self):
        resp = requests.get(f"{BASE_URL}/api/demo/projects/99999/", headers=self.hdrs)
        assert resp.status_code == 404

    def test_list_projects_paginated(self):
        resp = requests.get(f"{BASE_URL}/api/demo/projects/", headers=self.hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data or isinstance(data, list)


# ════════════════════════════════════════════════════════════════════════
# TICKET CRUD TESTS
# ════════════════════════════════════════════════════════════════════════
class TestTicketCRUD:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token, self.user = TestConfig.login("demo", "admin@demo.com")
        self.hdrs = TestConfig.headers(self.token)
        self.ts = int(time.time())
        # Get a project ID
        resp = requests.get(f"{BASE_URL}/api/demo/projects/", headers=self.hdrs)
        projects = resp.json().get("results", [])
        self.project_id = projects[0]["id"] if projects else None

    def test_create_ticket(self):
        if not self.project_id:
            pytest.skip("No project available")
        resp = requests.post(f"{BASE_URL}/api/demo/tickets/", headers=self.hdrs, json={
            "subject": f"Test Ticket {self.ts}",
            "description": "Test description",
            "priority": "high",
            "project": self.project_id,
            "sender_email": "test@demo.com"
        })
        assert resp.status_code == 201
        ticket = resp.json()
        assert ticket["subject"] == f"Test Ticket {self.ts}"
        assert ticket["status"] == "open"

    def test_read_ticket(self):
        resp = requests.get(f"{BASE_URL}/api/demo/tickets/", headers=self.hdrs)
        assert resp.status_code == 200
        tickets = resp.json().get("results", [])
        if tickets:
            tid = tickets[0]["ticket_id"]
            resp = requests.get(f"{BASE_URL}/api/demo/tickets/{tid}/", headers=self.hdrs)
            assert resp.status_code == 200
            assert "subject" in resp.json()

    def test_update_ticket(self):
        resp = requests.get(f"{BASE_URL}/api/demo/tickets/", headers=self.hdrs)
        tickets = resp.json().get("results", [])
        if tickets:
            tid = tickets[0]["ticket_id"]
            resp = requests.patch(f"{BASE_URL}/api/demo/tickets/{tid}/",
                                 headers=self.hdrs, json={"priority": "low"})
            assert resp.status_code == 200

    def test_ticket_stats(self):
        resp = requests.get(f"{BASE_URL}/api/demo/tickets/stats/", headers=self.hdrs)
        assert resp.status_code == 200

    def test_ticket_statuses(self):
        resp = requests.get(f"{BASE_URL}/api/demo/tickets/statuses/", headers=self.hdrs)
        assert resp.status_code == 200

    def test_empty_ticket_rejected(self):
        resp = requests.post(f"{BASE_URL}/api/demo/tickets/", headers=self.hdrs, json={})
        assert resp.status_code == 400

    def test_nonexistent_ticket_404(self):
        resp = requests.get(f"{BASE_URL}/api/demo/tickets/FAKE-999/", headers=self.hdrs)
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════════════════
# COMMENT TESTS
# ════════════════════════════════════════════════════════════════════════
class TestComments:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token, self.user = TestConfig.login("demo", "admin@demo.com")
        self.hdrs = TestConfig.headers(self.token)

    def test_add_comment(self):
        resp = requests.get(f"{BASE_URL}/api/demo/tickets/", headers=self.hdrs)
        tickets = resp.json().get("results", [])
        if tickets:
            tid = tickets[0]["ticket_id"]
            resp = requests.post(f"{BASE_URL}/api/demo/tickets/{tid}/comments/",
                                headers=self.hdrs, json={"comment": "pytest comment"})
            assert resp.status_code in [200, 201]


# ════════════════════════════════════════════════════════════════════════
# MULTI-TENANT ISOLATION TESTS
# ════════════════════════════════════════════════════════════════════════
class TestTenantIsolation:
    
    def test_users_isolated(self):
        demo_token, _ = TestConfig.login("demo", "admin@demo.com")
        acme_token, _ = TestConfig.login("acme", "admin@acme.com")
        
        demo_resp = requests.get(f"{BASE_URL}/api/demo/auth/users/", headers=TestConfig.headers(demo_token))
        acme_resp = requests.get(f"{BASE_URL}/api/acme/auth/users/", headers=TestConfig.headers(acme_token))
        
        demo_emails = {u["email"] for u in demo_resp.json().get("results", [])}
        acme_emails = {u["email"] for u in acme_resp.json().get("results", [])}
        
        assert demo_emails.isdisjoint(acme_emails), "User data leaked between tenants"

    def test_nonexistent_tenant(self):
        resp = requests.get(f"{BASE_URL}/api/fakecorp/auth/users/")
        assert resp.status_code in [401, 404]


# ════════════════════════════════════════════════════════════════════════
# SECURITY TESTS
# ════════════════════════════════════════════════════════════════════════
class TestSecurity:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token, self.user = TestConfig.login("demo", "admin@demo.com")
        self.hdrs = TestConfig.headers(self.token)

    def test_sql_injection_safe(self):
        resp = requests.get(f"{BASE_URL}/api/demo/tickets/?search=' OR 1=1 --",
                           headers=self.hdrs)
        assert resp.status_code in [200, 400]

    def test_wrong_password_rejected(self):
        resp = requests.post(f"{BASE_URL}/api/demo/auth/login/",
                            json={"email": "admin@demo.com", "password": "wrong"})
        assert resp.status_code in [401, 400]

    def test_empty_auth_rejected(self):
        resp = requests.get(f"{BASE_URL}/api/demo/auth/me/", headers={"Authorization": ""})
        assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT TESTS
# ════════════════════════════════════════════════════════════════════════
class TestUserManagement:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token, self.user = TestConfig.login("demo", "admin@demo.com")
        self.hdrs = TestConfig.headers(self.token)

    def test_list_users(self):
        resp = requests.get(f"{BASE_URL}/api/demo/auth/users/", headers=self.hdrs)
        assert resp.status_code == 200
        users = resp.json().get("results", [])
        assert len(users) > 0
        for u in users:
            assert "full_name" in u
            assert "email" in u
            assert "role" in u

    def test_user_detail(self):
        resp = requests.get(f"{BASE_URL}/api/demo/auth/users/", headers=self.hdrs)
        users = resp.json().get("results", [])
        if users:
            uid = users[0]["id"]
            resp = requests.get(f"{BASE_URL}/api/demo/auth/users/{uid}/", headers=self.hdrs)
            assert resp.status_code == 200


# ════════════════════════════════════════════════════════════════════════
# NOTIFICATION TESTS
# ════════════════════════════════════════════════════════════════════════
class TestNotifications:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token, self.user = TestConfig.login("demo", "admin@demo.com")
        self.hdrs = TestConfig.headers(self.token)

    def test_list_notifications(self):
        resp = requests.get(f"{BASE_URL}/api/demo/notifications/", headers=self.hdrs)
        assert resp.status_code == 200
