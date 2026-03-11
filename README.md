# TrackMyTicket — Multi-Tenant Ticket System

Django-based multi-tenant SaaS for ticket management. Supports platform admin, organizations (tenants), departments, projects, and role-based access.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Option A: Run with Docker (recommended)](#option-a-run-with-docker-recommended)
- [Option B: Run locally (Python + SQLite)](#option-b-run-locally-python--sqlite)
- [Access URLs & default credentials](#access-urls--default-credentials)
- [Common commands](#common-commands)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **For Docker**: [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- **For local run**: Python 3.10+, pip, and (optional) virtualenv

---

## Option A: Run with Docker (recommended)

### Step 1: Clone and enter the project

```bash
git clone <repository-url>
cd ticket_system_django
```

### Step 2: Create environment file

```bash
cp .env.example .env
```

Edit `.env` and set at least:

- `SECRET_KEY` — generate with:
  ```bash
  python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- `DB_CREDENTIALS_ENCRYPTION_KEY` — generate with:
  ```bash
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- `DB_PASSWORD` — use a strong password (default in compose: `TrackMyTickets2026!`)

Optional for email: `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`.

### Step 3: Build and start services

```bash
docker-compose up -d
```

This starts: PostgreSQL, Redis, PgBouncer, Django (Gunicorn), Celery, and Nginx.

### Step 4: Run migrations

```bash
docker-compose exec web python manage.py migrate
```

### Step 5: Create platform admin (optional)

```bash
docker-compose exec web python manage.py shell -c "
from apps.accounts.models import PlatformAdmin
if not PlatformAdmin.objects.filter(email='admin@platform.com').exists():
    PlatformAdmin.objects.create_superuser('admin@platform.com', 'password')
    print('Platform admin created.')
else:
    print('Platform admin already exists.')
"
```

### Step 6: Seed demo organization and data (optional)

```bash
docker-compose exec web python scripts/setup_demo_data.py
docker-compose exec web python scripts/populate_demo_org.py
```

### Step 7: Open the application

- **App (via Nginx)**: http://localhost:8080  
- **Platform login**: http://localhost:8080/platform/login  
- **Demo tenant login**: http://localhost:8080/demo/login  

Default credentials are in [Access URLs & default credentials](#access-urls--default-credentials) below.

---

## Option B: Run locally (Python + SQLite)

Use this for quick local development without Docker.

### Step 1: Clone and enter the project

```bash
git clone <repository-url>
cd ticket_system_django
```

### Step 2: Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Create `.env` and set required variables

```bash
cp .env.example .env
```

Edit `.env` (or export in the shell). **Required:**

```bash
# Required by config.settings.base
export DB_CREDENTIALS_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# Allow local dev server
export ALLOWED_HOSTS=localhost,127.0.0.1
export DEBUG=True
```

Or add the same to `.env` (with no `export`) and ensure your shell loads `.env`, or use `python-dotenv` (already in requirements; base settings load it).

### Step 5: Run migrations

```bash
python manage.py migrate
```

### Step 6: Create platform admin and demo data (optional)

```bash
python scripts/setup_manual_test_data.py
python scripts/setup_demo_data.py
python scripts/populate_demo_org.py
```

### Step 7: Start the development server

```bash
python manage.py runserver 0.0.0.0:8000
```

### Step 8: Open the application

- **App**: http://localhost:8000  
- **Platform login**: http://localhost:8000/platform/login  
- **Demo tenant login**: http://localhost:8000/demo/login  

---

## Access URLs & default credentials

After running either **Option A** or **Option B** and seeding data:

| Role            | Login URL (Docker: 8080 / Local: 8000) | Email                | Password   |
|-----------------|----------------------------------------|----------------------|------------|
| Platform Admin  | `http://localhost:8080/platform/login` or `...8000/platform/login` | `admin@platform.com` | `password` |
| Demo Org Admin  | `http://localhost:8080/demo/login` or `...8000/demo/login`        | `admin@demo.com`     | `password` |
| Demo Agent      | Same as Demo Org                       | `agent@demo.com`     | `password` |

- **Platform admin**: manage organizations, create tenants.  
- **Tenant (e.g. demo)**: dashboard, tickets, projects, admin (users, departments, reports).

If you use **Docker**, replace port `8000` with `8080` in the table above.

---

## Common commands

### Docker

```bash
# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild and start
docker-compose build && docker-compose up -d

# Run Django management command
docker-compose exec web python manage.py <command>

# Shell
docker-compose exec web python manage.py shell
```

### Local (no Docker)

```bash
# Run server
python manage.py runserver 0.0.0.0:8000

# Migrations
python manage.py migrate
python manage.py makemigrations <app_name>

# Create superuser (platform admin)
python manage.py shell
# Then use PlatformAdmin.objects.create_superuser(...) as in Step 5 of Option A
```

---

## Environment variables

| Variable                      | Required | Description |
|------------------------------|----------|-------------|
| `SECRET_KEY`                 | Yes (prod) | Django secret key. |
| `DB_CREDENTIALS_ENCRYPTION_KEY` | Yes | Fernet key for encrypting DB credentials (generate with `Fernet.generate_key()`). |
| `ALLOWED_HOSTS`              | Yes (local) | Comma-separated hosts, e.g. `localhost,127.0.0.1`. |
| `DEBUG`                      | No | Set `True` for local development only. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | For Docker / Postgres | Database connection. |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | No | For sending email (e.g. notifications). |

See `.env.example` for more options.

---

## Troubleshooting

### Docker: containers won’t start

```bash
docker-compose logs
docker-compose down -v
docker-compose up -d
```

### Docker: database or migrations

```bash
docker-compose exec web python manage.py migrate
docker-compose restart db
```

### Docker: static files

```bash
docker-compose exec web python manage.py collectstatic --noinput
```

### Local: “DB_CREDENTIALS_ENCRYPTION_KEY” missing

Set the env var (or add to `.env`) and ensure `.env` is loaded. Generate with:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Local: “Invalid HTTP_HOST” or connection refused

Set `ALLOWED_HOSTS=localhost,127.0.0.1` and use `http://localhost:8000` (or the host/port you use).

### Logins fail or “Invalid credentials”

- Ensure migrations are applied and demo data is loaded (`setup_demo_data.py`, `populate_demo_org.py`).
- Use the URLs and credentials from [Access URLs & default credentials](#access-urls--default-credentials).
- For Docker, use port **8080**; for local runserver, use **8000**.

---

## Production deployment

For production (HTTPS, scaling, backups), see [DEPLOYMENT.md](DEPLOYMENT.md) if present, or deploy the same stack (Django + Gunicorn, Nginx, Postgres, Redis, Celery) with your own orchestration and secrets.
