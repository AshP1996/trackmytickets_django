# Docker Deployment Guide - TrackMyTickets

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- `.env` file configured (copy from `.env.docker` template)

### 1. Configure Environment Variables

Copy the template and edit with your values:
```bash
cp .env.docker .env
# Edit .env with your actual values
```

### 2. Build and Start Services

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 3. Run Migrations and Create Admin

```bash
# Run database migrations
docker-compose exec web python manage.py migrate

# Create platform admin
docker-compose exec web python manage.py shell <<EOF
from apps.accounts.models import PlatformAdmin
from django.contrib.auth.hashers import make_password

if not PlatformAdmin.objects.filter(email='admin@trackmytickets.in').exists():
    PlatformAdmin.objects.create(
        email='admin@trackmytickets.in',
        password=make_password('Admin@2026')
    )
    print("Platform admin created successfully")
else:
    print("Platform admin already exists")
EOF
```

### 4. Access the Application

- **Main Site**: http://localhost
- **Platform Admin**: http://localhost/platform/login
  - Email: admin@trackmytickets.in
  - Password: Admin@2026

## Services

The Docker Compose setup includes:

1. **PostgreSQL Database** (port 5432)
   - Database: trackmytickets
   - User: ticketuser
   - Persistent volume: `postgres_data`

2. **Django Web Application** (port 8000, internal)
   - Runs with Gunicorn
   - Auto-restarts on failure
   - Health checks enabled

3. **Nginx Reverse Proxy** (ports 80, 443)
   - Serves static files
   - Proxies requests to Django
   - Gzip compression enabled

## Management Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f nginx
```

### Execute Django Commands
```bash
# Django shell
docker-compose exec web python manage.py shell

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Run migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

### Database Operations
```bash
# Access PostgreSQL
docker-compose exec db psql -U ticketuser -d trackmytickets

# Backup database
docker-compose exec db pg_dump -U ticketuser trackmytickets > backup.sql

# Restore database
docker-compose exec -T db psql -U ticketuser trackmytickets < backup.sql
```

### Service Management
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v

# Restart a specific service
docker-compose restart web

# Rebuild a specific service
docker-compose up -d --build web
```

## Production Deployment

### 1. Update Environment Variables

Edit `.env` with production values:
```env
DEBUG=False
SECRET_KEY=<generate-strong-secret-key>
DB_PASSWORD=<strong-database-password>
EMAIL_HOST_USER=<your-production-email>
EMAIL_HOST_PASSWORD=<your-email-password>
```

### 2. Configure Domain

Update `nginx/nginx.conf` with your domain:
```nginx
server_name yourdomain.com *.yourdomain.com;
```

### 3. SSL/HTTPS Setup

For SSL, you can use Let's Encrypt with Certbot:

```bash
# Install certbot
docker-compose exec nginx apk add certbot certbot-nginx

# Get SSL certificate
docker-compose exec nginx certbot --nginx -d yourdomain.com -d *.yourdomain.com
```

Or mount your SSL certificates:
```yaml
volumes:
  - ./ssl/cert.pem:/etc/nginx/ssl/cert.pem:ro
  - ./ssl/key.pem:/etc/nginx/ssl/key.pem:ro
```

### 4. Deploy

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build

# Run migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

## Monitoring

### Health Checks

All services have health checks configured:
```bash
# Check health status
docker-compose ps

# View health check logs
docker inspect ticket_system_web | grep -A 10 Health
```

### Resource Usage

```bash
# View resource usage
docker stats

# View disk usage
docker system df
```

## Troubleshooting

### Application Not Starting

1. Check logs:
   ```bash
   docker-compose logs web
   ```

2. Verify environment variables:
   ```bash
   docker-compose exec web env | grep DJANGO
   ```

3. Check database connection:
   ```bash
   docker-compose exec web python manage.py dbshell
   ```

### Static Files Not Loading

```bash
# Recollect static files
docker-compose exec web python manage.py collectstatic --noinput

# Restart nginx
docker-compose restart nginx
```

### Database Connection Issues

```bash
# Check if database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection
docker-compose exec web python manage.py dbshell
```

### Permission Issues

```bash
# Fix ownership
docker-compose exec web chown -R appuser:appuser /app
```

## Backup and Restore

### Automated Backup Script

Create `backup.sh`:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T db pg_dump -U ticketuser trackmytickets > "backups/db_$DATE.sql"
tar -czf "backups/media_$DATE.tar.gz" media/
echo "Backup completed: $DATE"
```

### Restore from Backup

```bash
# Restore database
docker-compose exec -T db psql -U ticketuser trackmytickets < backups/db_20260210.sql

# Restore media files
tar -xzf backups/media_20260210.tar.gz
```

## Scaling

To scale the web service:
```bash
# Run 3 web instances
docker-compose up -d --scale web=3
```

Note: You'll need to configure Nginx for load balancing.

## Cleanup

```bash
# Remove stopped containers
docker-compose down

# Remove all data (WARNING: irreversible)
docker-compose down -v

# Clean up Docker system
docker system prune -a
```

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Django debug mode | `False` |
| `SECRET_KEY` | Django secret key | Required |
| `DB_NAME` | Database name | `trackmytickets` |
| `DB_USER` | Database user | `ticketuser` |
| `DB_PASSWORD` | Database password | Required |
| `DB_HOST` | Database host | `db` |
| `DB_PORT` | Database port | `5432` |
| `EMAIL_HOST` | SMTP server | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | Email username | Required |
| `EMAIL_HOST_PASSWORD` | Email password | Required |
| `JWT_SECRET_KEY` | JWT secret | Required |

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review health checks: `docker-compose ps`
3. Verify environment variables
4. Check database connectivity
