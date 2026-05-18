# TrackMyTickets — Enterprise Technical Documentation

> **Version**: 1.0 | **Framework**: Django 5.0.3 | **Python**: 3.11 | **Architecture**: Multi-Tenant SaaS with BYODB

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Multi-Tenancy & BYODB](#3-multi-tenancy--byodb)
4. [Data Models](#4-data-models)
5. [Authentication & Authorization](#5-authentication--authorization)
6. [API Reference](#6-api-reference)
7. [URL Routing](#7-url-routing)
8. [Notification System](#8-notification-system)
9. [Email Service](#9-email-service)
10. [Security](#10-security)
11. [Configuration](#11-configuration)
12. [Deployment](#12-deployment)

---

## 1. System Overview

TrackMyTickets is a **multi-tenant ticket management SaaS platform** built with Django. It supports:

- **Multi-organization isolation** — each company gets its own data silo
- **BYODB (Bring Your Own Database)** — enterprise clients can use their own database server
- **Role-based access control** — 5 roles (admin, manager, department_head, agent, customer)
- **Platform administration** — super-admin panel for managing all organizations
- **Real-time notifications** — in-app + email notifications for ticket lifecycle events
- **Knowledge Base** — self-service article system per organization
- **SLA Management** — configurable SLA policies with breach tracking
- **Audit Logging** — full trail of all user actions
- **External Data Sources** — connect to PostgreSQL, MySQL, SQLite, MongoDB, etc.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.0.3, Django REST Framework |
| Auth | JWT (SimpleJWT) with org-scoped claims |
| Database | SQLite (dev) / PostgreSQL (prod), multi-DB routing |
| Frontend | Django Templates + Vanilla JS (SPA-like) |
| Email | Django SMTP with HTML templates |
| Encryption | Fernet (cryptography library) |
| SEO | robots.txt, sitemap.xml, meta tags |

---

## 2. Architecture

### Project Structure

```
ticket_system_django/
├── config/
│   ├── settings/
│   │   ├── base.py          # Core settings, middleware, DB router
│   │   └── dev.py           # Development overrides
│   ├── urls.py               # Root URL configuration
│   └── wsgi.py
├── apps/
│   ├── accounts/             # Users, Orgs, Auth, Platform Admin
│   │   ├── models.py         # User, Organization, PlatformAdmin, GlobalUser
│   │   ├── views.py          # Login, Register, User CRUD
│   │   ├── platform_views.py # Platform admin endpoints
│   │   ├── authentication.py # Custom JWT authentication
│   │   ├── services.py       # UserProvisionService (cross-DB sync)
│   │   ├── serializers.py    # DRF serializers
│   │   ├── urls.py           # Tenant API routes (/api/{org}/auth/)
│   │   ├── platform_urls.py  # Platform API routes (/api/platform/)
│   │   └── web_urls.py       # HTML page routes
│   ├── tickets/              # Tickets, Projects, KB, Audit
│   │   ├── models.py         # Ticket, Project, Tag, SLA, KB, AuditLog
│   │   ├── views.py          # TicketViewSet, ProjectViewSet, KB, Stats
│   │   ├── serializers.py    # DRF serializers
│   │   └── urls.py           # /api/{org}/tickets/, projects/, etc.
│   ├── comments/             # Ticket comments
│   │   └── models.py         # Comment model
│   ├── notifications/        # In-app + email notifications
│   │   ├── models.py         # Notification model
│   │   ├── signals.py        # Auto-create notifications on ticket events
│   │   └── email_service.py  # Templated HTML email sending
│   └── core/                 # Infra: routing, middleware, connectors
│       ├── routers.py        # TenantDatabaseRouter (ContextVar-based)
│       ├── middleware/
│       │   ├── tenant.py     # TenantMiddleware (org resolution + BYODB)
│       │   └── correlation.py# Request correlation ID
│       ├── permissions.py    # RBAC permission classes
│       ├── models.py         # Feedback, Enquiry, ExternalDataSource
│       ├── views.py          # Data source CRUD, dashboard analytics
│       ├── connectors/       # DB connector plugins
│       │   ├── postgres_connector.py
│       │   ├── sqlite_connector.py
│       │   └── mysql_connector.py
│       └── web_views.py      # Template rendering with context injection
└── templates/                # 40+ HTML templates
    ├── login.html, dashboard.html, landing.html
    ├── admin/                # Org admin pages
    ├── platform/             # Platform admin pages
    ├── tickets/              # Ticket CRUD pages
    ├── emails/               # 11 HTML email templates
    └── knowledge_base/       # KB pages
```

### Request Lifecycle

```
Client Request
    │
    ▼
┌─────────────────────────┐
│  CorrelationIDMiddleware │  ← Assigns unique request ID for logging
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│    TenantMiddleware      │  ← Extracts {company_name} from URL
│  ┌──────────────────┐   │     Resolves Organization from DB
│  │ Slug validation   │   │     Checks for BYODB external data source
│  │ Org lookup        │   │     Registers tenant DB in settings.DATABASES
│  │ BYODB registration│   │     Sets ContextVar db alias
│  │ ContextVar set    │   │
│  └──────────────────┘   │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│  JWT Authentication      │  ← PlatformJWTAuthentication
│  (PlatformAdmin or User) │     Resolves user from token claims
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│  Permission Check        │  ← IsOrgMember validates JWT org_subdomain
│  (RBAC)                  │     Role-based: IsOrgAdmin, IsOrgAdminOrManager
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│  View / ViewSet          │  ← Business logic
│  (DRF or TemplateView)   │     All DB queries routed via TenantDatabaseRouter
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│  TenantDatabaseRouter    │  ← ContextVar lookup → tenant DB alias
│  db_for_read/write()     │     Platform models → always 'default'
└─────────────────────────┘
```

---

## 3. Multi-Tenancy & BYODB

### How Multi-Tenancy Works

The system uses **path-based tenant resolution** (not subdomain-based):

```
/api/{company_name}/tickets/    → Tenant API
/{company_name}/dashboard       → Tenant Web Page
/api/platform/                  → Platform Admin API
```

**TenantMiddleware** (`apps/core/middleware/tenant.py`):
1. Extracts `company_name` from URL kwargs
2. Validates slug format (regex: `^[a-z0-9][a-z0-9\-]{0,61}[a-z0-9]$`)
3. Looks up `Organization` by subdomain
4. Checks if org has an `ExternalDataSource` with `is_active=True` and `connection_status='connected'`
5. If BYODB exists → dynamically registers the external DB in `settings.DATABASES` under alias `tenant_{org_id}`
6. Sets `ContextVar` to the tenant DB alias via `set_current_db_alias()`
7. Attaches `request.organization` for downstream views

**TenantDatabaseRouter** (`apps/core/routers.py`):

| Model Category | Database | Examples |
|---------------|----------|----------|
| **Platform models** | Always `default` | Organization, PlatformAdmin, GlobalUser, ExternalDataSource, AuditLog |
| **Tenant models** | ContextVar alias | User, Ticket, Project, Comment, Notification, Department |
| **Django built-ins** | Always `default` | auth, sessions, contenttypes, admin |

### BYODB Flow

```
Org Admin → Admin Panel → Data Sources → Add PostgreSQL
    │
    ▼
ExternalDataSource.set_password(raw)  ← Fernet encryption
    │
    ▼
Test Connection → PostgreSQLConnector.test_connection()
    │
    ▼
Mark connection_status = 'connected'
    │
    ▼
Next request to /{org}/... :
    TenantMiddleware detects active data source
    → Registers DB: settings.DATABASES['tenant_{org_id}'] = {...}
    → set_current_db_alias('tenant_{org_id}')
    → All ORM queries route to tenant DB
```

**Thread Safety**: `settings.DATABASES` writes are protected by `threading.Lock`. The ContextVar is async-safe.

### Hybrid User Architecture

```
┌─────────────────────────────────────────┐
│           DEFAULT DATABASE              │
│                                         │
│  Organization ─── GlobalUser (UUID PK)  │
│       │              │                  │
│       │         email + org + tenant_id │
│       │                                 │
│  PlatformAdmin    OrganizationSecret    │
└─────────────────────────────────────────┘
            │ (cross-DB sync via UserProvisionService)
            ▼
┌─────────────────────────────────────────┐
│        TENANT DATABASE (per org)        │
│                                         │
│  User (Integer PK) ── Department        │
│    │                                    │
│    ├── Ticket ── Comment                │
│    ├── Project ── Workflow              │
│    ├── Notification                     │
│    └── TicketHistory                    │
└─────────────────────────────────────────┘
```

**UserProvisionService** (`apps/accounts/services.py`):
- `create_user()`: Atomically creates User in tenant DB + GlobalUser in default DB
- `sync_global_user()`: Self-healing — auto-creates GlobalUser if missing during login

---

## 4. Data Models

### accounts app

| Model | DB | Description |
|-------|-----|------------|
| `PlatformAdmin` | default | Super-admin users, JWT auth via `is_platform_admin` claim |
| `Organization` | default | Tenant definition: name, subdomain, plan, limits (JSON) |
| `GlobalUser` | default | Cross-tenant user directory (UUID PK, email+org unique) |
| `User` | tenant | Operational user: email, role, department, organization_id |
| `Department` | tenant | Org departments with default assignee and SLA policy |
| `UserRole` | tenant | Scoped roles (org/dept/project level) |
| `OrganizationSecret` | default | Encrypted key-value store (email creds, API keys) |

### tickets app

| Model | DB | Description |
|-------|-----|------------|
| `Project` | tenant | Container for tickets, unique key per org (e.g., SUP, ENG) |
| `Ticket` | tenant | Core entity: subject, status, priority, SLA fields, merge tracking |
| `TicketHistory` | tenant | Changelog: action, old_value, new_value per field change |
| `TicketWatcher` | tenant | Subscribe users to ticket updates |
| `Attachment` | tenant | File metadata (filename, filepath, MIME type, size) |
| `Tag` | tenant | Labels for tickets (name + color, unique per org) |
| `SLAPolicy` | tenant | Per-priority SLA targets (response/resolution/escalation hours) |
| `Workflow` | tenant | Custom states per project (JSON) |
| `CannedResponse` | tenant | Quick-reply templates with usage tracking |
| `KBCategory` | tenant | Knowledge base categories (hierarchical) |
| `KBArticle` | tenant | KB articles: draft/published/archived, view counts |
| `AuditLog` | default | System audit trail: user, action, resource, IP, user-agent |

### Ticket ID Generation

Atomic sequence using `F()` expression:
```python
Project.objects.filter(id=project_id).update(ticket_sequence=F('ticket_sequence') + 1)
# Result: "SUP-1", "SUP-2", etc.
```

### Ticket Lifecycle

```
open → in_progress → waiting → resolved → closed
                  ↗                ↘
            (reassign)        (reopen → open)
```

---

## 5. Authentication & Authorization

### JWT Authentication

**PlatformJWTAuthentication** (`apps/accounts/authentication.py`):

```python
# Token claims for Platform Admin:
{ "user_id": 1, "is_platform_admin": true }

# Token claims for Tenant User:
{ "user_id": 2, "org_id": 6, "org_subdomain": "demo", "global_user_id": "uuid..." }
```

- Platform admin tokens contain `is_platform_admin=true` → resolves `PlatformAdmin` model
- Tenant tokens contain `org_subdomain` → validated by `IsOrgMember` permission to prevent token replay

### Role Hierarchy

| Role | Scope | Capabilities |
|------|-------|-------------|
| `platform_admin` | Global | Manage all orgs, view stats, manage enquiries |
| `admin` | Organization | Full org access, user CRUD, settings, data sources |
| `manager` | Organization | Manage projects, view reports, manage team |
| `department_head` | Department | Manage department tickets, assign agents |
| `agent` | Assigned | View/handle assigned tickets, comment |
| `customer` | Own tickets | Create tickets, view own tickets, comment |

### Permission Classes

| Class | Logic |
|-------|-------|
| `IsPlatformAdmin` | `isinstance(request.user, PlatformAdmin)` |
| `IsOrgAdmin` | `request.user.role == 'admin'` |
| `IsOrgAdminOrManager` | `role in ('admin', 'manager')` |
| `IsOrgAdminOrDepartmentHead` | `role in ('admin', 'department_head')` |
| `IsOrgMember` | Validates JWT `org_subdomain` matches URL org |
| `IsAdminOrReadOnly` | Admin = full access, others = GET only |

### Token Replay Prevention

`IsOrgMember` extracts the `org_subdomain` claim from the JWT and compares it against the URL-resolved organization. A token minted for org `demo` CANNOT be used against org `techflow`.

---

## 6. API Reference

### Platform APIs (`/api/platform/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/platform/login` | None | Platform admin login → JWT |
| GET | `/api/platform/me` | PlatformAdmin | Current admin profile |
| GET | `/api/platform/stats` | PlatformAdmin | Platform-wide statistics |
| GET | `/api/platform/organizations` | PlatformAdmin | List all orgs (paginated) |
| POST | `/api/platform/organizations` | PlatformAdmin | Create new organization + admin user |
| GET | `/api/platform/organizations/{id}` | PlatformAdmin | Org detail |
| PUT | `/api/platform/organizations/{id}` | PlatformAdmin | Update org |
| POST | `/api/platform/organizations/{id}/suspend` | PlatformAdmin | Suspend/activate org |
| GET | `/api/platform/enquiries` | PlatformAdmin | Landing page contact form submissions |
| POST | `/api/platform/register` | Rate-limited | Public org self-registration |
| POST | `/api/platform/forgot-password` | None | OTP-based password reset |
| POST | `/api/platform/reset-password` | None | Verify OTP + set new password |

### Tenant Auth APIs (`/api/{org}/auth/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/login/` | None | Tenant user login → JWT |
| POST | `/auth/register/` | Admin | Create new user in org |
| GET | `/auth/me/` | User | Current user profile |
| PUT | `/auth/me/` | User | Update own profile |
| POST | `/auth/change-password/` | User | Change own password |
| GET | `/auth/users/` | Admin | List org users |
| GET | `/auth/users/{id}/` | Admin | User detail |
| PUT | `/auth/users/{id}/` | Admin | Update user |
| DELETE | `/auth/users/{id}/` | Admin | Deactivate user |
| GET | `/auth/departments/` | User | List departments |
| POST | `/auth/departments/` | Admin | Create department |
| POST | `/auth/forgot-password/` | None | OTP password reset |
| POST | `/auth/reset-password/` | None | Verify OTP + reset |

### Ticket APIs (`/api/{org}/tickets/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/tickets/` | User | List tickets (filtered, paginated) |
| POST | `/tickets/` | User | Create ticket (with attachments) |
| GET | `/tickets/{id}/` | User | Ticket detail |
| PUT | `/tickets/{id}/` | User | Update ticket |
| DELETE | `/tickets/{id}/` | Admin | Delete ticket |
| GET | `/tickets/stats/` | User | Ticket statistics |
| GET | `/tickets/export/` | Admin | CSV export |
| POST | `/tickets/{id}/merge/` | Admin | Merge tickets |
| POST | `/tickets/{id}/watch/` | User | Watch/unwatch ticket |
| GET | `/tickets/{id}/comments/` | User | List comments |
| POST | `/tickets/{id}/comments/` | User | Add comment |
| GET | `/tickets/head-stats/` | DeptHead | Department head dashboard |

### Project APIs (`/api/{org}/projects/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/projects/` | User | List projects (with ticket counts) |
| POST | `/projects/` | Admin/Manager | Create project |
| GET | `/projects/{id}/` | User | Project detail |
| PUT | `/projects/{id}/` | Admin/Manager | Update project |
| GET | `/projects/{id}/analytics/` | User | Project analytics |

### Other APIs

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/data-sources/` | User | List external data sources |
| POST | `/data-sources/` | Admin | Add data source |
| POST | `/data-sources/test_connection/` | Admin | Test DB connection |
| GET | `/data-sources/{id}/tables/` | Admin | List tables |
| GET | `/data-sources/{id}/schema/` | Admin | Get table schema |
| GET | `/notifications/` | User | List notifications |
| POST | `/notifications/{id}/read/` | User | Mark as read |
| POST | `/notifications/read-all/` | User | Mark all as read |
| POST | `/feedback/` | User | Submit feedback |
| GET | `/canned-responses/` | User | List canned responses |
| GET | `/kb/articles/` | User | Knowledge base articles |
| GET | `/admin/dashboard/` | User | Admin dashboard analytics |

---

## 7. URL Routing

### Route Resolution Order

```python
# config/urls.py
urlpatterns = [
    path('health/', health_check),
    path('robots.txt', robots_txt),
    path('sitemap.xml', sitemap_xml),
    path('admin/', admin.site.urls),

    # Tenant API routes
    path('api/<str:company_name>/auth/', include('apps.accounts.urls')),
    path('api/<str:company_name>/',      include('apps.tickets.urls')),
    path('api/<str:company_name>/',      include('apps.notifications.urls')),
    path('api/<str:company_name>/',      include('apps.core.urls')),

    # Platform API
    path('api/platform/', include('apps.accounts.platform_urls')),

    # Web (HTML) routes
    path('', include('apps.core.web_urls')),           # Landing + platform pages
    path('<str:company_name>/', include('apps.accounts.web_urls')),  # Org pages
    path('<str:company_name>/', include('apps.tickets.web_urls')),
]
```

### Web Pages

| URL | Template | Description |
|-----|----------|-------------|
| `/` | `landing.html` | Public landing page |
| `/platform/login` | `platform/login.html` | Platform admin login |
| `/platform/dashboard` | `platform/dashboard.html` | Platform dashboard |
| `/{org}/login` | `login.html` | Org user login |
| `/{org}/dashboard` | `dashboard.html` | User dashboard |
| `/{org}/admin/dashboard` | `admin/dashboard.html` | Org admin dashboard |
| `/{org}/admin/users` | `admin/users.html` | User management |
| `/{org}/admin/departments` | `admin/departments.html` | Department management |
| `/{org}/admin/data-sources` | `admin/data_sources.html` | External DB management |
| `/{org}/tickets` | `tickets/list.html` | Ticket list |
| `/{org}/tickets/create` | `tickets/create.html` | Create ticket |
| `/{org}/tickets/{id}` | `tickets/details.html` | Ticket detail |
| `/{org}/projects` | `projects/list.html` | Project list |
| `/{org}/knowledge-base` | `knowledge_base/index.html` | KB articles |

---

## 8. Notification System

### In-App Notifications

**Signal-driven** via `post_save` on `TicketHistory`:

| Event | Notified Users | Type |
|-------|---------------|------|
| Ticket assigned/reassigned | Assignee | `assigned` |
| Comment added | Assignee + creator | `comment` |
| Status changed | Assignee + creator | `status_change` |
| Priority changed | Assignee | `priority_change` |
| Ticket merged | Assignee | `merged` |
| Any watched event | All watchers (not yet notified) | `watcher` |

### Watcher System

Users can subscribe to tickets via `TicketWatcher`. All watchers receive notifications for events they haven't already been notified about through direct notification.

---

## 9. Email Service

Asynchronous HTML email sending via `threading.Thread` (non-blocking).

| Email Template | Trigger |
|---------------|---------|
| `organization_created.html` | New org created via platform |
| `user_welcome.html` | New user registered |
| `user_updated.html` | User account modified |
| `user_deactivated.html` | User deactivated |
| `ticket_created.html` | New ticket created |
| `ticket_assigned.html` | Ticket assigned/reassigned |
| `ticket_status_changed.html` | Status change |
| `ticket_comment.html` | New comment |
| `ticket_deleted.html` | Ticket deleted |
| `forgot_password_otp.html` | Password reset OTP |
| `feedback_received.html` | User feedback submitted |

---

## 10. Security

### Credential Encryption
- DB passwords encrypted with **Fernet** (AES-128-CBC)
- Key: `DB_CREDENTIALS_ENCRYPTION_KEY` env var (required at boot)
- OTP hashed with **SHA-256** before storage

### Brute-Force Protection
- Cache-based rate limiting on password reset OTP verification (5 attempts)
- Rate limiting on public org registration endpoint

### Attachment Security
- Filename sanitization (strips path traversal chars)
- MIME type whitelist validation
- 10MB file size limit

### Token Replay Prevention
- JWT `org_subdomain` claim validated against URL org on every request
- Prevents using a token from org A against org B

### Input Validation
- Org subdomain regex whitelist: `^[a-z0-9][a-z0-9\-]{0,61}[a-z0-9]$`
- Bulk operation limit: 500 IDs max per request
- SQL injection protection via parameterized queries in connectors

---

## 11. Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Django secret key |
| `DB_CREDENTIALS_ENCRYPTION_KEY` | Yes (prod) | Fernet key for encrypting DB passwords |
| `DATABASE_URL` | No | Primary database connection string |
| `EMAIL_HOST` | No | SMTP server for email sending |
| `EMAIL_HOST_USER` | No | SMTP username |
| `EMAIL_HOST_PASSWORD` | No | SMTP password |
| `DEFAULT_FROM_EMAIL` | No | Sender email address |
| `ALLOWED_HOSTS` | Yes (prod) | Comma-separated allowed hostnames |
| `LOG_TENANT_ROUTING` | No | Enable tenant routing debug logs |
| `DJANGO_SETTINGS_MODULE` | No | Default: `config.settings.dev` |

### Organization Plans

| Plan | Max Users | Max Tickets/mo | Connectors | Dedicated DB |
|------|-----------|---------------|------------|-------------|
| `starter_trial` | 30 | 100 | email | No |
| `growth_cluster` | 200 | Unlimited | email, api, webhook | Yes (BYODB) |

---

## 12. Deployment

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create platform admin
python manage.py shell -c "
from apps.accounts.models import PlatformAdmin
admin = PlatformAdmin(email='admin@platform.com')
admin.set_password('Admin@2026')
admin.save()
"

# Start server
python manage.py runserver 9000
```

### Production Checklist

- [ ] Set `DJANGO_SETTINGS_MODULE=config.settings.production`
- [ ] Generate strong `SECRET_KEY` (50+ chars)
- [ ] Generate `DB_CREDENTIALS_ENCRYPTION_KEY` via `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- [ ] Configure PostgreSQL as primary database
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Enable `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`
- [ ] Configure SMTP email settings
- [ ] Set up `/logs` directory with write permissions
- [ ] Run `python manage.py collectstatic`
- [ ] Deploy behind Nginx/Gunicorn

### Database Migration for BYODB Tenants

When schema changes are deployed, all tenant databases must be migrated:

```bash
# Migrate default DB
python manage.py migrate

# For each tenant with BYODB:
python manage.py migrate --database=tenant_{org_id}
```

---

*Generated: May 2026 | TrackMyTickets Platform v1.0*
