# Multi-Tenant Enterprise Support Desk — Technical Reference

> **Version:** 2.0 (Post-Hardening) · **Last Updated:** March 2026 · **Maintainer:** Platform Engineering

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview & Architecture](#2-system-overview--architecture)
3. [Core Features](#3-core-features)
4. [Multi-Tenant Architecture](#4-multi-tenant-architecture-byodb)
5. [Authentication & Authorization](#5-authentication--authorization)
6. [API Reference — Complete URL Map](#6-api-reference--complete-url-map)
7. [Ticket Lifecycle](#7-ticket-lifecycle)
8. [Database Architecture](#8-database-architecture)
9. [Security Architecture (v2.0 Hardened)](#9-security-architecture-v20-hardened)
10. [Performance & DSA Optimizations (v2.0)](#10-performance--dsa-optimizations-v20)
11. [Observability & Logging](#11-observability--logging)
12. [Background Jobs & Celery](#12-background-jobs--celery)
13. [Deployment Architecture](#13-deployment-architecture)
14. [Default Credentials & Test Access](#14-default-credentials--test-access)
15. [Technical Stack](#15-technical-stack)
16. [Folder Structure](#16-folder-structure)
17. [Future Roadmap](#17-future-roadmap)

---

## 1. Executive Summary

**Multi-Tenant Enterprise Support Desk** is a production-grade B2B SaaS ticket management backend powering multi-organization customer support operations from a single, clean Django monolith.

**Key differentiator:** _Bring Your Own Database_ (BYODB) architecture — each organization brings its own database server (MySQL, PostgreSQL, SQLite). Ticket data is physically isolated per tenant. No shared rows, no logical filtering — true data sovereignty.

**Built for:** SaaS vendors, IT service providers, enterprise helpdesks, and audited environments requiring GDPR / SOC2-style data separation.

**v2.0 Upgrade highlights (March 2026):**
- Async-safe tenant routing (ContextVar replacing thread-locals)
- JWT cross-org replay protection
- Path traversal attack prevention on file uploads
- Atomic rate limiting (TOCTOU fix)
- N+1 query eliminations across all critical paths
- Composite DB indexes for SLA and overdue queries
- Structured logging with Correlation IDs

---

## 2. System Overview & Architecture

### Design Philosophy
- **Data Sovereignty:** Tenant data never shares a DB table with another tenant
- **Robustness:** Graceful 503 if tenant DB unreachable, never a raw 500
- **Auditability:** Every write is logged via `AuditLog` including IP + User Agent
- **Async-Safe:** All tenant context uses `ContextVar` (works under ASGI, Daphne, Uvicorn)

### High-Level Architecture Flow

```mermaid
graph TD
    Client -->|HTTPS Request: /api/acme/*| Nginx
    Nginx --> Gunicorn
    Gunicorn --> CorrelationMiddleware["CorrelationIDMiddleware\n(UUID inject, timer start)"]
    CorrelationMiddleware --> TenantMiddleware["TenantMiddleware\n(resolve org, inject DB config)"]
    TenantMiddleware -->|Org lookup| DefaultDB[(Default DB: accounts, core)]
    TenantMiddleware -->|Set ContextVar alias| ContextVar["ContextVar: tenant_5"]
    ContextVar --> DBRouter["TenantDatabaseRouter\n(reads ContextVar, routes per app_label)"]
    DBRouter -->|tickets, comments, notifications| TenantDB[(Tenant DB: org-specific)]
    DBRouter -->|accounts, core| DefaultDB
    TenantMiddleware --> RateLimitMiddleware["RateLimitMiddleware\n(atomic incr, per-IP + per-org)"]
    RateLimitMiddleware --> DRFView["DRF View\n(Auth → Permission → Queryset → Response)"]
```

---

## 3. Core Features

### 3.1 Identity & Access Management (IAM)

| Aspect | Detail |
|--------|--------|
| User Model | Custom `User` extending `AbstractBaseUser` |
| Roles | `admin`, `manager`, `department_head`, `agent` |
| Organization | Owns users, projects, departments |
| Platform Admin | Super-admin across all orgs, separate model |
| Token system | JWT via `rest_framework_simplejwt` with org binding |
| Password reset | OTP-based, time-limited (15 min) via email |

### 3.2 Ticket Management

| Aspect | Detail |
|--------|--------|
| ID Generation | Thread-safe, project-scoped: `PROJECT_KEY-{n}` (e.g. `ACME-142`) |
| Race protection | `transaction.atomic()` + `select_for_update()` |
| Sources | Web, API, Email, Phone, Chat |
| Priorities | `low`, `medium`, `high`, `critical` |
| Status flow | `open` → `in_progress` → `waiting` → `resolved` → `closed` |
| Merge | Source ticket comments/attachments/watchers transferred to target |
| Watchers | Auto-watch on create and assign; manual watch/unwatch |
| Bulk operations | Assign, close, change_priority, change_status, add_tag, remove_tag |
| Export | CSV export with full filter support |

### 3.3 SLA Management

- Policies per priority: define `response_hours` + `resolution_hours`
- Applied automatically on ticket create; re-applied on priority change
- Breach detected via `is_sla_breached` model property (no background scan needed for single lookups)
- **Indexed filter:** `?sla=breached` uses composite index `(organization, sla_resolution_deadline)` — O(1) seek, no table scan

### 3.4 Knowledge Base

- Hierarchical: `KBCategory` → `KBArticle`
- Draft + Published states
- Internal (agents-only) and external (customer-facing) articles

### 3.5 Comments & Notifications

- Per-ticket threaded comments (public + internal/private)
- Notification layer in `apps.notifications` (event-driven, extensible)
- First-response timer auto-set on first agent comment

### 3.6 Canned Responses

- Pre-saved reply templates per organization
- Instantly insertable into ticket responses

---

## 4. Multi-Tenant Architecture (BYODB)

### Tenant Identification

Every API request carries the organization slug in the URL path:
```
/api/{company_name}/tickets/tickets/
```
`TenantMiddleware.process_view()` extracts `company_name`, resolves the `Organization`, looks up its `ExternalDataSource`, and dynamically injects the database config.

### ContextVar DB Routing (v2.0, async-safe)

```python
# routers.py — async-safe ContextVar replaces threading.local()
_current_db_alias: ContextVar[str] = ContextVar('current_db_alias', default='default')

class TenantDatabaseRouter:
    tenant_apps = frozenset({'tickets', 'comments', 'notifications'})

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.tenant_apps:
            return get_current_db_alias()   # O(1) ContextVar lookup
        return 'default'
```

**Why ContextVar over threading.local?** `threading.local()` binds to OS threads. Under ASGI (Daphne, Uvicorn), one request can hop threads — causing alias bleed between concurrent requests. `ContextVar` binds to the *asyncio task/coroutine*, making routing correct under both WSGI and ASGI.

### DB Registration with Double-Checked Locking (v2.0)

```python
with _db_settings_lock:
    if alias not in settings.DATABASES:
        settings.DATABASES[alias] = db_config
```

Prevents partial-config race when two requests arrive simultaneously for a new tenant.

### Graceful 503 Fallback (v2.0)

If the tenant DB is configured but unreachable:
```json
HTTP 503
{
    "error": "Tenant database is temporarily unavailable.",
    "retry_after": 30
}
```

### Per-App Database Routing Table

| Django App | Routes To |
|-----------|-----------|
| `tickets` | Tenant DB (`tenant_{org_id}`) |
| `comments` | Tenant DB |
| `notifications` | Tenant DB |
| `accounts` | Default DB |
| `core` | Default DB |
| `admin`, `auth` | Default DB |

```mermaid
graph LR
    Request --> ContextVar["ContextVar\ntenant_5"]
    ContextVar --> Router{TenantDatabaseRouter}
    Router -->|app in tenant_apps| TDB[(Tenant DB: MySQL/Postgres)]
    Router -->|app = accounts/core| DefaultDB[(Default DB)]
```

---

## 5. Authentication & Authorization

### JWT Authentication Flow

```mermaid
sequenceDiagram
    Client->>+LoginView: POST /api/{org}/auth/login/
    LoginView->>DefaultDB: Verify User (email + org)
    LoginView-->>Client: access_token (contains org_id, org_subdomain)
    Client->>+DRFView: GET /api/{org}/tickets/ Bearer token
    DRFView->>PlatformJWTAuthentication: Validate token
    PlatformJWTAuthentication-->>DRFView: User object
    DRFView->>IsOrgMember: Check org_subdomain claim == URL org
    IsOrgMember-->>DRFView: 200 OK or 403 Forbidden
```

### JWT Payload (v2.0)

```json
{
    "user_id": 42,
    "org_id": 5,
    "org_subdomain": "acme",     // NEW v2.0: bound to URL slug
    "is_platform_admin": false,
    "exp": 1741234567,
    "iat": 1741148167
}
```

### Role & Permission Matrix

| Permission | Platform Admin | Org Admin | Manager | Agent |
|-----------|:-:|:-:|:-:|:-:|
| Manage all orgs | ✅ | — | — | — |
| View platform stats | ✅ | — | — | — |
| Manage org settings | ✅ | ✅ | — | — |
| Manage users/depts | ✅ | ✅ | — | — |
| Create projects | ✅ | ✅ | — | — |
| Manage SLA policies | ✅ | ✅ | — | — |
| Assign tickets | ✅ | ✅ | ✅ | — |
| Create/comment tickets | ✅ | ✅ | ✅ | ✅ |
| View own dept tickets | ✅ | ✅ | ✅ | ✅ |
| Export CSV | ✅ | ✅ | ✅ | ✅ |

### Cross-Org Protection (v2.0 — Belt & Suspenders)

**Layer 1 — User model:** `request.user.organization_id == org.id`

**Layer 2 — JWT claim (NEW):** `token['org_subdomain'] == request.organization.subdomain`

Both must pass or `IsOrgMember` returns `403`.

---

## 6. API Reference — Complete URL Map

All tenant API routes follow the pattern: **`/api/{company_name}/`**

> Replace `{company_name}` with your organization's subdomain (e.g., `acme`, `techcorp`).

### 6.1 Authentication Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `POST` | `/api/{company}/auth/login/` | None | Login, returns `access_token` + `refresh_token` |
| `POST` | `/api/{company}/auth/register/` | OrgAdmin | Register new user in this org |
| `GET` | `/api/{company}/auth/me/` | Any | Get logged-in user profile |
| `PATCH` | `/api/{company}/auth/profile/` | Any | Update own profile |
| `POST` | `/api/{company}/auth/change-password/` | Any | Change own password (returns new tokens) |
| `POST` | `/api/{company}/auth/forgot-password/` | None | Request OTP to email |
| `POST` | `/api/{company}/auth/reset-password/` | None | Reset password with OTP |
| `GET` | `/api/{company}/auth/users/` | OrgMember | List all users in org |
| `GET/PUT/PATCH/DELETE` | `/api/{company}/auth/users/{id}/` | OrgMember | User detail (role change = OrgAdmin only) |
| `GET/POST/PUT/DELETE` | `/api/{company}/auth/departments/` | OrgMember | Department CRUD |
| `GET` | `/api/{company}/auth/department-head/stats/` | Auth | Aggregated dept stats (single query, v2.0) |
| `GET` | `/api/{company}/auth/department-head/tickets/` | Auth | Department tickets |
| `GET` | `/api/{company}/auth/department-head/employees/` | Auth | Department employee list |
| `GET/PATCH` | `/api/{company}/auth/organization/settings/` | OrgMember | View/update org settings |

### 6.2 Ticket Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `GET` | `/api/{company}/tickets/` | OrgMember | List tickets (paginated, 20/page) |
| `POST` | `/api/{company}/tickets/` | OrgMember | Create ticket |
| `GET` | `/api/{company}/tickets/{ticket_id}/` | OrgMember | Ticket detail with history |
| `PUT/PATCH` | `/api/{company}/tickets/{ticket_id}/` | OrgMember | Update ticket |
| `DELETE` | `/api/{company}/tickets/{ticket_id}/` | OrgAdmin | Delete ticket |
| `POST` | `/api/{company}/tickets/{ticket_id}/comments/` | OrgMember | Add comment/attachment |
| `POST` | `/api/{company}/tickets/{ticket_id}/assign/` | OrgMember | Assign to user |
| `POST` | `/api/{company}/tickets/{ticket_id}/watch/` | OrgMember | Start watching |
| `POST` | `/api/{company}/tickets/{ticket_id}/unwatch/` | OrgMember | Stop watching |
| `GET` | `/api/{company}/tickets/{ticket_id}/watchers/` | OrgMember | List watchers |
| `POST` | `/api/{company}/tickets/{ticket_id}/merge/` | OrgAdminOrManager | Merge source ticket in |
| `POST` | `/api/{company}/tickets/bulk-action/` | OrgMember | Bulk: assign/close/change_priority/change_status |
| `GET` | `/api/{company}/tickets/export/` | OrgMember | CSV export (all filters honored) |
| `GET` | `/api/{company}/tickets/stats/` | OrgMember | Dashboard statistics |
| `GET` | `/api/{company}/tickets/recent-activity/` | OrgMember | Last N history entries |
| `GET` | `/api/{company}/tickets/statuses/` | OrgMember | Available status choices |
| `GET` | `/api/{company}/tickets/priorities/` | OrgMember | Available priority choices |
| `GET` | `/api/{company}/tickets/types/` | OrgMember | Available ticket type choices |

#### Ticket List Filter Parameters

| Param | Values | Example |
|-------|--------|---------|
| `status` | `open,in_progress,waiting,resolved,closed` | `?status=open,in_progress` |
| `priority` | `low,medium,high,critical` | `?priority=high` |
| `assigned_to` | `me`, `unassigned`, or user `id` | `?assigned_to=me` |
| `project` | Project ID | `?project=3` |
| `department` | Department ID | `?department=2` |
| `tag` | Tag name | `?tag=billing` |
| `ticket_type` | `bug`, `feature`, `support`, etc. | `?ticket_type=bug` |
| `source` | `web`, `api`, `email`, `phone` | `?source=email` |
| `sla` | `breached` | `?sla=breached` |
| `overdue` | `true` | `?overdue=true` |
| `watching` | `true` | `?watching=true` |
| `date_from` | `YYYY-MM-DD` | `?date_from=2026-01-01` |
| `date_to` | `YYYY-MM-DD` | `?date_to=2026-03-01` |
| `search` | Free text | `?search=login+error` |
| `ordering` | `created_at,-created_at,priority,status,due_date` | `?ordering=-priority` |
| `page_size` | 1–100 (default 20) | `?page_size=50` |

### 6.3 Projects

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `GET/POST` | `/api/{company}/projects/` | OrgMember | List/Create projects |
| `GET/PUT/PATCH/DELETE` | `/api/{company}/projects/{id}/` | OrgMember | Project detail |

### 6.4 SLA Policies

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `GET/POST` | `/api/{company}/sla-policies/` | OrgMember | List/Create SLA policies |
| `GET/PUT/PATCH/DELETE` | `/api/{company}/sla-policies/{id}/` | OrgAdmin | Manage SLA policy |

### 6.5 Tags

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `GET/POST` | `/api/{company}/tags/` | OrgMember | List/Create tags |
| `PUT/DELETE` | `/api/{company}/tags/{id}/` | OrgAdminOrManager | Manage tag |

### 6.6 Knowledge Base

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `GET/POST` | `/api/{company}/kb/categories/` | OrgMember | List/Create KB categories |
| `GET/POST` | `/api/{company}/kb/articles/` | OrgMember | List/Create KB articles |
| `GET/PUT/DELETE` | `/api/{company}/kb/articles/{id}/` | OrgMember | Article detail |

### 6.7 Canned Responses

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `GET/POST` | `/api/{company}/canned-responses/` | OrgMember | List/Create canned responses |
| `GET/PUT/DELETE` | `/api/{company}/canned-responses/{id}/` | OrgAdminOrManager | Manage canned response |

### 6.8 Audit Logs

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `GET` | `/api/{company}/audit-logs/` | OrgAdmin | List audit events (read-only) |

### 6.9 Core / BYODB Configuration

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `GET/POST` | `/api/{company}/data-sources/` | PlatformAdmin | Manage tenant DB connections |
| `GET/PUT/DELETE` | `/api/{company}/data-sources/{id}/` | PlatformAdmin | Data source detail |
| `GET/POST` | `/api/{company}/mappings/` | PlatformAdmin | Schema mappings |
| `GET/POST` | `/api/{company}/feedback/` | Any | Submit platform feedback |
| `GET/POST` | `/api/{company}/enquiries/` | Any/PlatformAdmin | Public enquiry form / admin list |
| `GET` | `/api/{company}/admin/dashboard/` | PlatformAdmin | Platform-wide admin dashboard |

### 6.10 Platform (Super Admin) API

Base: `/api/platform/`

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `POST` | `/api/platform/login` | None | Platform Admin login |
| `GET` | `/api/platform/me` | PlatformAdmin | Platform Admin profile |
| `GET/POST` | `/api/platform/organizations` | PlatformAdmin | List all orgs / create org |
| `GET` | `/api/platform/stats` | PlatformAdmin | Global platform statistics |
| `GET` | `/api/platform/enquiries` | PlatformAdmin | All enquiries |
| `PATCH` | `/api/platform/enquiries/{id}/read` | PlatformAdmin | Mark enquiry as read |
| `POST` | `/api/platform/public/enquiries` | None | Public enquiry submission |
| `POST` | `/api/platform/forgot-password` | None | Platform admin password reset |
| `POST` | `/api/platform/reset-password` | None | Reset with OTP |

### 6.11 Infrastructure Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/health/` | Health check (returns `{"status": "ok"}`) |
| `GET` | `/robots.txt` | SEO robots file |
| `GET` | `/sitemap.xml` | SEO sitemap |
| `ANY` | `/admin/` | Django admin panel |

### 6.12 Response Headers (v2.0)

All API responses now include:

```
X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
X-Request-Duration-Ms: 34.7
```

---

## 7. Ticket Lifecycle

```mermaid
stateDiagram-v2
    [*] --> open: Created (Web/API/Email/Phone)
    open --> in_progress: Assigned & Agent Working
    in_progress --> waiting: Waiting for customer info
    waiting --> in_progress: Customer replied
    in_progress --> resolved: Issue fixed
    resolved --> closed: Customer confirmed
    closed --> open: Customer reopens
    in_progress --> merged: Merged into parent ticket
```

### SLA Enforcement Timeline

```
Ticket Created ──► SLA applied (response_hours, resolution_hours)
        │
        ├─► response_deadline reached + no first_response_at → BREACH (response)
        │
        └─► resolution_deadline reached + status not resolved/closed → BREACH (resolution)
```

**Breach detection is index-backed (v2.0):**
```sql
-- idx_ticket_org_sla_deadline covers this query:
SELECT * FROM tickets
WHERE organization_id = 5
  AND status NOT IN ('resolved', 'closed')
  AND sla_resolution_deadline < NOW();
```

---

## 8. Database Architecture

### Model Relationships

```mermaid
erDiagram
    ORGANIZATION ||--o{ USER : "1:M"
    ORGANIZATION ||--o{ PROJECT : "1:M"
    ORGANIZATION ||--o{ TICKET : "1:M"
    ORGANIZATION ||--o{ DEPARTMENT : "1:M"
    ORGANIZATION ||--o{ EXTERNALDATASOURCE : "1:1"
    ORGANIZATION ||--o{ SLAPOLICY : "1:M"
    USER ||--o{ TICKET : "created_by / assigned_to"
    PROJECT ||--o{ TICKET : "groups"
    TICKET ||--o{ TICKETHISTORY : "audit trail"
    TICKET ||--o{ ATTACHMENT : "files"
    TICKET ||--o{ COMMENT : "thread"
    TICKET ||--o{ TICKETWATCHER : "subscribers"
    TICKET }o--|| TICKET : "merged_into"
    KBCATEGORY ||--o{ KBARTICLE : "hierarchy"
    TICKET ||--o{ AUDITLOG : "system events"
```

### Ticket Model — Key Indexes (v2.0)

```python
indexes = [
    Index(fields=['organization', 'status']),           # list filter
    Index(fields=['organization', 'project']),           # project filter
    Index(fields=['organization', 'assigned_to']),       # assignee filter
    Index(fields=['organization', 'created_at']),        # date sort
    Index(fields=['organization', 'priority']),          # priority filter
    Index(fields=['organization', 'ticket_type']),       # type filter
    Index(fields=['organization', 'sla_resolution_deadline']),  # NEW v2.0: SLA breach
    Index(fields=['organization', 'due_date']),          # NEW v2.0: overdue filter
]
```

### Cross-Database Foreign Keys

Tickets reference Users across databases (tenant DB → default DB). Handled via:
- `db_constraint=False` on FK fields to satisfy Django ORM
- Application-level validation in `IsOrgMember` (every request)
- Referential integrity enforced at the permission/middleware layer

---

## 9. Security Architecture (v2.0 Hardened)

### Security Layers

```mermaid
graph TD
    Request --> TLS["TLS/HTTPS\n(Nginx + HSTS)"]
    TLS --> CSRF["CSRF Protection\n(Django CsrfMiddleware)"]
    CSRF --> RateLimit["Rate Limiting\n(atomic incr, no race)"]
    RateLimit --> JWT["JWT Validation\n(PlatformJWTAuthentication)"]
    JWT --> OrgClaim["JWT Org Claim Check\n(org_subdomain binding v2.0)"]
    OrgClaim --> Permission["RBAC Permission Classes\n(IsOrgMember etc.)"]
    Permission --> View["View Logic\n(ORM: org-scoped querysets)"]
```

### Security Fixes Applied (v2.0)

#### C1 — Async-Safe Tenant Routing
- **Threat:** Under ASGI, `threading.local()` allows tenant DB alias to leak between concurrent coroutines — serving tenant A's data to tenant B.
- **Fix:** Replaced with `contextvars.ContextVar` — binds to asyncio task, not OS thread.

#### C2 — JWT Cross-Org Replay Prevention
- **Threat:** A valid JWT from `orgA/login` could be replayed against `orgB` endpoints. `IsOrgMember` only checked `user.organization_id` which could theoretically match.
- **Fix (Login):** JWT now includes `org_subdomain` claim bound to the login organization:
  ```python
  refresh['org_subdomain'] = organization.subdomain
  ```
- **Fix (Permission):** `IsOrgMember` validates the claim on every authenticated request:
  ```python
  if token_subdomain and token_subdomain != org.subdomain:
      return False  # 403
  ```

#### C3 — Path Traversal on File Uploads
- **Threat:** Upload filename `../../etc/passwd` would write outside the intended storage directory.
- **Fix:** Whitelist-based filename sanitizer applied before any storage call:
  ```python
  # "../../etc/passwd" → "passwd"
  # "../confs/secret.key" → "secret.key"
  name = os.path.basename(raw_name)
  name = re.sub(r'[^\w\-.]', '_', name)
  name = name[:200] or 'attachment'
  ```

#### H5 — Rate Limiter TOCTOU Race
- **Threat:** Two concurrent requests both reading count=limit-1 could both pass the rate check.
- **Fix:** Atomic `cache.add()` + `cache.incr()` — the incr return value is the authoritative count:
  ```python
  added = cache.add(key, 1, timeout=window)  # atomic set-if-absent
  if added: return False    # first request in window
  count = cache.incr(key)   # atomic increment
  return count > limit
  ```

### Security Configuration

| Setting | Value |
|---------|-------|
| `SECURE_BROWSER_XSS_FILTER` | `True` |
| `X_FRAME_OPTIONS` | `DENY` |
| `CSRF_COOKIE_SECURE` | `True` (prod) |
| `SESSION_COOKIE_SECURE` | `True` (prod) |
| `SECURE_HSTS_SECONDS` | `31536000` |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` |
| `SECURE_HSTS_PRELOAD` | `True` |
| DB credentials encryption | AES via `apps.core.utils.encryption` |
| Rate limit (per IP) | 200 req/min |
| Rate limit (per org) | 1000 req/min |

---

## 10. Performance & DSA Optimizations (v2.0)

### Before & After Complexity Table

| Operation | Before | After | DB Calls: 50-agent dept |
|-----------|--------|-------|------------------------|
| Dept head stats | O(7 + 4n) queries | O(2) aggregate | **~207 → 2** |
| Bulk history insert (100 tickets) | O(n) INSERTs | O(1) `bulk_create` | **100 → 1** |
| CSV export tag names (10k tickets) | O(n) per-ticket query | O(1) prefetch | **10k → 1** |
| Watcher transfer on merge | O(m) get_or_create | Set-diff + bulk_create | **50 → 2** |
| Manager ticket filter | 2 queries (IN subquery) | 1 ORM subquery join | **2 → 1** |
| SLA breach detection | Full table scan | Index seek | **100ms → <1ms at 100k** |
| Overdue detection | Full table scan | Index seek | **100ms → <1ms at 100k** |
| Rate limit check | TOCTOU (racy, 2 ops) | Atomic (2 ops, correct) | **Race eliminated** |
| Tenant DB routing | threading.local (unsafe) | ContextVar (O(1), safe) | **Correctness fix** |

### Key Query Patterns

**DepartmentHead Stats — Single Aggregate:**
```python
agg = Ticket.objects.filter(org=org, dept=dept).aggregate(
    total=Count('id'),
    open=Count('id', filter=Q(status='open')),
    in_progress=Count('id', filter=Q(status__in=['in_progress', 'inprocess'])),
    resolved=Count('id', filter=Q(status='resolved')),
    ...
)
# → 1 SQL query with conditional COUNTs
```

**CSV Export — Zero N+1:**
```python
queryset = queryset.prefetch_related(
    Prefetch('tags', queryset=Tag.objects.only('name'))
).select_related('project', 'assigned_to').iterator(chunk_size=500)
# → 2 queries total regardless of ticket count
```

**Bulk History — Single INSERT:**
```python
TicketHistory.objects.bulk_create([
    TicketHistory(ticket=t, user=user, action='assigned', new_value=name)
    for t in tickets
])
# → 1 batch INSERT instead of n individual INSERTs
```

---

## 11. Observability & Logging

### CorrelationID Middleware (v2.0 — NEW)

Every request automatically gets:
- A UUID4 Correlation ID (or accepts `X-Correlation-ID` from upstream LB)
- Wall-clock timer from middleware entry
- Structured completion log on response

```
INFO apps: request_complete correlation_id=abc-123 tenant_id=5 user_id=42 method=GET path=/api/acme/tickets/ status=200 duration_ms=34.7
```

Response headers on every API call:
```http
X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
X-Request-Duration-Ms: 34.7
```

### Logging Configuration

| Logger | Handler | Level | Output |
|--------|---------|-------|--------|
| `apps` | `console` + `file` | `DEBUG` (dev), `INFO` (prod) | `logs/django.log` |
| `django.request` | `error_file` | `ERROR` | `logs/django_error.log` |
| `django.db.backends` | `console` | `DEBUG` (dev only) | SQL queries |

### AuditLog Model

Every mutating API action creates an `AuditLog` entry:

```python
AuditLog.log(request, action='create', resource_type='ticket', resource_id=ticket.id,
             description='Created ticket ACME-142: Login broken')
# Captures: user_id, organization_id, ip_address, user_agent, extra_data, timestamp
```

Audit events tracked: `create`, `update`, `delete`, `export`, `bulk_action`, `login`, `settings_change`, `merged`.

---

## 12. Background Jobs & Celery

| Task | Trigger | Description |
|------|---------|-------------|
| Email dispatch | On ticket event | Notify assignee/watchers on create/update/comment |
| SLA breach check | Periodic (cron) | Scan for breached SLAs and mark/alert |
| DB sync | On-demand / periodic | Sync `ExternalDataSource` schema mappings |
| OTP cleanup | Periodic | Remove expired password-reset OTPs |

**Configuration (`config/celery.py`):**
```python
app = Celery('ticket_system')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()  # auto-discovers tasks in all INSTALLED_APPS
```

**Broker:** Redis (`CELERY_BROKER_URL`)
**Result backend:** Redis (`CELERY_RESULT_BACKEND`)

---

## 13. Deployment Architecture

### Production Stack

```mermaid
graph LR
    Internet -->|HTTPS :443| Nginx
    Nginx -->|Proxy| Gunicorn["Gunicorn\n(workers = 2×CPU+1)"]
    Nginx -->|/static/| WhiteNoise["WhiteNoise\n(static files)"]
    Gunicorn --> Django["Django App\n(ContextVar-safe)"]
    Django --> PgBouncer["PgBouncer\n(connection pooler)"]
    PgBouncer --> DefaultPG[(PostgreSQL: default)]
    Django --> TenantDBs[(Tenant Databases\nMySQL/Postgres/etc.)]
    Django --> Redis[(Redis\nCache + Celery Broker)]
    Redis --> Celery["Celery Workers\n(background tasks)"]
```

### Docker Compose Services

| Service | Image | Port |
|---------|-------|------|
| `web` | Custom Django | 8000 |
| `nginx` | nginx:alpine | 80, 443 |
| `db` | postgres:15 | 5432 |
| `redis` | redis:7-alpine | 6379 |
| `celery` | Same as web | — |

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `SECRET_KEY` | Django secret | `django-insecure-...` |
| `DEBUG` | Debug mode | `False` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `trackmytickets.in,www.trackmytickets.in` |
| `DATABASE_URL` | Default DB | `postgres://user:pass@localhost:5432/db` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `DB_CREDENTIALS_ENCRYPTION_KEY` | AES key for BYODB conn strings | 32-byte base64 key |
| `EMAIL_HOST` / `EMAIL_PORT` | SMTP for OTPs | `smtp.gmail.com` / `587` |
| `EMAIL_HOST_USER` | Sender email | `noreply@trackmytickets.in` |
| `EMAIL_HOST_PASSWORD` | SMTP password | — |
| `ORG_RATE_LIMIT` | Requests/min per org | `1000` |
| `IP_RATE_LIMIT` | Requests/min per IP | `200` |

---

## 14. Default Credentials & Test Access

> ⚠️ **Change all default credentials immediately in production.**

### Platform Admin (Super Admin)

| Field | Value |
|-------|-------|
| **Login URL** | `POST /api/platform/login` |
| **Email** | `admin@trackmytickets.in` |
| **Password** | `Admin@123` |
| **Dashboard URL (Web)** | `http://localhost:8000/platform/dashboard` |
| **API Base** | `http://localhost:8000/api/platform/` |

### Demo Organization

| Field | Value |
|-------|-------|
| **Company Slug** | `demo` |
| **API Base** | `http://localhost:8000/api/demo/` |
| **Web Login** | `http://localhost:8000/demo/login` |

### Demo Tenant Users

| Role | Email | Password |
|------|-------|----------|
| Org Admin | `admin@demo.com` | `Admin@123` |
| Manager | `manager@demo.com` | `Manager@123` |
| Agent | `agent@demo.com` | `Agent@123` |

### Login Request Example

```bash
# Tenant user login
curl -X POST http://localhost:8000/api/demo/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@demo.com", "password": "Admin@123"}'

# Platform admin login
curl -X POST http://localhost:8000/api/platform/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@trackmytickets.in", "password": "Admin@123"}'
```

### Authenticated API Request Example

```bash
# Use the access_token from login
curl http://localhost:8000/api/demo/tickets/ \
  -H "Authorization: Bearer <access_token>"
```

### Health Check

```bash
curl http://localhost:8000/health/
# → {"status": "ok", "timestamp": "2026-03-04T01:00:00Z"}
```

---

## 15. Technical Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11+ |
| Framework | Django | 5.0 |
| API | Django REST Framework | 3.15 |
| Auth | `rest_framework_simplejwt` | 5.x |
| Default DB | PostgreSQL (prod) / SQLite (dev) | 15 |
| Tenant DB | Any: PostgreSQL, MySQL, MariaDB, SQLite | — |
| Cache / Broker | Redis | 7 |
| Background Tasks | Celery | 5.x |
| Web Server | Gunicorn | 21+ |
| Reverse Proxy | Nginx | 1.25+ |
| Static Files | WhiteNoise | 6.x |
| Encryption | PyCryptodome (AES) | — |
| Correlation | `contextvars` (stdlib, Python 3.7+) | — |

---

## 16. Folder Structure

```
ticket_system_django/
├── apps/
│   ├── accounts/           # IAM: User, Organization, Department, Auth
│   │   ├── models.py       # User, PlatformAdmin, Organization, Department, UserRole
│   │   ├── views.py        # LoginView, RegisterView, UserListView, DeptHeadStats...
│   │   ├── authentication.py # PlatformJWTAuthentication
│   │   ├── serializers.py
│   │   ├── urls.py         # Tenant auth routes
│   │   ├── platform_urls.py # Platform admin routes
│   │   ├── platform_views.py
│   │   └── web_urls.py
│   ├── core/
│   │   ├── models.py       # ExternalDataSource, SchemaMapping, Feedback, Enquiry
│   │   ├── permissions.py  # IsOrgMember (JWT org claim check v2.0)
│   │   ├── routers.py      # TenantDatabaseRouter (ContextVar, v2.0)
│   │   └── middleware/
│   │       ├── tenant.py   # TenantMiddleware (lock+503 fallback, v2.0)
│   │       ├── rate_limit.py # RateLimitMiddleware (atomic, v2.0)
│   │       └── correlation.py # NEW v2.0: CorrelationID + timing
│   ├── tickets/
│   │   ├── models.py       # Ticket, Project, SLAPolicy, TicketHistory, AuditLog...
│   │   ├── views.py        # TicketViewSet + all actions (bulk_create, prefetch v2.0)
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── migrations/
│   │   │   └── 0004_add_sla_due_date_indexes.py  # NEW v2.0
│   │   └── web_urls.py
│   ├── comments/           # Comment model + serializers
│   └── notifications/      # Notification model + event handlers
├── config/
│   ├── settings/
│   │   ├── base.py         # Core settings (CorrelationMiddleware added v2.0)
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py             # Root URL configuration
│   └── celery.py           # Celery app setup
├── tests/
│   ├── test_crud_operations.py
│   ├── test_browser_ui.py
│   └── locustfile.py       # Load testing
├── ENTERPRISE_DOCUMENTATION.md
├── deploy_docker.sh
└── requirements.txt
```

---

## 17. Future Roadmap

### Near-Term (Justified by codebase analysis)
- **Celery task idempotency:** Add deduplification keys to prevent double-processing of SLA alerts on worker restart
- **Structured JSON logging:** Full JSON log format for Elasticsearch/Loki ingestion
- **DB-level audit triggers:** PostgreSQL event triggers as a secondary safety net

### Medium-Term
- **Real-time notifications:** WebSocket layer (Django Channels) for live ticket updates without polling
- **Plugin framework:** Webhook-based integrations (Slack, PagerDuty, Jira) for ticket events
- **Multi-DB migrations:** Automated schema provisioning when a new BYODB tenant is onboarded

### Long-Term (Open-Source Microservice Options)
- **Notification Service:** Extract `apps.notifications` → standalone FastAPI service (open-source)
- **Analytics Service:** Separate read-replica aggregation service for global cross-tenant analytics using **Apache Superset** (open-source BI)
- **AI/Vector Search:** Semantic search on ticket history using **Milvus** (open-source vector DB) + **sentence-transformers`** for canned response suggestions
- **Event Streaming:** **Apache Kafka** (open-source) for `ExternalDataSource` sync events — replacing synchronous loops
