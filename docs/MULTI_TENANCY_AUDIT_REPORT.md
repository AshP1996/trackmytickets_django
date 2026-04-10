# Multi-Tenancy Audit Report — TrackMyTickets

**Date:** 2026-03-13  
**Scope:** Full multi-tenant architecture validation, security audit, and fixes.

---

## 1. Architecture Summary

### Components Analyzed

| Component | Location | Role |
|-----------|----------|------|
| TenantMiddleware | `apps/core/middleware/tenant.py` | Extracts `company_name` from URL, resolves Organization, sets DB alias |
| TenantDatabaseRouter | `apps/core/routers.py` | Routes ORM queries to `default` or `tenant_N` based on ContextVar |
| Organization extraction | `_extract_company_name()` | Parses `/acme/dashboard`, `/api/acme/tickets`, returns `acme` |
| Excluded paths | `_is_excluded_path()` | `/admin/`, `/static/`, `/media/`, `/health`, `/platform/` |

### Data Flow

1. Request arrives at `/api/acme/tickets/`
2. TenantMiddleware `process_view` extracts `company_name=acme` (from `view_kwargs` or path)
3. Looks up `Organization` in default DB where `subdomain='acme'`
4. If BYODB: registers `tenant_{org_id}` in `DATABASES`, sets `set_current_db_alias('tenant_N')`
5. Otherwise: alias stays `default` (from `reset_current_db_alias()` at start)
6. TenantDatabaseRouter: platform models → `default`, tenant apps → `get_current_db_alias()`

---

## 2. Issues Found & Fixes Applied

### BUG 1: Shared-DB Leak in `UserDetailView.get_queryset`

**Problem:** When using shared `default` DB (no BYODB), `User.objects.all()` returns users from ALL organizations.

**Location:** `apps/accounts/views.py` — `UserDetailView.get_queryset`

**Fix:**
```python
from apps.core.routers import get_current_db_alias
if get_current_db_alias() == 'default':
    org_qs = User.objects.filter(organization_id=self.request.organization.id)
else:
    org_qs = User.objects.all()
```

### BUG 2: Shared-DB Leak in `AdminDashboardView`

**Problem:** `Ticket.objects.all()` and `User.objects.all()` leak cross-tenant data in shared mode.

**Location:** `apps/core/views.py` — `AdminDashboardView.get`

**Fix:** Same pattern: when `get_current_db_alias() == 'default'`, filter by `organization_id`.

### BUG 3: Shared-DB Leak in `DepartmentViewSet.get_queryset`

**Problem:** `Department.objects.all()` returns all departments across orgs in shared mode.

**Location:** `apps/accounts/views.py` — `DepartmentViewSet.get_queryset`

**Fix:** When default DB, filter by `organization_id`.

### BUG 4: Email Uniqueness Check in Shared DB

**Problem:** `UserCreateSerializer.validate_email` used `User.objects.filter(email__iexact=value).exists()` without `organization_id`, causing false rejections when same email exists in another org.

**Location:** `apps/accounts/serializers.py`

**Fix:** When in default DB and org is set, add `organization_id` filter.

### IMPROVEMENT 1: Platform Path Exclusion

**Change:** Added `/platform/` to `_is_excluded_path()` so platform login/dashboard never receive tenant context.

**Location:** `apps/core/middleware/tenant.py`

### IMPROVEMENT 2: Debug Logging

**Change:** Optional `LOG_TENANT_ROUTING=True` in settings logs:
- `[TENANT] org=acme org_id=5 path=/api/acme/tickets/`
- `[TENANT] db_alias=tenant_5 db_name=acme_db`

**Usage:** Add to `.env` or settings: `LOG_TENANT_ROUTING=True`

---

## 3. Security Validation

### Cross-Tenant Isolation Verified

| Check | Status |
|-------|--------|
| JWT `org_id` vs request org | ✅ Blocked in TenantMiddleware (403) |
| Token replay (Acme token → Stark URL) | ✅ `IsOrgMember` checks `org_subdomain` |
| Shared DB queries without `organization_id` | ✅ Fixed in User, Department, AdminDashboard |
| Platform models always on default | ✅ Router `platform_models` set |
| ContextVar reset on exception | ✅ `process_exception` resets alias |

### No Raw SQL Bypassing Router

- Connectors (sqlite, mysql, postgres) use explicit tenant connections from ExternalDataSource, not main app DB.
- Health check uses default connection.

---

## 4. Test Cases Added

**File:** `apps/core/tests/test_tenant_isolation.py`

| Test | Purpose |
|------|---------|
| `TenantMiddlewareTests.test_extract_company_name_*` | Path parsing for `/acme/`, `/api/acme/`, `/api/platform/` |
| `TenantMiddlewareTests.test_is_excluded_path_*` | Admin, platform, static excluded |
| `TenantRouterTests.test_platform_models_route_to_default` | Organization, GlobalUser → default |
| `TenantRouterTests.test_tenant_models_use_current_alias` | User, Ticket follow ContextVar |
| `CrossTenantIsolationTests.test_acme_cannot_access_stark_tickets_via_api` | Cross-org API blocked |
| `CrossTenantIsolationTests.test_token_replay_blocked` | Acme token fails on Stark `/auth/me/` |
| `TenantDebugEndpointTests.test_debug_endpoint_returns_tenant_info` | Debug endpoint response shape |

**Run:** `python manage.py test apps.core.tests.test_tenant_isolation`

---

## 5. Debug Endpoint

**URL:** `/api/<company_name>/debug/tenant/`

**Example:** `GET /api/acme/debug/tenant/`

**Response (when DEBUG or ENABLE_TENANT_DEBUG=True):**
```json
{
  "organization": "acme",
  "org_id": 5,
  "database_alias": "tenant_5",
  "database_name": "acme_db"
}
```

**Security:** Returns 404 when `DEBUG=False` and `ENABLE_TENANT_DEBUG` not set.

---

## 6. Recommendations

### Performance

- Cache `ExternalDataSource` lookup per request when alias already in `DATABASES`
- Consider Redis cache for Organization-by-subdomain when high traffic

### Security

- Add `process_response` to TenantMiddleware to reset ContextVar on normal completion (defense in depth; `process_view` reset at start already mitigates)
- Consider rate limiting per-organization for sensitive endpoints
- Enforce `organization_id` filter at model manager level for tenant models in shared DB

### Scalability

- Document BYODB provisioning for new tenants
- Consider connection pooling limits per `tenant_N` to avoid exhaustion
- Add metrics for per-tenant DB latency

### Database Routing Safety

- Add integration test that creates two orgs in shared DB, creates tickets for each, and asserts Acme cannot see Stark tickets via API
- Consider a base `TenantQuerysetMixin` that automatically filters by `request.organization_id` when alias is `default`

---

## 7. Files Modified

| File | Changes |
|------|---------|
| `apps/accounts/views.py` | UserDetailView, DepartmentViewSet: org_id filter for shared DB |
| `apps/accounts/serializers.py` | UserCreateSerializer: org_id in email uniqueness |
| `apps/core/views.py` | AdminDashboardView: org_id filter for tickets/users |
| `apps/core/middleware/tenant.py` | Added `/platform/` to excluded paths, debug logging |
| `apps/core/debug_views.py` | New: tenant debug endpoint |
| `apps/core/debug_urls.py` | New: URL config for debug |
| `config/urls.py` | Added `api/<company_name>/debug/` route |
| `apps/core/tests/test_tenant_isolation.py` | New: tenant isolation tests |
