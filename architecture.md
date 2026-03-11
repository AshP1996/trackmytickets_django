# Multi-Tenant Ticket System Architecture

This document outlines the core architecture of the Multi-Tenant Enterprise Support Desk, specifically focusing on how the Database, Organizations, Multi-tenancy, Tickets, Comments, Notifications, and Users interact.

## 1. Multi-Tenant Architecture (Bring Your Own Database)

The system is designed around a **Data Sovereignty** model. Instead of storing all tenants' data in a single massive database with Foreign Key filters (logical isolation), this system uses **Physical Isolation (BYODB)** for ticket data.

### How it works:
1. **Primary Database (`db.sqlite3` / Default DB):** 
   - Stores global configurations, super-admins (Platform Admins), and the `Organization` catalog.
   - Stores the active `ExternalDataSource` credentials for each organization.
   - For demo accounts or orgs without external databases, it serves as the fallback storage.
2. **Tenant Databases:**
   - When a request comes in (e.g., to `/api/acme/tickets/`), the system parses `acme`.
   - The `TenantMiddleware` securely looks up the `Organization` where `subdomain='acme'`.
   - It queries the `ExternalDataSource` table to see if Acme has connected an external PostgreSQL/MySQL database.
   - If connected and active, the middleware registers a dynamic DB alias (`tenant_<id>`) and uses Python `ContextVar` to securely route **all subsequent queries** in that request to Acme's private database.
   - Tenant data never shares a table with another tenant.

### Visual Architecture Flow

```mermaid
graph TD
    Client -->|HTTPS Request: /api/acme/*| Nginx
    Nginx -->|Proxy Pass| Gunicorn[Gunicorn / Django WSGI]
    
    subgraph Django Config
        Gunicorn --> Routing[TenantMiddleware]
    end

    subgraph Default Database
        Routing -->|Lookup 'acme'| PrimaryDB[(Primary DB: core, accounts)]
    end

    subgraph Bring-Your-Own-DB Routing
        PrimaryDB -.->|Returns DB config| Routing
        Routing -->|ContextVar Alias| ContextRouter{Database Router}
    end

    subgraph Tenant Databases
        ContextRouter -->|Routes Query| Tenant1DB[(Acme Corp DB: tickets)]
        ContextRouter -->|Routes Query| Tenant2DB[(Stark Ind DB: tickets)]
        ContextRouter -->|Fallback| PrimaryDB
    end

    style Routing fill:#f9f,stroke:#333,stroke-width:2px
    style ContextRouter fill:#bbf,stroke:#333,stroke-width:2px
```

---

## 2. Organizations & Users Hierarchy

Organizations are the top-level entity. Every User belongs directly to one Organization.

- **Organizations:** Define the subdomain (`testorg`), branding, subscription plan, and limits.
- **Departments (Optional):** Sub-divisions within an organization (e.g., "IT Support", "HR"). Departments have `default_assignees` to auto-route incoming tickets.
- **Projects:** Logical groupings of tickets (e.g., "Website Redesign").
- **Users:**
  - `admin`: Has full control over the Organization settings, Departments, Projects, and can see all tickets.
  - `manager`: Can manage Projects and oversee all tickets.
  - `department_head`: Oversees a specific department and its statistics.
  - `agent`: Standard support agent. Can only act on assigned tickets or view tickets within their Project restrictions.

```mermaid
erDiagram
    Organization ||--o{ User : "has many"
    Organization ||--o{ Department : "has many"
    Organization ||--o{ Project : "has many"
    Department ||--o{ User : "can belong to"
    User ||--o{ Ticket : "assigned to / creates"
```

---

## 3. Tickets, Comments, and Notifications

The core workflow engine revolves around the `Ticket` model.

### Tickets
Tickets are bound to an Organization and optionally to a `Project` and/or `Department`. 
- **Fields:** Subject, Description, Status (`open`, `in_progress`, `resolved`, `closed`), Priority, and Due Date.
- **SLA Engine:** Tickets automatically track First Response Time and Resolution Time against the configured `SLAPolicy`.
- **Merging & Linking:** Tickets can be merged together to handle duplicate submissions.

### Comments
Comments represent the conversation thread of a ticket.
- **Public Comments:** Visible to the customer/creator.
- **Internal Notes:** Private remarks visible only to `agents`, `managers`, and `admins`. Used for backend coordination.
- **Attachments:** Both tickets and comments support multiple file attachments, securely stored in tenant-isolated AWS S3 prefixes or local media folders.

### Notifications
The system uses an asynchronous event-driven approach. 
When a ticket is updated or commented on, signals trigger Celery workers.
- **Models:** Records of unread/read alerts tracking State Changes (e.g., "Ticket Assigned to You", "SLA Breached").
- **Delivery:** Notifications run primarily in-app via the API (`/api/{org}/notifications/`), but the architecture supports modular Email and WebSocket delivery extensions.

### Entity Relationship Walkthrough

```mermaid
erDiagram
    Project ||--o{ Ticket : "contains"
    Department ||--o{ Ticket : "routes to"
    
    Ticket ||--o{ Comment : "has thread"
    Ticket ||--o{ Attachment : "has files"
    Ticket ||--o{ TicketHistory : "audit logs"
    Ticket ||--o{ TicketWatcher : "subscribed users"
    
    Comment ||--o{ Attachment : "has files"
    Comment }|--|| User : "authored by"
    
    Notification }|--|| User : "alerts"
    Notification }|--|| Ticket : "references"
```

---

## 4. System Interactions

1. **Inbound Request:** The user hits `/api/testorg/tickets/`.
2. **Authentication:** The JWT token is validated. The token contains an `org_id` claim, ensuring tokens from `acme` cannot be used on `testorg` URLs (Cross-Tenant Replay Protection).
3. **Database Routing:** TenantMiddleware identifies `testorg`. If a custom DB is connected, it locks the query stream to that specific DB.
4. **Authorization:** Drf permissions (`IsOrgMember`) ensure the User's database record matches the URL organization context.
5. **Business Logic:** The `TicketViewSet` executes the query. Due to N+1 optimizations, it uses `select_related` and `prefetch_related` to fetch the Ticket, its Assignee (User), and Tags in just 2 queries.
6. **Outbound Notification:** If the action was creating a ticket, Django Signals fire asynchronously via Redis/Celery to insert a new `Notification` row for the assigned user, completely decoupled from the HTTP response time.

---

## 5. Detailed End-to-End Request Flow

The following sequence diagram illustrates the lifecycle of a ticket creation request traversing through Nginx, Authentication, the Tenant Data router, Business Logic, and firing asynchronous SLA/Notification background tasks.

```mermaid
sequenceDiagram
    autonumber
    actor User as Support Agent
    participant Nginx as Nginx / WAF
    participant Auth as JWT Authentication
    participant Middleware as TenantMiddleware
    participant Router as DB Context Router
    participant View as TicketViewSet (API)
    participant PrimaryDB as Primary Database (sqlite)
    participant TenantDB as Tenant Database (pg/mysql)
    participant Celery as Celery / Redis
    
    User->>Nginx: POST /api/testorg/tickets/ (Token)
    Nginx->>Auth: Forward Request

    %% Authentication Phase
    note over Auth: Verifies JWT validity and org scope
    Auth->>Auth: Decode Token
    alt Invalid Token / Wrong Org Scope
        Auth-->>User: 401 / 403 Forbidden
    end
    
    Auth->>Middleware: Pass Authenticated Request
    
    %% Multi-Tenant Resolution Phase
    note over Middleware: Determines correct database for org
    Middleware->>PrimaryDB: SELECT * FROM organizations WHERE subdomain='testorg'
    PrimaryDB-->>Middleware: <Organization object>
    
    Middleware->>PrimaryDB: SELECT * FROM external_data_sources WHERE is_active=True
    PrimaryDB-->>Middleware: <External DB Credentials if any>
    
    alt BYODB Connected
        Middleware->>Router: set_current_db_alias('tenant_XYZ')
    else No External DB
        Middleware->>Router: set_current_db_alias('default')
    end
    
    %% Business Logic Phase
    Middleware->>View: Execute View Logic
    View->>TenantDB: SELECT * FROM users WHERE id=AssigneeID
    TenantDB-->>View: <User data>
    View->>TenantDB: INSERT INTO tickets (Subject, Priority...)
    TenantDB-->>View: <Ticket Created>
    
    %% Asynchronous Processing Phase
    View->>Celery: Trigger post_save signal (Async Task)
    
    %% Return to Client
    View-->>Middleware: HttpResponse (201 Created)
    Middleware-->>Auth: 
    Auth-->>Nginx: 
    Nginx-->>User: JSON Response (Ticket Data)

    %% Background Jobs running concurrently
    par Background Tasks
        Celery->>TenantDB: Calculate SLA (Resolution Deadline)
        TenantDB-->>Celery: Update Ticket SLA fields
        Celery->>TenantDB: INSERT INTO notifications (Alert Assignee)
        celery-->>Celery: Send Email (SMTP)
    end
```
