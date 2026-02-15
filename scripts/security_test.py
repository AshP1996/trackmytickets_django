
import os
import sys
import django
# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

import unittest
from django.conf import settings
from django.test import RequestFactory
from rest_framework.test import APIClient
from apps.accounts.models import User, Organization
from apps.tickets.models import Ticket, Project
from apps.core.models import ExternalDataSource
from apps.core.utils.encryption import encrypt_password, decrypt_password, get_encryption_key
from apps.core.connectors.sqlite_connector import SQLiteConnector
from apps.tickets.views import TicketViewSet

class SecurityTestCase(unittest.TestCase):
    def setUp(self):
        import time
        suffix = int(time.time())
        
        # Create Organizations
        self.org_a, _ = Organization.objects.get_or_create(
            subdomain=f'orga_{suffix}',
            defaults={'name': 'Org A', 'email': f'admin_a_{suffix}@orga.com'}
        )
        self.org_b, _ = Organization.objects.get_or_create(
            subdomain=f'orgb_{suffix}',
            defaults={'name': 'Org B', 'email': f'admin_b_{suffix}@orgb.com'}
        )

        # Create Users
        self.user_a, _ = User.objects.get_or_create(
            email=f'user_a_{suffix}@orga.com', 
            defaults={
                'organization': self.org_a, 
                'role': 'admin', 
                'is_active': True
            }
        )
        if _:
            self.user_a.set_password('password')
            self.user_a.save()

        self.user_b, _ = User.objects.get_or_create(
            email=f'user_b_{suffix}@orgb.com', 
            defaults={
                'organization': self.org_b, 
                'role': 'admin', 
                'is_active': True
            }
        )
        if _:
            self.user_b.set_password('password')
            self.user_b.save()

        # Create Project & Ticket in Org A
        self.project_a, _ = Project.objects.get_or_create(
            key=f'PROJA_{suffix}',
            organization=self.org_a,
            defaults={
                'name': 'Project A', 
                'lead_user': self.user_a
            }
        )
        self.ticket_a, _ = Ticket.objects.get_or_create(
            ticket_id=f'PROJA_{suffix}-1',
            organization=self.org_a,
            defaults={
                'subject': 'Ticket A',
                'description': 'Desc A',
                'project': self.project_a,
                'sender_email': 'sender@test.com',
                'status': 'open',
                'priority': 'medium'
            }
        )

    def test_encryption_consistency(self):
        """
        Verify that encryption keys are consistent and encryption/decryption works.
        """
        print("\n[Security] Testing Credential Encryption...")
        
        # Check if key is configured in settings
        key_setting = getattr(settings, 'DB_CREDENTIALS_ENCRYPTION_KEY', None)
        if not key_setting:
            print("WARNING: DB_CREDENTIALS_ENCRYPTION_KEY is NOT set in settings!")
        else:
            print(f"INFO: DB_CREDENTIALS_ENCRYPTION_KEY is set (Length: {len(key_setting)})")

        secret = "SuperSecretPassword123!"
        encrypted = encrypt_password(secret)
        decrypted = decrypt_password(encrypted)
        
        self.assertEqual(secret, decrypted, "Decrypted password does not match original!")
        
        # Verify key stability (simulate by calling get_encryption_key again)
        key1 = get_encryption_key()
        key2 = get_encryption_key()
        self.assertEqual(key1, key2, "Encryption key changed between calls! Persistence failure.")
        print("[PASS] Encryption mechanism is sound.")

    def test_idor_ticket_access(self):
        """
        Verify that User B cannot access Ticket A (IDOR).
        """
        print("\n[Security] Testing IDOR (Ticket Access)...")
        
        client = APIClient()
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user_b)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        # Try to retrieve Ticket A
        url = f'/api/v1/tickets/{self.ticket_a.ticket_id}/' 
        # Note: In a real request, the host/subdomain might route to the org.
        # But here we are testing the API View protection directly or via client assuming middleware handles scoping.
        # IF middleware relies on Host header for organization, we must spoof it.
        # However, the Token contains user info, but TenantMiddleware usually sets request.organization based on hostname.
        # Let's see TenantMiddleware.
        
        # We need to simulate the environment correctly.
        # TenantMiddleware resolves organization by subdomain.
        # So if we request with Org B's domain, we get Org B scope.
        # Then looking up Ticket A (which is Org A) should fail 404.
        
        response = client.get(
            url, 
            HTTP_HOST='orgb.trackmytickets.local' # Spoof Org B domain
        )
        
        if response.status_code == 404:
            print("[PASS] User B (Org B) cannot see Ticket A.")
        else:
            print(f"[FAIL] User B accessed Ticket A! Status: {response.status_code}")
            # Identify why
            self.fail(f"IDOR Vulnerability: User B accessed Ticket A. Response: {response.status_code}")

    def test_idor_user_assignment(self):
        """
        Verify User B cannot be assigned to Ticket A.
        """
        print("\n[Security] Testing IDOR (User Assignment)...")
        
        # Login as User A (Org A Admin)
        client = APIClient()
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user_a)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Try to assign User B (from Org B) to Ticket A
        url = f'/api/v1/tickets/{self.ticket_a.ticket_id}/assign/'
        data = {'user_id': self.user_b.id}
        
        response = client.post(
            url, 
            data, 
            format='json', 
            HTTP_HOST='orga.trackmytickets.local'
        )
        
        if response.status_code == 404:
            print("[PASS] Cannot assign User B to Ticket A (User not found in Org context).")
        elif response.status_code == 400 and 'User not found' in str(response.data):
             print("[PASS] User B not found in Org A context.")
        elif response.status_code == 200:
            print(f"[FAIL] Successfully assigned User B (Org B) to Ticket A (Org A)!")
            self.fail("IDOR Vulnerability: Cross-tenant user assignment allowed.")
        else:
             # Could be User not found error which is also 404 or 400
             if 'User not found' in str(response.data):
                 print("[PASS] User B not found in Org A context.")
             else:
                 print(f"[INFO] Unexpected response: {response.status_code} {response.data}")

    def test_sqlite_connector_sqli(self):
        """
        Test SQLiteConnector for SQL Injection in get_schema.
        """
        print("\n[Security] Testing SQLite Connector SQL Injection...")
        
        # Create a dummy sqlite db
        db_path = 'test_security_sqli.sqlite3'
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE valid_table (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()
        conn.close()
        
        connector = SQLiteConnector({'database': db_path})
        
        # 1. Valid case
        schema = connector.get_schema('valid_table')
        self.assertTrue(len(schema) > 0, "Failed to get schema for valid table")
        
        # 2. Injection case
        # Try to inject a second command or cause syntax error
        # "valid_table); DROP TABLE valid_table; --"
        # PRAGMA table_info(valid_table); DROP TABLE valid_table; --)
        
        malicious_table_name = "valid_table); DELETE FROM valid_table; --"
        
        try:
            # We expect this to either fail gracefully or NOT execute the delete
            connector.get_schema(malicious_table_name)
        except Exception as e:
            print(f"[INFO] Injection attempt raised exception: {e}")
            
        # Verify table still exists and has data (if we added any)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Inserting data if not exists to verify delete
        cursor.execute("INSERT INTO valid_table (name) VALUES ('Test')")
        conn.commit()
        
        # Try injection again if first one didn't error out hard
        try:
             connector.get_schema("valid_table); DELETE FROM valid_table; --")
        except:
            pass
            
        cursor.execute("SELECT count(*) FROM valid_table")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            print("[FAIL] SQL Injection successful! Table data deleted.")
            self.fail("SQL Injection Vulnerability in SQLiteConnector.get_schema")
        else:
            print("[PASS] SQL Injection unsuccessful (Data likely intact).")

        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == '__main__':
    unittest.main()
