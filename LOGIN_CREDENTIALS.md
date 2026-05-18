# TrackMyTickets - Login Credentials

##  Production Server (HTTPS - Secure)

**Domain**: https://trackmytickets.in  
**Server IP**: 72.60.101.189  
**SSL**:  Enabled (Let's Encrypt)

---

##  Platform Admin Login

**URL**: https://trackmytickets.in/platform/login

| Role | Email | Password |
|------|-------|----------|
| Platform Super Admin | `superadmin@platform.com` | `Admin@2026` |
| Platform Admin | `admin@platform.com` | `Admin@2026` |

**Dashboard**: https://trackmytickets.in/platform/dashboard

**Features**:
- Create and manage organizations
- View all enquiries from landing page
- View platform-wide statistics
- Manage organization subscriptions

---

##  Organization Logins

### Demo Organization
**URL**: https://trackmytickets.in/demo/login

| Role | Email | Password | Status |
|------|-------|----------|--------|
| Admin | `admin@demo.com` | `Admin@2026` | ✅ Verified |
| Agent | `testagent1@demo.com` | _(set via admin)_ | Active |
| Agent | `testmanager1@demo.com` | _(set via admin)_ | Active |
| Agent | `testuser999@demo.com` | _(set via admin)_ | Active |

**Admin Dashboard**: https://trackmytickets.in/demo/admin/dashboard  
**User Dashboard**: https://trackmytickets.in/demo/dashboard  
**Tickets**: https://trackmytickets.in/demo/tickets  
**Data Sources**: https://trackmytickets.in/demo/admin/data-sources  
**Reports**: https://trackmytickets.in/demo/admin/reports

### TechFlow Organization
**URL**: https://trackmytickets.in/techflow/login

| Role | Email | Password |
|------|-------|----------|
| Marketing Manager | `head.marketing@techflow.com` | `password123` |
| Support Agent 1 | `agent.support1@techflow.com` | `password123` |
| Customer 1 | `customer1@client.com` | `password123` |

*Note: 6 Dept Heads, 5 Agents, and 10 Customers created.*

---

##  Password Reset (OTP via Email)

### Platform Admin Password Reset
**Forgot Password**: https://trackmytickets.in/platform/api/forgot-password

**API Request**:
```bash
curl -X POST https://trackmytickets.in/platform/api/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@trackmytickets.in"}'
```

**Reset Password**: https://trackmytickets.in/platform/api/reset-password

**API Request**:
```bash
curl -X POST https://trackmytickets.in/platform/api/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@trackmytickets.in",
    "otp": "123456",
    "new_password": "NewPassword@2026"
  }'
```

### Organization User Password Reset
**Forgot Password**: https://trackmytickets.in/{company}/api/forgot-password/

**Example (Demo)**:
```bash
curl -X POST https://trackmytickets.in/demo/api/forgot-password/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@demo.com"}'
```

**Reset Password**: https://trackmytickets.in/{company}/api/reset-password/

**Example (Demo)**:
```bash
curl -X POST https://trackmytickets.in/demo/api/reset-password/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@demo.com",
    "otp": "123456",
    "new_password": "newpassword123"
  }'
```

**OTP Details**:
- OTP sent to: ash894173@gmail.com
- OTP expires in: 15 minutes
- OTP length: 6 digits

---

##  Email Configuration

**SMTP Server**: smtp.gmail.com  
**SMTP Port**: 587  
**Email**: ash894173@gmail.com  
**Use for**: Password reset OTPs, notifications

---

##  Local Development Server

**URL**: http://127.0.0.1:9000

### Platform Admin Login (Local)
**URL**: http://127.0.0.1:9000/platform/login

| Role | Email | Password |
|------|-------|----------|
| Platform Admin | `admin@trackmytickets.in` | `Admin@2026` |

### Demo Organization (Local)
**URL**: http://127.0.0.1:9000/demo/login

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@demo.com` | `password123` |
| Department Head (IT) | `head.it@demo.com` | `password123` |
| Department Head (HR) | `head.hr@demo.com` | `password123` |
| Department Head (Sales) | `head.sales@demo.com` | `password123` |
| Department Head (Support) | `head.support@demo.com` | `password123` |
| Department Head (Finance) | `head.finance@demo.com` | `password123` |
| Department Head (Marketing) | `head.marketing@demo.com` | `password123` |
| Agent (IT) | `agent.it1@demo.com` | `password123` |
| Agent (Support) | `agent.support1@demo.com` | `password123` |
| Customer | `customer1@client.com` | `password123` |

**Admin Dashboard**: http://127.0.0.1:9000/demo/admin/dashboard  
**User Dashboard**: http://127.0.0.1:9000/demo/dashboard  
**Tickets**: http://127.0.0.1:9000/demo/tickets  
**Data Sources**: http://127.0.0.1:9000/demo/admin/data-sources  
**Reports**: http://127.0.0.1:9000/demo/admin/reports

### TechFlow Organization (Local)
**URL**: http://127.0.0.1:9000/techflow/login

| Role | Email | Password |
|------|-------|----------|
| Marketing Manager | `head.marketing@techflow.com` | `password123` |
| Support Agent 1 | `agent.support1@techflow.com` | `password123` |
| Customer 1 | `customer1@client.com` | `password123` |

---

##  Notes

### URL Structure
- **Platform**: `https://trackmytickets.in/platform/<page>`
- **Organization**: `https://trackmytickets.in/<company_subdomain>/<page>`
- **Demo Subdomain**: `demo`
- **TechFlow Subdomain**: `techflow`

### Default Password
All test accounts use: `password123`

### Security
-  HTTPS enabled with Let's Encrypt SSL
-  Secure cookies enabled
-  CSRF protection enabled
-  Password reset via OTP
-  Auto-renewal for SSL certificate

### Server Access
**SSH**: `ssh root@72.60.101.189`  
**Application Path**: `/var/www/trackmytickets/ticket_system_django`  
**Logs**: `/var/www/trackmytickets/logs/`

---

##  Quick Access Links

### Production (HTTPS - Secure)
-  **Landing Page**: https://trackmytickets.in
-  **Platform Login**: https://trackmytickets.in/platform/login
-  **Demo Login**: https://trackmytickets.in/demo/login
-  **TechFlow Login**: https://trackmytickets.in/techflow/login

### Local Development
-  **Landing Page**: http://127.0.0.1:9000
-  **Platform Login**: http://127.0.0.1:9000/platform/login
-  **Demo Login**: http://127.0.0.1:9000/demo/login
-  **TechFlow Login**: http://127.0.0.1:9000/techflow/login

---

##  Database Credentials

### Production PostgreSQL
**Host**: localhost  
**Port**: 5432  
**Database**: trackmytickets  
**User**: ticketuser  
**Password**: TrackMyTickets2026!

**Access**:
```bash
ssh root@72.60.101.189
sudo -u postgres psql trackmytickets
```

### Local SQLite
**Database**: `db.sqlite3`  
**Location**: `/home/ashish/Documents/ticket_system_v1/ticket_system_django/db.sqlite3`

---

##  Environment Variables

### Production (.env location)
`/var/www/trackmytickets/.env`

### Local (.env location)
`/home/ashish/Documents/ticket_system_v1/ticket_system_django/.env`

---

## 📱 API Endpoints

### Platform API
- **Login**: `POST https://trackmytickets.in/platform/api/login`
- **Me**: `GET https://trackmytickets.in/platform/api/me`
- **Organizations**: `GET/POST https://trackmytickets.in/platform/api/organizations`
- **Stats**: `GET https://trackmytickets.in/platform/api/stats`
- **Enquiries**: `GET https://trackmytickets.in/platform/api/enquiries`
- **Forgot Password**: `POST https://trackmytickets.in/platform/api/forgot-password`
- **Reset Password**: `POST https://trackmytickets.in/platform/api/reset-password`

### Organization API
- **Login**: `POST https://trackmytickets.in/{company}/api/login`
- **Register**: `POST https://trackmytickets.in/{company}/api/register`
- **Me**: `GET https://trackmytickets.in/{company}/api/me`
- **Users**: `GET https://trackmytickets.in/{company}/api/users`
- **Forgot Password**: `POST https://trackmytickets.in/{company}/api/forgot-password/`
- **Reset Password**: `POST https://trackmytickets.in/{company}/api/reset-password/`

---

**Last Updated**: February 10, 2026  
**SSL Certificate Expiry**: May 10, 2026 (Auto-renewal enabled)
