"""
Locust Load Testing Script for Multi-Tenant Ticket System
Run: locust -f tests/locustfile.py --host=http://localhost:8000
Then open http://localhost:8089 to configure and run tests.
"""
import time
import random
import json
from locust import HttpUser, task, between, events


class TicketSystemUser(HttpUser):
    """Simulates a typical user session: login, browse, create, comment."""
    
    wait_time = between(1, 3)
    
    USERS = [
        {"org": "demo", "email": "admin@demo.com", "password": "password123"},
        {"org": "demo", "email": "agent@demo.com", "password": "password123"},
        {"org": "demo", "email": "customer@demo.com", "password": "password123"},
        {"org": "acme", "email": "admin@acme.com", "password": "password123"},
        {"org": "omega", "email": "admin@omega.com", "password": "password123"},
        {"org": "omega", "email": "agent@omega.com", "password": "password123"},
    ]

    def on_start(self):
        """Login at the start of each user session."""
        user = random.choice(self.USERS)
        self.org = user["org"]
        self.email = user["email"]
        
        resp = self.client.post(
            f"/api/{self.org}/auth/login/",
            json={"email": user["email"], "password": user["password"]},
            name="/api/[org]/auth/login/"
        )
        
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("access_token")
            self.user_data = data.get("user", {})
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
        else:
            self.token = None
            self.headers = {}

    # ── Browse Tasks ──────────────────────────────────────────────────

    @task(5)
    def list_tickets(self):
        """Most common action: view ticket list."""
        if not self.token:
            return
        self.client.get(
            f"/api/{self.org}/tickets/",
            headers=self.headers,
            name="/api/[org]/tickets/"
        )

    @task(3)
    def list_projects(self):
        """View project list."""
        if not self.token:
            return
        self.client.get(
            f"/api/{self.org}/projects/",
            headers=self.headers,
            name="/api/[org]/projects/"
        )

    @task(2)
    def view_ticket_detail(self):
        """View a specific ticket."""
        if not self.token:
            return
        resp = self.client.get(
            f"/api/{self.org}/tickets/",
            headers=self.headers,
            name="/api/[org]/tickets/ (for detail)"
        )
        if resp.status_code == 200:
            tickets = resp.json().get("results", [])
            if tickets:
                tid = random.choice(tickets)["ticket_id"]
                self.client.get(
                    f"/api/{self.org}/tickets/{tid}/",
                    headers=self.headers,
                    name="/api/[org]/tickets/[id]/"
                )

    @task(2)
    def get_users(self):
        """View user list."""
        if not self.token:
            return
        self.client.get(
            f"/api/{self.org}/auth/users/",
            headers=self.headers,
            name="/api/[org]/auth/users/"
        )

    @task(2)
    def get_notifications(self):
        """Check notifications."""
        if not self.token:
            return
        self.client.get(
            f"/api/{self.org}/notifications/",
            headers=self.headers,
            name="/api/[org]/notifications/"
        )

    @task(1)
    def get_departments(self):
        """View departments."""
        if not self.token:
            return
        self.client.get(
            f"/api/{self.org}/auth/departments/",
            headers=self.headers,
            name="/api/[org]/auth/departments/"
        )

    @task(2)
    def ticket_stats(self):
        """View ticket statistics."""
        if not self.token:
            return
        self.client.get(
            f"/api/{self.org}/tickets/stats/",
            headers=self.headers,
            name="/api/[org]/tickets/stats/"
        )

    @task(1)
    def get_me(self):
        """Check own profile."""
        if not self.token:
            return
        self.client.get(
            f"/api/{self.org}/auth/me/",
            headers=self.headers,
            name="/api/[org]/auth/me/"
        )

    # ── Write Tasks ──────────────────────────────────────────────────

    @task(1)
    def create_ticket(self):
        """Create a new ticket (less frequent)."""
        if not self.token:
            return
        
        # Get a project first
        resp = self.client.get(
            f"/api/{self.org}/projects/",
            headers=self.headers,
            name="/api/[org]/projects/ (for create)"
        )
        if resp.status_code != 200:
            return
            
        projects = resp.json().get("results", [])
        if not projects:
            return
            
        project = random.choice(projects)
        ts = int(time.time() * 1000)
        
        self.client.post(
            f"/api/{self.org}/tickets/",
            headers=self.headers,
            json={
                "subject": f"Load Test Ticket {ts}",
                "description": "Created during load test",
                "priority": random.choice(["low", "medium", "high", "critical"]),
                "project": project["id"],
                "sender_email": self.email
            },
            name="/api/[org]/tickets/ (CREATE)"
        )

    @task(1)
    def add_comment(self):
        """Add a comment to a ticket."""
        if not self.token:
            return
            
        resp = self.client.get(
            f"/api/{self.org}/tickets/",
            headers=self.headers,
            name="/api/[org]/tickets/ (for comment)"
        )
        if resp.status_code != 200:
            return
            
        tickets = resp.json().get("results", [])
        if not tickets:
            return
            
        ticket = random.choice(tickets)
        self.client.post(
            f"/api/{self.org}/tickets/{ticket['ticket_id']}/comments/",
            headers=self.headers,
            json={"comment": f"Load test comment at {time.time()}"},
            name="/api/[org]/tickets/[id]/comments/ (CREATE)"
        )


class HealthCheckUser(HttpUser):
    """Lightweight user that just checks health."""
    
    wait_time = between(5, 10)

    @task
    def health_check(self):
        self.client.get("/health/", name="/health/")

    @task
    def landing_page(self):
        self.client.get("/", name="/ (landing)")
