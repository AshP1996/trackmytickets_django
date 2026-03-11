## Local Login URLs & Credentials

This file documents **known-good local URLs and credentials** for your current `db.sqlite3`.  
All URLs assume the dev server is running on `http://localhost:8000`.

> If logins fail, **restart the Django dev server** so it uses the latest code and DB state:
> ```bash
> cd /home/ashish/Documents/ticket_system_v1/ticket_system_django
> python manage.py runserver 8000
> ```

---

### 1. Platform Admin (global)

- **Login URL**:  
  `http://localhost:8000/platform/login`

- **Credentials**:

  | Email                | Password |
  |----------------------|----------|
  | `admin@platform.com` | `password` |

This account is stored in the `platform_admins` table and was (re)created by `scripts/setup_manual_test_data.py`.

Once logged in:

- **Platform dashboard**: `http://localhost:8000/platform/dashboard`
- You can create and manage organizations from the platform UI.

---

### 2. Demo Organization (`demo`)

The demo organization uses subdomain **`demo`**.

#### 2.1. Admin (Org-level)

- **Login URL**:  
  `http://localhost:8000/demo/login`

- **Credentials**:

  | Email             | Password |
  |-------------------|----------|
  | `admin@demo.com`  | `password` |

- **Key pages after login**:
  - Admin dashboard: `http://localhost:8000/demo/admin/dashboard`
  - User dashboard: `http://localhost:8000/demo/dashboard`
  - Tickets list: `http://localhost:8000/demo/tickets`
  - Departments: `http://localhost:8000/demo/admin/departments`
  - Users: `http://localhost:8000/demo/admin/users`

#### 2.2. Agent

- **Login URL**:  
  `http://localhost:8000/demo/login`

- **Credentials**:

  | Email             | Password |
  |-------------------|----------|
  | `agent@demo.com`  | `password` |

This agent account belongs to the `demo` organization and is allowed to:

- View assigned tickets
- Add comments
- Update ticket status (according to role permissions)

---

### 3. Notes / Troubleshooting

1. **If you see “Invalid credentials” for the platform admin**:
   - Make sure you are on `http://localhost:8000/platform/login` (not a tenant login).
   - Use `admin@platform.com` / `password` exactly (lowercase email, password is literally `password`).

2. **If you see “Invalid credentials” for the demo org**:
   - Ensure you are on `http://localhost:8000/demo/login`.
   - Use `admin@demo.com` / `password` or `agent@demo.com` / `password`.
   - If you recently changed DB schema or demo scripts, restart the dev server and try again.

3. **If you hit an error page mentioning `no such table: users`**:
   - That means a tenant DB alias was pointing at a BYODB SQLite file without migrations.
   - Fix: disable external data sources for local dev and restart the server:
     ```bash
     cd /home/ashish/Documents/ticket_system_v1/ticket_system_django
     python manage.py shell <<'PY'
     from apps.core.models import ExternalDataSource
     ExternalDataSource.objects.all().update(is_active=False, connection_status='untested')
     print("Disabled all external data sources for local dev")
     PY
     python manage.py runserver 8000
     ```

4. **To inspect current users for an org** (optional):
   ```bash
   cd /home/ashish/Documents/ticket_system_v1/ticket_system_django
   python manage.py shell <<'PY'
   from apps.accounts.models import User, Organization
   org = Organization.objects.get(subdomain='demo')
   print(list(User.objects.all().values('id','email','role')))
   PY
   ```

