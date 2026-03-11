#!/usr/bin/env python3
"""
Fix corrupted data from earlier failed migration and apply tenant isolation migrations.
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db.sqlite3')
DB_PATH = os.path.normpath(DB_PATH)

print(f"Database: {DB_PATH}")

# Step 1: Check for WAL journal and recover
wal_path = DB_PATH + '-wal'
shm_path = DB_PATH + '-shm'
if os.path.exists(wal_path):
    print(f"  WAL journal found ({os.path.getsize(wal_path)} bytes). Recovering...")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    print("  WAL checkpoint done.")
else:
    print("  No WAL journal (clean state).")

# Step 2: Fix corrupted organization_id = 0 
conn = sqlite3.connect(DB_PATH, timeout=10)
conn.execute("PRAGMA foreign_keys=OFF")

# Check current state
print("\n--- Data Check ---")
tables_with_org = ['departments', 'users', 'projects', 'tickets', 'tags', 'sla_policies',
                   'canned_responses', 'kb_categories', 'kb_articles', 'audit_logs']

for table in tables_with_org:
    try:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE organization_id = 0")
        count = cursor.fetchone()[0]
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if count > 0:
            print(f"  ⚠️  {table}: {count}/{total} rows have organization_id=0")
        else:
            print(f"  ✅ {table}: {total} rows, all have valid org IDs")
    except sqlite3.OperationalError as e:
        print(f"  ⓘ  {table}: {e}")

# Get the default org ID to fix any corrupted rows
cursor = conn.execute("SELECT id, name, subdomain FROM organizations ORDER BY id LIMIT 5")
orgs = cursor.fetchall()
print(f"\n  Organizations: {orgs}")

if orgs:
    default_org_id = orgs[0][0]
    print(f"\n  Using default org ID={default_org_id} to fix corrupted rows...")
    
    for table in tables_with_org:
        try:
            cursor = conn.execute(
                f"UPDATE {table} SET organization_id = ? WHERE organization_id = 0",
                (default_org_id,)
            )
            if cursor.rowcount > 0:
                print(f"    Fixed {cursor.rowcount} rows in {table}")
        except sqlite3.OperationalError:
            pass  # Table doesn't exist or no such column

conn.commit()
conn.close()

print("\n--- Data fix complete ---")
print("\nNow run: python manage.py migrate --settings=config.settings.dev")
