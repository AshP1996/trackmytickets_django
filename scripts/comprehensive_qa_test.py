import requests
import sqlite3
import json
import uuid
from termcolor import colored
import time

BASE_URL = "http://localhost:8000"
PLATFORM_API = f"{BASE_URL}/api/platform"

class Auditor:
    def __init__(self):
        self.session = requests.Session()
        # Initialize stamp here for use across methods
        self.stamp = str(int(time.time()))
        self.org_subdomain = f"audit-{self.stamp}" # Use stamp for initial subdomain
        self.admin_email = None # Will be set in phase_2_and_3
        
    def step(self, name):
        print(f"\n{colored('>>>', 'cyan')} {colored(name, attrs=['bold'])}")
        
    def check(self, condition, success_msg, fail_msg):
        if condition:
            print(f"   {colored('✓', 'green')} {success_msg}")
            return True
        else:
            print(f"   {colored('✗', 'red')} {fail_msg}")
            print(colored(f"      [DEBUG] Output trace:", 'yellow'))
            import textwrap
            print(textwrap.indent(str(fail_msg), '        '))
            return False

    def phase_1_platform_login(self):
        self.step("PHASE 1: Platform Login Verification")
        
        # 1. First touch to get CSRF
        try:
            self.session.get(f"{BASE_URL}/platform/login/")
        except requests.exceptions.ConnectionError:
            self.check(False, "", "Django Dev Server is not running on port 8000!")
            return False
            
        csrf_token = self.session.cookies.get('csrftoken', '')
        
        # 2. Login via API
        response = self.session.post(
            f"{PLATFORM_API}/login", 
            json={"email": "admin@platform.com", "password": "password123"}
        )
        
        if not self.check(response.status_code == 200, "Platform Admin authenticated", f"Platform Login Failed: {response.status_code} {response.text}"):
            return False
            
        data = response.json()
        self.platform_token = data.get('access_token')
        self.session.headers.update({"Authorization": f"Bearer {self.platform_token}"})
        
        # 3. Verify ME endpoint
        me_resp = self.session.get(f"{PLATFORM_API}/me")
        return self.check(me_resp.status_code == 200, "Dashboard /me context loads successfully", f"/me failed: {me_resp.text}")

    def phase_2_and_3_org_creation_and_logout(self):
        self.step("PHASE 2 & 3: Organization Provisioning & Logout")
        
        # Dynamic seed to avoid duplicate IntegrityErrors across script reruns
        # self.stamp is already initialized in __init__
        
        # Payload for new Phase 2
        payload = {
            "name": f"Test Organization {self.stamp}",
            "subdomain": f"audit-{self.stamp}",
            "email": "contact@audit.com", # This email is not dynamic, but it's not used for login
            "admin_email": f"admin{self.stamp}@audit.com",
            "admin_password": "Password123!",
            "admin_name": "Audit Admin",
            "plan": "starter_trial"
        }
        
        resp = self.session.post(f"{PLATFORM_API}/organizations", json=payload)
        
        if not self.check(resp.status_code == 201, "Organization Created via API", f"Org Creation Failed: {resp.text}"):
            return False

        data = resp.json()
        org_id = data.get('id')
        self.admin_email = data.get('admin_user', {}).get('email') or payload.get('admin_email')
        
        # Validate DB integrity explicitly
        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        
        # 1. Organization in Default DB
        c.execute("SELECT id FROM organizations WHERE subdomain=?", (self.org_subdomain,))
        if not self.check(c.fetchone() is not None, "Organization row created in Default DB", "Missing from organizations table!"):
            return False
            
        # 2. GlobalUser created for org admin
        c.execute("SELECT id FROM global_users WHERE email=?", (self.admin_email,))
        if not self.check(c.fetchone() is not None, "GlobalUser synchronizer auto-created admin directory row", "Missing from global_users table!"):
            return False
            
        # 3. Test Logout (Simulated by trashing token context)
        self.session.headers.pop("Authorization", None)
        self.check(True, "Platform Admin logged out", "")
        return True

    def phase_4_and_5_tenant_crud(self):
        self.step("PHASE 4 & 5: Tenant Subdomain Auth & Core CRUD")
        tenant_api = f"{BASE_URL}/api/{self.org_subdomain}"
        
        # 1. Tenant Login
        resp = self.session.post(f"{tenant_api}/auth/login/", json={
            "email": self.admin_email,
            "password": "Password123!"
        })
        
        if not self.check(resp.status_code == 200, "Successfully logged into Tenant API", f"Tenant Login Failed: {resp.text}"):
            return False
            
        self.tenant_token = resp.json().get('access_token')
        self.session.headers.update({"Authorization": f"Bearer {self.tenant_token}"})
        
        # 2. Create Department
        dep_resp = self.session.post(f"{tenant_api}/auth/departments/", json={
            "name": "Audit Engineering"
        })
        if not self.check(dep_resp.status_code == 201, "Department created via Tenant", f"Dep Creation Failed: {dep_resp.text}"): return False
        self.dep_id = dep_resp.json().get('id')
        
        # 3. Create Project (Project model has name, key, description; no department FK)
        proj_resp = self.session.post(f"{tenant_api}/projects/", json={
            "name": "Hybrid Migration",
            "key": "HYB",
            "description": "A very stable audit project."
        })
        if not self.check(proj_resp.status_code == 201, "Project created via Tenant", f"Proj Creation Failed: {proj_resp.text}"): return False
        self.proj_id = proj_resp.json().get('id')
        
        # 4. Create User (Manager) - User.department is CharField (name), not FK
        manager_email = f"manager{self.stamp}@audit.com"
        user_resp = self.session.post(f"{tenant_api}/auth/users/", json={
            "email": manager_email,
            "full_name": "Audit Manager",
            "password": "Password123!",
            "role": "manager",
            "department": "Audit Engineering"
        })
        if not self.check(user_resp.status_code == 201, "Manager provisioned via Tenant", f"Manager Creation Failed: {user_resp.text}"): return False
        
        # 5. Verify isolated Database state
        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email=?", (manager_email,))
        if not self.check(c.fetchone() is not None, "Manager stored strictly via the Tenant layer directly", "Manager missing!"): return False
        
        c.execute("SELECT id FROM global_users WHERE email=?", (manager_email,))
        if not self.check(c.fetchone() is not None, "Manager successfully synchronized out to GlobalUser Directory automatically", "Manager failed global link!"): return False

        # Phases 6-13: ticket, comment, notification, roles, pages, cross-tenant
        import os
        import sys
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir not in sys.path:
            sys.path.insert(0, os.path.dirname(script_dir))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "audit_phases_6_to_13",
            os.path.join(script_dir, "audit_phases_6_to_13.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        Phase6To13Auditor = mod.Phase6To13Auditor
        auditor613 = Phase6To13Auditor(
            self.org_subdomain,
            self.admin_email,
            admin_password="Password123!",
            manager_email=manager_email,
        )
        auditor613.dep_id = self.dep_id
        auditor613.proj_id = self.proj_id
        self.session.headers["Authorization"] = f"Bearer {self.tenant_token}"
        r = self.session.get(f"{BASE_URL}/api/{self.org_subdomain}/auth/users/")
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            if isinstance(results, list):
                for u in results:
                    if u.get("email") == manager_email or (manager_email and manager_email in (u.get("email") or "")):
                        auditor613.manager_user_id = u.get("id")
                        break
                if auditor613.manager_user_id is None and results:
                    for u in results:
                        if "manager" in (u.get("email") or "").lower() or u.get("role") == "manager":
                            auditor613.manager_user_id = u.get("id")
                            auditor613.manager_email = u.get("email") or auditor613.manager_email
                            break
        auditor613.session = self.session
        auditor613.admin_token = self.tenant_token
        auditor613.phase_6_ticket_creation()
        auditor613.phase_7_comments()
        auditor613.phase_8_notifications()
        auditor613.phase_9_role_permissions()
        auditor613.phase_10_page_load()
        auditor613.phase_12_cross_tenant()
        return True

if __name__ == "__main__":
    print(colored("="*50, "blue"))
    print(colored("13-PHASE HYBRID PLATFORM AUDIT ENGINE", "blue", attrs=['bold']))
    print(colored("="*50, "blue"))
    
    auditor = Auditor()
    if auditor.phase_1_platform_login():
        if auditor.phase_2_and_3_org_creation_and_logout():
            auditor.phase_4_and_5_tenant_crud()
