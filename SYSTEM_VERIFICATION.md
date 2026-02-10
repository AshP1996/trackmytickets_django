# System Verification & Documentation

This document outlines the system verification process, available test data, and key URLs for the Ticket System.

## Test Data Generation

A script has been created to populate the database with comprehensive test data.

**Script Path**: `scripts/add_test_data.py`

**Usage**:
```bash
python scripts/add_test_data.py
```

### Generated Data
- **Organization**: Demo Corp (Subdomain: `demo`)
- **Departments**: Support, IT, Sales
- **Project**: Support Project (Key: `SUP`)

### Test Credentials

| Role | Email | Password | Access URL |
|------|-------|----------|------------|
| **Platform Admin** | `admin@platform.com` | `adminpassword` | `/platform/login` |
| **Company Admin** | `admin@democorp.com` | `password123` | `/demo/login` |
| **Head (Manager)** | `head@democorp.com` | `password123` | `/demo/login` |
| **Agent** | `agent@democorp.com` | `password123` | `/demo/login` |
| **User (Customer)** | `user@democorp.com` | `password123` | `/demo/login` |

## Verification Check

A verification script checks the accessibility of key pages for different user roles.

**Script Path**: `scripts/verify_system.py`

**Usage**:
```bash
python scripts/verify_system.py
```

**Results**:
- Platform Admin Dashboard: ✓ Accessible
- Company Admin Dashboard & Settings: ✓ Accessible
- Agent Ticket List & Detail: ✓ Accessible
- Customer Ticket Creation: ✓ Accessible

## Key URLs

### Platform
- Login: `/platform/login`
- Dashboard: `/platform/dashboard`

### Organization (Demo Corp)
- Login: `/demo/login`
- Dashboard: `/demo/dashboard`
- Tickets: `/demo/tickets`
- Create Ticket: `/demo/tickets/create`
- Admin Users: `/demo/admin/users`
- Admin Departments: `/demo/admin/departments`

## Troubleshooting

If pages fail to load:
1. Ensure the database is migrated: `python manage.py migrate`
2. Ensure the server is running: `python manage.py runserver`
3. Check the `verify_system.py` output for specific error codes (e.g., 403 Forbidden, 500 Internal Server Error).
