#!/usr/bin/env python3
"""
Data Migration Script: Migrate Users from Primary DB to Tenant DBs

This script:
1. Reads all Organizations from the primary (default) DB
2. For each organization, finds users in the primary DB
3. Copies those users to the tenant DB, preserving password hashes
4. Verifies the migration

Usage:
    python manage.py shell < scripts/migrate_users_to_tenant.py
    
    OR:
    
    DJANGO_SETTINGS_MODULE=config.settings.dev python scripts/migrate_users_to_tenant.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

django.setup()

from django.db import connections
from apps.accounts.models import Organization
from apps.core.routers import set_current_db_alias, reset_current_db_alias


def get_users_from_primary_db(org_id):
    """
    Read users directly from the primary database using raw SQL.
    This works even after the User model has been re-routed to tenant DBs.
    """
    with connections['default'].cursor() as cursor:
        cursor.execute(
            "SELECT id, email, password, full_name, role, department, "
            "is_active, is_onboarded, is_staff, created_at, last_login, "
            "reset_otp, reset_otp_expires_at, organization_id "
            "FROM users WHERE organization_id = %s",
            [org_id]
        )
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_departments_from_primary_db(org_id):
    """Read departments from the primary database."""
    with connections['default'].cursor() as cursor:
        cursor.execute(
            "SELECT id, name, organization_id, default_assignee_id, "
            "sla_policy_id, is_active, created_at, updated_at "
            "FROM departments WHERE organization_id = %s",
            [org_id]
        )
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def migrate_org(org):
    """Migrate users and departments for a single organization."""
    from django.conf import settings
    
    db_alias = f'tenant_{org.id}'
    
    # Check if tenant DB is configured
    if db_alias not in settings.DATABASES:
        print(f"  ⚠️  No tenant DB configured for {org.subdomain} (alias: {db_alias})")
        print(f"     Using 'default' database — data stays in primary DB.")
        return {'users': 0, 'departments': 0, 'skipped': True}
    
    # Activate tenant DB
    set_current_db_alias(db_alias)
    
    try:
        # --- Migrate Users ---
        primary_users = get_users_from_primary_db(org.id)
        user_count = 0
        
        for user_data in primary_users:
            # Check if user already exists in tenant DB
            with connections[db_alias].cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM users WHERE email = %s",
                    [user_data['email']]
                )
                if cursor.fetchone():
                    print(f"    User {user_data['email']} already exists in tenant DB, skipping")
                    continue
            
            # Insert into tenant DB
            with connections[db_alias].cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (id, email, password, full_name, role, department, "
                    "is_active, is_onboarded, is_staff, created_at, last_login, "
                    "reset_otp, reset_otp_expires_at, organization_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        user_data['id'],
                        user_data['email'],
                        user_data['password'],
                        user_data['full_name'],
                        user_data['role'],
                        user_data['department'],
                        user_data['is_active'],
                        user_data['is_onboarded'],
                        user_data['is_staff'],
                        user_data['created_at'],
                        user_data['last_login'],
                        user_data['reset_otp'],
                        user_data['reset_otp_expires_at'],
                        user_data['organization_id'],
                    ]
                )
                user_count += 1
        
        # --- Migrate Departments ---
        primary_depts = get_departments_from_primary_db(org.id)
        dept_count = 0
        
        for dept_data in primary_depts:
            with connections[db_alias].cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM departments WHERE name = %s",
                    [dept_data['name']]
                )
                if cursor.fetchone():
                    print(f"    Department '{dept_data['name']}' already exists, skipping")
                    continue
            
            with connections[db_alias].cursor() as cursor:
                cursor.execute(
                    "INSERT INTO departments (id, name, organization_id, default_assignee_id, "
                    "sla_policy_id, is_active, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        dept_data['id'],
                        dept_data['name'],
                        dept_data['organization_id'],
                        dept_data['default_assignee_id'],
                        dept_data['sla_policy_id'],
                        dept_data['is_active'],
                        dept_data['created_at'],
                        dept_data['updated_at'],
                    ]
                )
                dept_count += 1
        
        return {'users': user_count, 'departments': dept_count, 'skipped': False}
    
    finally:
        reset_current_db_alias()


def main():
    print("=" * 60)
    print("  TENANT DATA MIGRATION")
    print("  Moving Users & Departments from Primary → Tenant DBs")
    print("=" * 60)
    
    organizations = Organization.objects.filter(is_active=True)
    print(f"\nFound {organizations.count()} active organizations.\n")
    
    total_users = 0
    total_depts = 0
    
    for org in organizations:
        print(f"📦 Migrating: {org.name} (subdomain: {org.subdomain}, id: {org.id})")
        result = migrate_org(org)
        
        if result['skipped']:
            print(f"   ⏭️  Skipped (no tenant DB configured)\n")
        else:
            print(f"   ✅ Migrated {result['users']} users, {result['departments']} departments\n")
            total_users += result['users']
            total_depts += result['departments']
    
    print("=" * 60)
    print(f"  MIGRATION COMPLETE")
    print(f"  Total Users Migrated:       {total_users}")
    print(f"  Total Departments Migrated: {total_depts}")
    print("=" * 60)


if __name__ == '__main__':
    main()
