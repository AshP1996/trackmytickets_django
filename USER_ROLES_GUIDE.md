# User Roles and Permissions - Demo Organization

## Overview

The ticket system has **4 user roles** with different permission levels. All users in the demo organization now have the password: `admin123`

## User Accounts

| Email | Password | Role | Access Level |
|-------|----------|------|--------------|
| admin@demo.com | admin123 | **Admin** | Full system access |
| manager@demo.com | admin123 | **Manager** | Department management |
| agent@demo.com | admin123 | **Agent** | Ticket handling |
| customer@demo.com | admin123 | **Customer** | Ticket creation only |

## Role Permissions

### 1. Admin (`admin@demo.com`)

**Full System Access** - Complete control over the organization

#### Can Access:
- ✅ **Dashboard**: View all statistics and charts
- ✅ **All Tickets**: View, create, edit, delete any ticket
- ✅ **Projects**: Create, edit, delete projects
- ✅ **Users**: Add, edit, deactivate users
- ✅ **Departments**: Create, edit departments
- ✅ **Settings**: Organization settings, integrations
- ✅ **Data Sources**: Configure external data sources
- ✅ **Reports**: Generate and export reports

#### Navigation Menu:
```
Dashboard
Tickets
  - All Tickets
  - My Tickets
  - Create Ticket
Projects
Admin
  - Users
  - Departments
  - Data Sources
  - Settings
```

#### Typical Use Cases:
- System configuration and setup
- User management
- Department structure
- Integration with external systems
- Viewing organization-wide analytics

---

### 2. Manager (`manager@demo.com`)

**Department Management** - Oversee team and tickets

#### Can Access:
- ✅ **Dashboard**: View department statistics
- ✅ **Department Tickets**: View all tickets in their department
- ✅ **Ticket Assignment**: Assign tickets to agents
- ✅ **Projects**: Create and manage projects
- ✅ **Team View**: See agents in their department
- ⚠️ **Limited Admin**: Can view users but not create/delete

#### Cannot Access:
- ❌ Organization settings
- ❌ Create/delete users
- ❌ Create/delete departments
- ❌ Data source configuration

#### Navigation Menu:
```
Dashboard
Tickets
  - Department Tickets
  - My Tickets
  - Create Ticket
Projects
Team
  - View Agents
  - Performance Metrics
```

#### Typical Use Cases:
- Assign tickets to team members
- Monitor team performance
- Create projects for department
- Review and approve ticket resolutions
- Track SLA compliance

---

### 3. Agent (`agent@demo.com`)

**Ticket Handling** - Respond to and resolve tickets

#### Can Access:
- ✅ **Dashboard**: View personal statistics
- ✅ **Assigned Tickets**: View tickets assigned to them
- ✅ **Department Tickets**: View tickets in their department
- ✅ **Create Tickets**: Create new tickets
- ✅ **Comments**: Add comments and updates
- ✅ **Status Updates**: Change ticket status
- ✅ **Projects**: View projects (read-only)

#### Cannot Access:
- ❌ Create/delete projects
- ❌ User management
- ❌ Department management
- ❌ Assign tickets to others (can only self-assign)
- ❌ Admin panel

#### Navigation Menu:
```
Dashboard
Tickets
  - My Tickets
  - Department Tickets
  - Create Ticket
Projects (View Only)
```

#### Typical Use Cases:
- Respond to assigned tickets
- Update ticket status
- Add internal notes
- Communicate with customers
- Self-assign available tickets

---

### 4. Customer (`customer@demo.com`)

**Ticket Creation** - Submit and track own tickets

#### Can Access:
- ✅ **My Tickets**: View only their own tickets
- ✅ **Create Ticket**: Submit new tickets
- ✅ **Comments**: Reply to their tickets
- ✅ **View Status**: Track ticket progress

#### Cannot Access:
- ❌ Other users' tickets
- ❌ Dashboard statistics
- ❌ Projects
- ❌ User list
- ❌ Department information
- ❌ Admin panel
- ❌ Assign or reassign tickets

#### Navigation Menu:
```
My Tickets
Create Ticket
```

#### Typical Use Cases:
- Submit support requests
- Track ticket status
- Provide additional information
- View responses from agents
- Reopen resolved tickets if needed

---

## Testing User Roles

### Manual Browser Testing

1. **Open browser** and navigate to: `http://localhost:9000/demo/login`

2. **Test each user** by logging in with their credentials:

#### Test Admin
```
Email: admin@demo.com
Password: admin123
```
- Navigate to Admin → Users (should see all users)
- Navigate to Admin → Departments (should see all departments)
- Navigate to Admin → Data Sources (should see data sources)
- Create a new project
- Create a new ticket

#### Test Manager
```
Email: manager@demo.com
Password: admin123
```
- Navigate to Dashboard (should see department stats)
- Navigate to Tickets (should see department tickets)
- Try to access Admin → Users (should have limited access)
- Create a project
- Assign a ticket to an agent

#### Test Agent
```
Email: agent@demo.com
Password: admin123
```
- Navigate to Dashboard (should see personal stats)
- Navigate to My Tickets (should see assigned tickets)
- Try to create a project (should fail)
- Try to access Admin panel (should be denied)
- Create a ticket
- Update ticket status

#### Test Customer
```
Email: customer@demo.com
Password: admin123
```
- Navigate to My Tickets (should see only own tickets)
- Create a new ticket
- Try to access other sections (should be denied)
- Add a comment to own ticket
- Try to view another user's ticket (should fail)

---

## Permission Matrix

| Feature | Admin | Manager | Agent | Customer |
|---------|-------|---------|-------|----------|
| **View Dashboard** | ✅ All | ✅ Dept | ✅ Personal | ❌ |
| **View All Tickets** | ✅ | ✅ Dept | ✅ Dept | ❌ |
| **View Own Tickets** | ✅ | ✅ | ✅ | ✅ |
| **Create Ticket** | ✅ | ✅ | ✅ | ✅ |
| **Edit Any Ticket** | ✅ | ✅ Dept | ❌ | ❌ |
| **Delete Ticket** | ✅ | ⚠️ Limited | ❌ | ❌ |
| **Assign Tickets** | ✅ | ✅ | ⚠️ Self | ❌ |
| **Create Project** | ✅ | ✅ | ❌ | ❌ |
| **Edit Project** | ✅ | ✅ Own | ❌ | ❌ |
| **Delete Project** | ✅ | ⚠️ Limited | ❌ | ❌ |
| **View Users** | ✅ | ✅ | ⚠️ Limited | ❌ |
| **Create User** | ✅ | ❌ | ❌ | ❌ |
| **Edit User** | ✅ | ❌ | ❌ | ❌ |
| **Delete User** | ✅ | ❌ | ❌ | ❌ |
| **View Departments** | ✅ | ✅ | ✅ | ❌ |
| **Create Department** | ✅ | ❌ | ❌ | ❌ |
| **Edit Department** | ✅ | ❌ | ❌ | ❌ |
| **Configure Data Sources** | ✅ | ❌ | ❌ | ❌ |
| **View Reports** | ✅ | ✅ Dept | ⚠️ Personal | ❌ |
| **Export Data** | ✅ | ✅ Dept | ❌ | ❌ |

**Legend:**
- ✅ = Full access
- ⚠️ = Limited/Partial access
- ❌ = No access

---

## API Endpoints by Role

### Admin Endpoints
```
GET    /api/demo/users/              - List all users
POST   /api/demo/users/              - Create user
PATCH  /api/demo/users/{id}/         - Update user
DELETE /api/demo/users/{id}/         - Delete user
GET    /api/demo/departments/        - List departments
POST   /api/demo/departments/        - Create department
GET    /api/demo/data-sources/       - List data sources
POST   /api/demo/data-sources/       - Create data source
```

### Manager Endpoints
```
GET    /api/demo/tickets/            - List department tickets
POST   /api/demo/tickets/            - Create ticket
PATCH  /api/demo/tickets/{id}/       - Update ticket
GET    /api/demo/projects/           - List projects
POST   /api/demo/projects/           - Create project
GET    /api/demo/users/              - List users (read-only)
```

### Agent Endpoints
```
GET    /api/demo/tickets/            - List assigned/dept tickets
POST   /api/demo/tickets/            - Create ticket
PATCH  /api/demo/tickets/{id}/       - Update assigned tickets
GET    /api/demo/projects/           - List projects (read-only)
POST   /api/demo/tickets/{id}/comments/ - Add comments
```

### Customer Endpoints
```
GET    /api/demo/tickets/            - List own tickets only
POST   /api/demo/tickets/            - Create ticket
GET    /api/demo/tickets/{id}/       - View own ticket
POST   /api/demo/tickets/{id}/comments/ - Comment on own ticket
```

---

## Security Notes

> [!IMPORTANT]
> **Password Security**
> - All demo users currently have the same password: `admin123`
> - In production, enforce strong password policies
> - Require password changes on first login
> - Implement password expiration

> [!WARNING]
> **Role-Based Access Control (RBAC)**
> - Permissions are enforced at the API level
> - Frontend hides inaccessible features but doesn't enforce security
> - Always validate permissions on the backend
> - Log all permission-denied attempts

> [!CAUTION]
> **Customer Data Isolation**
> - Customers can ONLY see their own tickets
> - This is enforced by filtering tickets by `sender_email`
> - Never expose other customers' data
> - Audit customer data access regularly

---

## Next Steps

1. **Test in Browser**: Login with each user and verify permissions
2. **Check Navigation**: Ensure menu items match role permissions
3. **Test API**: Use browser DevTools to verify API responses
4. **Review Logs**: Check for any permission errors

**All users are ready to test with password: `admin123`**
