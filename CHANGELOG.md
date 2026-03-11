# CHANGELOG — TrackMyTickets Full Audit & Advanced Feature Upgrade

> **Date**: February 2026  
> **Scope**: Comprehensive audit, bug fixes, and advanced feature enhancements across the entire multi-tenant ticket management system.

---

## Phase 1: Critical Bug Fixes

### Bug 1 — `get_allowed_transitions` Always Returned `[]`
**File**: `apps/tickets/serializers.py` — `TicketDetailSerializer`  
**Problem**: The `get_allowed_transitions` method had a `TODO` placeholder and always returned an empty list. The UI couldn't display valid next-status buttons (e.g., "Resolve", "Close").  
**Fix**: Implemented a proper state machine map:

| Current Status | Allowed Transitions |
|---------------|---------------------|
| `open` | `in_progress`, `waiting`, `closed` |
| `in_progress` | `waiting`, `resolved`, `open` |
| `waiting` | `in_progress`, `open`, `closed` |
| `resolved` | `closed`, `open` |
| `closed` | `open` |

**Why**: Without valid transitions the front-end "Change Status" buttons were always hidden. This is a core workflow feature.

---

### Bug 2 — Deprecated `.extra()` in Project Analytics
**File**: `apps/core/views.py` — `AdminDashboardView`  
**Problem**: Used `.extra({'date': "date(updated_at)"})` which is deprecated in Django 4+ and DB-specific (PostgreSQL SQL).  
**Fix**: Replaced with `TruncDate` from `django.db.models.functions`:
```python
from django.db.models.functions import TruncDate
qs.annotate(date=TruncDate('updated_at')).values('date').annotate(count=Count('id'))
```
Also fixed `timezone.timedelta` → `timedelta` (from `datetime`).  
**Why**: `.extra()` is deprecated and causes errors on some databases. `TruncDate` is the idiomatic Django approach and works across all DB backends.

---

### Bug 3 — Notification Signal Missed `status_changed` Events
**File**: `apps/notifications/signals.py`  
**Problem**: Only handled `assigned`/`reassigned` and `added_comment` actions. Status changes (e.g., ticket resolved) and priority changes did not fire notifications.  
**Fix**: Added signal handlers for:
- `status_changed` → notifies assigned user and all watchers  
- `priority_changed` → notifies assigned user and all watchers  

Also updated all notification paths to include **ticket watchers** (`ticket.watchers.all()`).  
**Why**: Users need to know when tickets they're involved with change status or priority. Watchers should always be in the loop.

---

### Bug 4 — No API Pagination
**File**: `apps/tickets/views.py`  
**Problem**: `TicketViewSet` and `ProjectViewSet` returned all records in a single response. With thousands of tickets this would cause timeouts and memory issues.  
**Fix**: Added `StandardPagination` (PageNumberPagination) with `page_size=20`, `max_page_size=100`, configurable via query param.  
Applied to: `TicketViewSet`, `ProjectViewSet`, `KBArticleViewSet`, `AuditLogViewSet`.  
**Why**: Pagination is essential for any production API that serves lists. Without it, page load times degrade linearly with data volume.

---

### Bug 5 — `User.department` Was a Plain `CharField`
**File**: `apps/accounts/models.py`  
**Problem**: `department` was a `CharField` while a proper `Department` model existed. This caused inconsistency and made department-user relationships unreliable.  
**Fix**: Added `department_fk = ForeignKey(Department, null=True, blank=True, on_delete=SET_NULL)` while keeping the old `CharField` for backward compatibility.  
**Why**: A ForeignKey allows proper relational queries (e.g., "all users in Engineering"), enforces referential integrity, and supports the `Department` model features.

---

### Bug 6 — `addComment` in `api.js` Had Incorrect Signature
**File**: `static/js/api.js`  
**Problem**: The `addComment(ticketId, comment, isInternal)` function didn't accept a `files` parameter, but the detail page was calling it with 4 arguments. File uploads were silently broken.  
**Fix**: Updated signature to `addComment(ticketId, comment, files = [], isInternal = false)`. When files are present, it now sends `FormData` instead of JSON.  
**Why**: Attachments on comments are a core feature. The mismatched signature meant no files were ever uploaded when commenting.

---

### Bug 7 — `Comment.user` Used `CASCADE` Delete
**File**: `apps/comments/models.py`  
**Problem**: `user = ForeignKey(User, on_delete=CASCADE)` — deleting a user would delete all their comments, losing valuable ticket history.  
**Fix**: Changed to `on_delete=SET_NULL, null=True, blank=True`.  
**Why**: Comments are part of the ticket audit trail. They must be preserved even if the author account is deactivated or deleted.

---

### Bug 8 — `EnquiryViewSet` Had `AllowAny` Permission
**File**: `apps/core/views.py`  
**Problem**: `EnquiryViewSet` used `permissions.AllowAny`, meaning unauthenticated users could read all enquiries.  
**Fix**: Changed to `permissions.IsAuthenticated`.  
**Why**: Enquiry data may contain sensitive business information. Only authenticated org members should access it.

---

### Bug 9 — `RateLimitMiddleware` Ran Before `request.organization` Was Set
**File**: `apps/core/middleware/rate_limit.py`  
**Problem**: The middleware tried to access `request.organization` in `__call__`, but `TenantMiddleware` hadn't populated it yet.  
**Fix**: Changed from `__call__` to `process_view` so it runs after all middleware `__call__` methods (including `TenantMiddleware`).  
**Why**: Rate limiting per-organization requires the organization to be resolved first.

---

### Bug 10 — `print()` Statements Used Throughout Codebase
**Files**: Multiple (`views.py`, `platform_views.py`, `middleware/tenant.py`, etc.)  
**Problem**: Debug `print()` statements don't go to log files, can't be filtered by severity, and pollute stdout in production.  
**Fix**: Replaced all `print()` calls with `logging.getLogger(__name__)` and appropriate levels (`logger.info`, `logger.error`). Added `LOGGING` config in `settings/base.py` with `RotatingFileHandler`.  
**Why**: Proper logging is essential for production debugging, monitoring, and audit trails.

---

### Bug 11 — `bulk_action` Stale Status Bug
**File**: `apps/tickets/views.py`  
**Problem**: In the 'close' bulk action, `old_status` was read **after** `tickets.update(status='closed')`, so it always read 'closed'.  
**Fix**: Captured `old_status` values **before** the `.update()` call.  
**Why**: TicketHistory needs the correct `old_value` → `new_value` transition for accurate audit trails.

---

### Bug 12 — Duplicate `MessageMiddleware` in Settings
**File**: `config/settings/base.py`  
**Problem**: `django.contrib.messages.middleware.MessageMiddleware` appeared twice in `MIDDLEWARE`.  
**Fix**: Removed the duplicate.  
**Why**: Duplicate middleware causes messages to be processed twice, leading to subtle bugs.

---

## Phase 2: Advanced Feature Enhancements

### Feature 1 — Ticket Tags / Labels
**Files**: `tickets/models.py`, `tickets/serializers.py`, `tickets/views.py`, `tickets/urls.py`  
**What**: Added `Tag` model with `name`, `color`, `organization` FK. Added M2M relationship `tags` on `Ticket`. Created `TagViewSet` for CRUD operations. Tags are displayed on ticket cards, can be filtered by, and managed on ticket detail pages.  
**Why**: Tags provide flexible categorization beyond status/priority. Teams often need custom labels like "regression", "customer-reported", "documentation-needed".

---

### Feature 2 — SLA Policy Enforcement
**Files**: `tickets/models.py`, `tickets/serializers.py`, `tickets/views.py`  
**What**: Added `SLAPolicy` model with `priority`, `response_hours`, `resolution_hours`, `escalation_hours`, per organization. Tickets now have:
- `sla_response_deadline` / `sla_resolution_deadline` (auto-set on create)
- `first_response_at` / `resolution_time_seconds` (tracked on updates)
- `sla_status` computed field in serializers (`on_track`, `at_risk`, `breached`)
- Dashboard SLA summary widget (on-track vs breached counts)

**Why**: SLA management is critical for support teams with contractual response time commitments. Without SLA tracking, teams can't identify and prevent breaches.

---

### Feature 3 — Ticket Search & Filtering
**Files**: `tickets/views.py`, `templates/tickets/list.html`  
**What**: Added `SearchFilter` and `OrderingFilter` to `TicketViewSet`. Frontend filter bar includes:
- Status, Priority, Ticket Type, Tag, SLA Status dropdowns
- Full-text search on subject/description
- Ordering by created_at, updated_at, priority

**Why**: As ticket volume grows, finding specific tickets becomes the primary UX challenge. Comprehensive filtering is essential for productivity.

---

### Feature 4 — Bulk Ticket Operations
**Files**: `tickets/views.py`, `templates/tickets/list.html`, `static/js/api.js`  
**What**: Added `bulk_action` endpoint supporting:
- Bulk assign (change `assigned_to`)
- Bulk close (change status to `closed`)
- Bulk change priority
- Bulk add/remove tags

Frontend includes checkbox selection on each ticket row and a "Bulk Actions" dropdown.  
**Why**: Managers handling dozens of tickets daily need batch operations to avoid repetitive one-by-one updates.

---

### Feature 5 — Ticket Export (CSV)
**Files**: `tickets/views.py`, `templates/tickets/list.html`  
**What**: Added `export` endpoint that generates a CSV with columns: Ticket ID, Subject, Status, Priority, Type, Assigned To, Created, Updated, Due Date, SLA Status. Applies the same filters as the list view.  
**Why**: Teams need to export ticket data for reporting, SLA reviews, management presentations, and integration with external tools.

---

### Feature 6 — Dashboard Activity Feed
**Files**: `tickets/views.py`, `templates/dashboard.html`  
**What**: Added `recent_activity` endpoint returning the last N ticket history entries. Dashboard renders these as a vertical activity feed with icons, user names, action descriptions, and relative timestamps.  
**Why**: A live activity feed gives managers instant visibility into team operations without needing to click into individual tickets.

---

### Feature 7 — Enhanced Analytics
**Files**: `tickets/views.py`, `templates/dashboard.html`  
**What**: Enhanced the `stats` endpoint with:
- **Trend chart**: Tickets created per day (last 14 days) — rendered as a line chart
- **Agent performance leaderboard**: Top 10 agents by resolved tickets, with avg resolution time
- **SLA summary**: On-track vs breached counts displayed as stat cards
- **Type distribution**: Doughnut chart showing tickets by type
- **Overdue/Unassigned counts**: Highlighted stat cards

**Why**: Analytics transform raw data into actionable insights. Trend charts reveal workload patterns; agent leaderboards foster healthy competition; SLA widgets highlight urgent issues.

---

### Feature 8 — Ticket Watchers
**Files**: `tickets/models.py`, `tickets/views.py`, `tickets/serializers.py`, `templates/tickets/details.html`  
**What**: Added `TicketWatcher` model (M2M through table). Users can watch/unwatch tickets. Watchers receive notifications for all ticket events (comments, status changes, priority changes). The detail page shows a watchers section with add/remove capabilities.  
**Why**: Stakeholders (PMs, team leads, executives) often need to monitor specific tickets without being the assignee. Watchers provide a clean opt-in notification mechanism.

---

### Feature 9 — Ticket Merge
**Files**: `tickets/models.py`, `tickets/views.py`, `templates/tickets/details.html`  
**What**: Added `merged_into` FK and `is_merged` flag on `Ticket`. The `merge_tickets` endpoint closes source tickets, copies their comments to the target, and records the merge in history. UI provides a merge modal on the detail page.  
**Why**: Duplicate tickets are common in support systems. Merging consolidates context and prevents agents from working on the same issue separately.

---

### Feature 10 — Canned Responses
**Files**: `tickets/models.py`, `tickets/views.py`, `tickets/serializers.py`, `templates/tickets/details.html`  
**What**: Added `CannedResponse` model with title, content, category, and shortcode. The comment form on ticket detail includes a "Canned Responses" dropdown that inserts pre-written text.  
**Why**: Support teams repeatedly type the same responses ("We're looking into this", "Could you provide more details?"). Canned responses save time and ensure consistency.

---

### Feature 11 — Knowledge Base
**Files**: `tickets/models.py`, `tickets/views.py`, `tickets/serializers.py`, `tickets/urls.py`, `tickets/web_urls.py`, `templates/knowledge_base/index.html`, `templates/knowledge_base/article.html`  
**What**: Added `KBCategory` and `KBArticle` models with full CRUD endpoints. Features include:
- Category browsing with article counts
- Full-text search across title, content, and tags
- Status-based visibility (draft articles hidden from non-admins)
- View counting and "Was this helpful?" feedback mechanism
- Pinned articles support

**Why**: A knowledge base reduces ticket volume by enabling self-service. Common issues documented as articles deflect support requests and empower users.

---

### Feature 12 — Audit Logging
**Files**: `tickets/models.py`, `tickets/views.py`, `tickets/serializers.py`  
**What**: Added `AuditLog` model tracking `action`, `model_name`, `object_id`, `changes` (JSON), `ip_address`, `user_agent`, `user`, `organization`, `timestamp`. Read-only API endpoint restricted to admins.  
**Why**: Audit logs provide accountability and traceability. They're required for compliance (SOC2, ISO 27001) and essential for investigating security incidents.

---

## Phase 3: UI Polish

### Enhancement 1 — Ticket Filters UI
**File**: `templates/tickets/list.html`  
**What**: Added a full filter bar above the tickets table with dropdowns for Status, Priority, Ticket Type, Tags, and SLA Status. Includes search input and "Reset" button.  
**Why**: Filters must be visible and accessible — hidden or complex filter UIs lead to underutilization.

---

### Enhancement 2 — SLA Badge on Ticket Cards
**Files**: `templates/tickets/list.html`, `templates/tickets/details.html`  
**What**: Tickets display a colored SLA badge: green "On Track", yellow "At Risk", red "Breached", or gray "No SLA".  
**Why**: SLA status must be immediately visible without clicking into each ticket. Color-coded badges enable quick scanning.

---

### Enhancement 3 — Activity Timeline on Ticket Detail
**File**: `templates/tickets/details.html`  
**What**: Ticket history is rendered as a vertical timeline with colored icons per action type, user names, old/new values, and relative timestamps.  
**Why**: A timeline view is more scannable than a flat list. It tells the "story" of a ticket at a glance.

---

### Enhancement 4 — Dashboard Stat Cards for Overdue & Unassigned
**File**: `templates/dashboard.html`  
**What**: Added prominently colored stat cards for SLA On Track, SLA Breached, Overdue, and Unassigned ticket counts.  
**Why**: These are the most actionable metrics for a support manager. They need to be front-and-center, not buried in charts.

---

### Enhancement 5 — Knowledge Base Navigation
**Files**: `templates/base.html`, `apps/tickets/web_urls.py`  
**What**: Added "Knowledge Base" link in the sidebar navigation. Created index (browse/search) and article detail templates.  
**Why**: The knowledge base needs to be easily discoverable from the main navigation for both agents (reference) and customers (self-service).

---

## Infrastructure & Security Improvements

### Logging Configuration
**File**: `config/settings/base.py`  
Added `LOGGING` configuration with:
- Console handler (INFO level)
- `RotatingFileHandler` for `django_error.log` (ERROR level, 5MB max, 5 backups)
- `RotatingFileHandler` for `django.log` (INFO level, 10MB max, 5 backups)

**Why**: Production systems need structured, rotated log files for monitoring, alerting, and post-incident analysis.

---

### Security Headers
**File**: `config/settings/base.py`  
Added:
- `SECURE_BROWSER_XSS_FILTER = True`
- `SECURE_CONTENT_TYPE_NOSNIFF = True`
- `X_FRAME_OPTIONS = 'DENY'`
- `CSRF_COOKIE_HTTPONLY = True`

**Why**: These are OWASP-recommended security headers that prevent XSS, MIME-type sniffing, and clickjacking attacks with zero performance cost.

---

### Role-Based Access Control (RBAC)
**File**: `apps/core/permissions.py`  
Created custom DRF permission classes:
- `IsPlatformAdmin` — platform-level superadmin
- `IsAdmin` — organization admin
- `IsManager` — organization manager
- `IsAgent` — organization agent
- `IsAdminOrManager` — admin or manager
- `IsAgentOrAdminOrManager` — any staff role

Applied across all viewsets for proper access control.  
**Why**: Multi-tenant systems must enforce strict role boundaries. Without RBAC, agents could modify organization settings and managers could access other tenants' data.

---

### WhiteNoise for Static Files
**File**: `config/settings/base.py`  
Added `whitenoise.middleware.WhiteNoiseMiddleware` to `MIDDLEWARE`.  
**Why**: Serves static files efficiently in production without requiring a separate web server (Nginx) configuration step.

---

## New API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/{company}/tickets/stats/` | Enhanced dashboard stats (SLA, trend, agents) |
| GET | `/api/{company}/tickets/recent-activity/` | Activity feed |
| POST | `/api/{company}/tickets/bulk-action/` | Bulk assign/close/priority/tag |
| GET | `/api/{company}/tickets/export/` | CSV export |
| POST | `/api/{company}/tickets/{id}/merge/` | Merge tickets |
| GET | `/api/{company}/tickets/{id}/watchers/` | List ticket watchers |
| POST | `/api/{company}/tickets/{id}/watch/` | Watch a ticket |
| DELETE | `/api/{company}/tickets/{id}/unwatch/` | Unwatch a ticket |
| GET | `/api/{company}/tickets/statuses/` | Available status choices |
| GET | `/api/{company}/tickets/priorities/` | Available priority choices |
| GET | `/api/{company}/tickets/types/` | Available type choices |
| CRUD | `/api/{company}/tags/` | Tag management |
| CRUD | `/api/{company}/sla-policies/` | SLA policy management |
| CRUD | `/api/{company}/canned-responses/` | Canned response management |
| CRUD | `/api/{company}/kb/categories/` | KB category management |
| CRUD | `/api/{company}/kb/articles/` | KB article management |
| POST | `/api/{company}/kb/articles/{id}/helpful/` | Mark article helpful/unhelpful |
| GET | `/api/{company}/audit-logs/` | Audit log viewer (admin only) |
| POST | `/api/{company}/auth/password-change/` | Change password |
| GET/PUT | `/api/{company}/auth/profile/` | User profile management |
| GET/PUT | `/api/{company}/auth/organization/settings/` | Org settings (admin only) |

---

## New Models Summary

| Model | Purpose |
|-------|---------|
| `Tag` | Colored labels for ticket categorization |
| `SLAPolicy` | Response/resolution time targets per priority |
| `TicketWatcher` | M2M through table for ticket watch subscriptions |
| `CannedResponse` | Pre-written reply templates for agents |
| `KBCategory` | Knowledge base article categories |
| `KBArticle` | Knowledge base articles with versioning |
| `AuditLog` | System-wide audit trail |

---

## Files Modified

| File | Changes |
|------|---------|
| `config/settings/base.py` | Logging, security headers, WhiteNoise, dedup middleware |
| `apps/core/views.py` | Fix `.extra()`, secure EnquiryViewSet |
| `apps/core/permissions.py` | **NEW** — RBAC permission classes |
| `apps/core/middleware/rate_limit.py` | Fix timing (process_view), add logging |
| `apps/core/middleware/tenant.py` | Replace print with logging |
| `apps/accounts/models.py` | Add `department_fk` FK |
| `apps/accounts/views.py` | Logging, RBAC, new profile/password views |
| `apps/accounts/serializers.py` | New serializers for profile/password/org settings |
| `apps/accounts/urls.py` | New URL patterns |
| `apps/accounts/platform_views.py` | IsPlatformAdmin permissions, logging |
| `apps/tickets/models.py` | Tag, SLAPolicy, Watcher, CannedResponse, KB, AuditLog models; Ticket enhancements |
| `apps/tickets/serializers.py` | State machine, SLA status, new model serializers |
| `apps/tickets/views.py` | Pagination, search, bulk ops, export, merge, watchers, KB, audit, stats |
| `apps/tickets/urls.py` | Register new viewsets |
| `apps/tickets/web_urls.py` | Knowledge base web routes |
| `apps/comments/models.py` | SET_NULL on user FK |
| `apps/notifications/signals.py` | status_changed, priority_changed, watchers |
| `static/js/api.js` | Fix addComment, add 25+ new API methods |
| `templates/dashboard.html` | SLA/overdue/unassigned cards, trend/type charts, agent leaderboard, activity feed |
| `templates/tickets/list.html` | Filters UI, bulk actions, export button, SLA badges |
| `templates/tickets/details.html` | SLA info, watchers, tags, merge modal, canned responses, timeline |
| `templates/tickets/create.html` | Type, source, due date, tags selectors |
| `templates/knowledge_base/index.html` | **NEW** — KB browse/search page |
| `templates/knowledge_base/article.html` | **NEW** — KB article detail page |
| `templates/base.html` | Knowledge Base nav link |
