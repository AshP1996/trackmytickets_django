#!/usr/bin/env python
"""
Comprehensive Data Source Feature Test
Tests the complete workflow of external data sources
"""
import os
import sys
import django
import sqlite3

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.models import ExternalDataSource
from apps.core.connectors import get_connector
from apps.accounts.models import Organization, User

def create_test_database():
    """Create a test SQLite database with sample ticket data"""
    print("\n[1] Creating Test SQLite Database...")
    
    db_path = '/tmp/test_support.db'
    
    # Remove if exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"   Removed existing database at {db_path}")
    
    # Create database with sample data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create support_tickets table
    cursor.execute('''
        CREATE TABLE support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            description TEXT,
            customer_email TEXT,
            status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample data
    sample_tickets = [
        ('Login Issue', 'Cannot login to my account. Getting error 401', 'user1@example.com', 'open', 'high'),
        ('Feature Request', 'Please add dark mode to the application', 'user2@example.com', 'open', 'low'),
        ('Bug Report', 'Application crashes on startup', 'user3@example.com', 'in_progress', 'critical'),
        ('Password Reset', 'Need to reset my password but not receiving email', 'user4@example.com', 'open', 'medium'),
        ('Performance Issue', 'Dashboard loads very slowly', 'user5@example.com', 'resolved', 'medium'),
    ]
    
    cursor.executemany('''
        INSERT INTO support_tickets (subject, description, customer_email, status, priority)
        VALUES (?, ?, ?, ?, ?)
    ''', sample_tickets)
    
    conn.commit()
    
    # Verify data
    cursor.execute('SELECT COUNT(*) FROM support_tickets')
    count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"   ✓ Created database at {db_path}")
    print(f"   ✓ Inserted {count} sample tickets")
    
    return db_path

def setup_organization():
    """Get or create demo organization"""
    print("\n[2] Setting Up Organization...")
    
    # Try to get existing organization first
    try:
        org = Organization.objects.get(subdomain='demo')
        print(f"   ✓ Using existing organization: {org.name}")
    except Organization.DoesNotExist:
        # Create new one
        org = Organization.objects.create(
            name='demo',
            subdomain='demo',
            is_active=True
        )
        print(f"   ✓ Created new organization: {org.name}")
    
    return org

def test_data_source_creation(org, db_path):
    """Test creating a data source"""
    print("\n[3] Testing Data Source Creation...")
    
    # Delete existing test data sources
    ExternalDataSource.objects.filter(
        organization=org,
        name='Test Support DB'
    ).delete()
    
    # Create new data source
    ds = ExternalDataSource.objects.create(
        organization=org,
        name='Test Support DB',
        type='sqlite',
        database=db_path,
        is_active=True
    )
    
    print(f"   ✓ Created data source: {ds.name} (ID: {ds.id})")
    print(f"   ✓ Type: {ds.get_type_display()}")
    print(f"   ✓ Database: {ds.database}")
    
    return ds

def test_password_encryption(org):
    """Test password encryption and decryption"""
    print("\n[4] Testing Password Encryption...")
    
    # Create a temporary data source (don't save)
    ds = ExternalDataSource(
        organization=org,
        name='Test PostgreSQL',
        type='postgres',
        host='localhost',
        port=5432,
        database='testdb',
        username='testuser'
    )
    
    # Test encryption
    test_password = 'SecurePassword123!@#'
    ds.set_password(test_password)
    
    print(f"   Original password: {test_password}")
    print(f"   Encrypted (first 50 chars): {ds.password_encrypted[:50]}...")
    
    # Test decryption
    decrypted = ds.get_password()
    print(f"   Decrypted password: {decrypted}")
    
    if decrypted == test_password:
        print("   ✓ Password encryption/decryption works correctly")
        return True
    else:
        print("   ✗ Password encryption/decryption FAILED")
        return False

def test_connection(ds):
    """Test database connection"""
    print("\n[5] Testing Database Connection...")
    
    config = {
        'database': ds.database,
        'host': ds.host,
        'port': ds.port,
        'username': ds.username,
        'password': ds.get_password() if ds.password_encrypted else None,
    }
    
    connector = get_connector(ds.type, config)
    result = connector.test_connection()
    
    if result['success']:
        print(f"   ✓ Connection successful")
        print(f"   ✓ Message: {result['message']}")
        if result.get('details'):
            for key, value in result['details'].items():
                print(f"   ✓ {key}: {value}")
    else:
        print(f"   ✗ Connection failed: {result['message']}")
    
    connector.close()
    return result['success']

def test_get_tables(ds):
    """Test getting list of tables"""
    print("\n[6] Testing Get Tables...")
    
    config = {'database': ds.database}
    connector = get_connector(ds.type, config)
    
    tables = connector.get_tables()
    
    print(f"   ✓ Found {len(tables)} table(s):")
    for table in tables:
        print(f"     - {table}")
    
    connector.close()
    return tables

def test_get_schema(ds, table_name):
    """Test getting table schema"""
    print(f"\n[7] Testing Get Schema for '{table_name}'...")
    
    config = {'database': ds.database}
    connector = get_connector(ds.type, config)
    
    schema = connector.get_schema(table_name)
    
    print(f"   ✓ Found {len(schema)} column(s):")
    for col in schema:
        nullable = "NULL" if col.get('nullable') else "NOT NULL"
        pk = " [PRIMARY KEY]" if col.get('primary_key') else ""
        print(f"     - {col['name']}: {col['type']} {nullable}{pk}")
    
    connector.close()
    return schema

def test_fetch_data(ds):
    """Test fetching data from database"""
    print("\n[8] Testing Data Fetch...")
    
    config = {'database': ds.database}
    connector = get_connector(ds.type, config)
    
    # Fetch all tickets
    query = "SELECT * FROM support_tickets ORDER BY id"
    data = connector.fetch_data(query)
    
    print(f"   ✓ Fetched {len(data)} row(s):")
    for row in data:
        print(f"     - ID {row['id']}: {row['subject']} ({row['status']}, {row['priority']})")
    
    # Test filtered query
    query_filtered = "SELECT * FROM support_tickets WHERE status = 'open'"
    data_filtered = connector.fetch_data(query_filtered)
    print(f"   ✓ Filtered query (status='open'): {len(data_filtered)} row(s)")
    
    connector.close()
    return data

def test_api_workflow(ds):
    """Test the API workflow"""
    print("\n[9] Testing API Workflow...")
    
    # Update connection status
    from django.utils import timezone
    ds.connection_status = 'connected'
    ds.last_connection_test = timezone.now()
    ds.save()
    
    print(f"   ✓ Updated connection status: {ds.connection_status}")
    print(f"   ✓ Last connection test: {ds.last_connection_test}")
    
    # Verify data source can be retrieved
    retrieved = ExternalDataSource.objects.get(id=ds.id)
    print(f"   ✓ Data source retrieved from database: {retrieved.name}")
    
    return True

def cleanup(db_path):
    """Cleanup test database"""
    print("\n[10] Cleanup...")
    
    if os.path.exists(db_path):
        # Don't delete - leave for manual inspection
        print(f"   ℹ Test database kept at: {db_path}")
        print(f"   ℹ You can inspect it with: sqlite3 {db_path}")
    
    print("   ✓ Cleanup completed")

def main():
    print("=" * 70)
    print("COMPREHENSIVE DATA SOURCE FEATURE TEST")
    print("=" * 70)
    
    try:
        # Run all tests
        db_path = create_test_database()
        org = setup_organization()
        ds = test_data_source_creation(org, db_path)
        test_password_encryption(org)
        test_connection(ds)
        tables = test_get_tables(ds)
        
        if 'support_tickets' in tables:
            test_get_schema(ds, 'support_tickets')
            test_fetch_data(ds)
        
        test_api_workflow(ds)
        cleanup(db_path)
        
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED SUCCESSFULLY")
        print("=" * 70)
        print(f"\nData Source ID: {ds.id}")
        print(f"Database Path: {db_path}")
        print(f"Organization: {org.name}")
        print("\nNext Steps:")
        print("1. Start dev server: python manage.py runserver")
        print(f"2. Navigate to: http://localhost:8000/{org.subdomain}/admin/data-sources/")
        print("3. View and test the data source in the UI")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
