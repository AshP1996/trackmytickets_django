# Flask to Django Migration Guide

This guide details the steps to run the migrated Django application.

## Prerequisites
- Python 3.10+
- PostgreSQL (for production)
- SQLite (for development)

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Create a `.env` file in `ticket_system_django/` or set environment variables:
   ```bash
   DJANGO_SECRET_KEY=your-secret-key
   DEBUG=True (or False)
   DATABASE_URL=postgres://user:pass@host:port/dbname (optional override)
   ```

3. **Database Initialization**
   ```bash
   python manage.py migrate
   ```

## Running the Application

### Development
```bash
python manage.py runserver
```

### Production
Use Gunicorn or uWSGI:
```bash
gunicorn config.wsgi:application
```

## Application Structure

The project has been restructured from Flask Blueprints to Django Apps:

| Flask Blueprint | Django App | Notes |
|-----------------|------------|-------|
| `auth`, `admin` | `apps.accounts` | User management, Auth, Roles, Organizations |
| `tickets`, `projects` | `apps.tickets` | Ticket CRUD, Projects, Workflow |
| `comments` | `apps.comments` | Ticket comments |
| `notifications` | `apps.notifications` | User notifications |
| `views`, `data_sources` | `apps.core` | Landing pages, Shared utils |

## Key Changes
- **Database**: Models have been converted to Django ORM. `User` model now handles multi-tenancy uniqueness via application logic (email unique per organization).
- **Authentication**: Uses `SimpleJWT` for API authentication.
- **Multi-tenancy**: Implemented via `TenantMiddleware`. Organization context is resolved from URL path (e.g., `/api/<company_name>/...`) or subdomain (optional).
- **Templates**: Flask templates have been migrated to `templates/` directory and are served via `TemplateView`s matching original routes.

## Verification
To verify the installation:
1. Run migrations: `python manage.py migrate`
2. Create a superuser: `python manage.py createsuperuser`
3. Start server: `python manage.py runserver`
4. Access `http://localhost:8000/` to see Landing Page.
5. Create an organization via Django Admin or Shell.

## API Documentation
The API behavior matches the Flask application.
- Auth: `/api/<company>/auth/login`
- Tickets: `/api/<company>/tickets`
