# Quick Start Guide

## Local Development with Docker

### 1. Prerequisites
- Docker and Docker Compose installed
- Git

### 2. Clone and Setup

```bash
git clone <repo-url>
cd ticket_system_django

# Copy environment file
cp .env.example .env.local

# Generate keys
python3 -c "from django.core.management.utils import get_random_secret_key; print('SECRET_KEY=' + get_random_secret_key())" >> .env.local
python3 -c "from cryptography.fernet import Fernet; print('DB_CREDENTIALS_ENCRYPTION_KEY=' + Fernet.generate_key().decode())" >> .env.local
```

### 3. Start Services

```bash
# Build and start
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Load demo data
docker-compose exec web python scripts/setup_demo_data.py
docker-compose exec web python scripts/populate_demo_org.py
```

### 4. Access Application

- **Application**: http://localhost
- **Admin**: http://localhost/admin/
- **Demo Login**: http://localhost/demo/login
  - Email: admin@demo.com
  - Password: admin123

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed production deployment instructions.

### Quick Production Deploy

```bash
# On your server
cd /opt
git clone <repo-url> ticket_system
cd ticket_system/ticket_system_django

# Configure
cp .env.example .env
nano .env  # Fill in production values

# Deploy
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

## Common Commands

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild
docker-compose build

# Run Django command
docker-compose exec web python manage.py <command>

# Backup database
./scripts/backup.sh

# Access database
docker-compose exec db psql -U postgres ticket_system
```

## Environment Variables

Key variables to set in `.env`:

```env
SECRET_KEY=<generate-with-django>
DB_PASSWORD=<strong-password>
DB_CREDENTIALS_ENCRYPTION_KEY=<generate-with-fernet>
EMAIL_HOST_USER=<your-email>
EMAIL_HOST_PASSWORD=<app-password>
```

## Troubleshooting

### Containers won't start
```bash
docker-compose logs
docker-compose down -v  # Remove volumes
docker-compose up -d
```

### Database issues
```bash
docker-compose exec web python manage.py migrate
docker-compose restart db
```

### Static files not loading
```bash
docker-compose exec web python manage.py collectstatic --noinput
docker-compose restart nginx
```

For more help, see [DEPLOYMENT.md](DEPLOYMENT.md)
