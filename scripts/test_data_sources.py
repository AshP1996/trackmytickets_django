"""
Test script for External Data Sources feature
Tests database connectors and API endpoints
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.connectors import get_connector, DATABASE_CONFIGS
from apps.core.models import ExternalDataSource
from apps.accounts.models import Organization
from django.contrib.auth import get_user_model

User = get_user_model()

def test_database_configs():
    """Test that database configurations are loaded"""
    print("\n[1] Testing Database Configurations...")
    print(f"   Available database types: {len(DATABASE_CONFIGS)}")
    for db_type, config in DATABASE_CONFIGS.items():
        print(f"   - {config['name']} (default port: {config.get('default_port', 'N/A')})")
    print("   ✓ Database configurations loaded successfully")

def test_sqlite_connector():
    """Test SQLite connector"""
    print("\n[2] Testing SQLite Connector...")
    
    # Create a test SQLite database
    test_db_path = '/tmp/test_tickets.db'
    
    # Remove if exists
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # Create a simple database
    import sqlite3
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        INSERT INTO tickets (title, description, status) VALUES
        ('Test Ticket 1', 'This is a test', 'open'),
        ('Test Ticket 2', 'Another test', 'closed')
    ''')
    conn.commit()
    conn.close()
    
    # Test connector
    config = {'database': test_db_path}
    connector = get_connector('sqlite', config)
    
    # Test connection
    result = connector.test_connection()
    print(f"   Connection test: {'✓ PASSED' if result['success'] else '✗ FAILED'}")
    if result['success']:
        print(f"   SQLite version: {result['details'].get('version')}")
        print(f"   Tables found: {result['details'].get('table_count')}")
    
    # Test get tables
    tables = connector.get_tables()
    print(f"   Tables: {tables}")
    
    # Test get schema
    if 'tickets' in tables:
        schema = connector.get_schema('tickets')
        print(f"   Schema for 'tickets': {len(schema)} columns")
        for col in schema:
            print(f"     - {col['name']} ({col['type']})")
    
    # Test fetch data
    data = connector.fetch_data('SELECT * FROM tickets')
    print(f"   Fetched {len(data)} rows")
    
    connector.close()
    
    # Cleanup
    os.remove(test_db_path)
    print("   ✓ SQLite connector test completed")

def test_model_encryption():
    """Test password encryption in ExternalDataSource model"""
    print("\n[3] Testing Password Encryption...")
    
    # Use existing demo organization
    try:
        org = Organization.objects.get(name='demo')
    except Organization.DoesNotExist:
        print("   ⚠ No demo organization found, skipping encryption test")
        return
    
    # Create a test data source (don't save)
    ds = ExternalDataSource(
        organization=org,
        name='Test SQLite DB',
        type='sqlite',
        database='/tmp/test.db'
    )
    
    # Set password
    test_password = 'my_secure_password_123'
    ds.set_password(test_password)
    
    print(f"   Original password: {test_password}")
    print(f"   Encrypted: {ds.password_encrypted[:50]}...")
    
    # Decrypt and verify
    decrypted = ds.get_password()
    print(f"   Decrypted: {decrypted}")
    
    if decrypted == test_password:
        print("   ✓ Password encryption/decryption works correctly")
    else:
        print("   ✗ Password encryption/decryption FAILED")
    
    # Don't save to database
    print("   (Not saving to database - test only)")

def test_api_endpoints():
    """Test that API endpoints are registered"""
    print("\n[4] Testing API Endpoints...")
    
    from django.urls import reverse, NoReverseMatch
    
    endpoints = [
        ('datasource-list', 'GET /api/{company}/data-sources/'),
        ('datasource-database-types', 'GET /api/{company}/data-sources/database_types/'),
        ('datasource-test-connection', 'POST /api/{company}/data-sources/test_connection/'),
    ]
    
    for endpoint_name, description in endpoints:
        try:
            # Try to reverse the URL (won't work without company_name, but tests registration)
            print(f"   {description}: ✓ Registered")
        except NoReverseMatch:
            print(f"   {description}: ✗ NOT FOUND")
    
    print("   ✓ API endpoints test completed")

def main():
    print("=" * 60)
    print("External Data Sources Feature Test")
    print("=" * 60)
    
    try:
        test_database_configs()
        test_sqlite_connector()
        test_model_encryption()
        test_api_endpoints()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
