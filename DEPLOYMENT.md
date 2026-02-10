# Production Deployment Guide

## Ticket System - trackmytickets.in

This guide will help you deploy the Ticket System to production using Docker.

## Prerequisites

- Server with Docker and Docker Compose installed
- Domain name (trackmytickets.in) pointing to your server
- SSL certificate (Let's Encrypt recommended)
- Minimum 2GB RAM, 2 CPU cores, 20GB storage

## Quick Start

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

### 2. Clone Repository

```bash
cd /opt
git clone <your-repo-url> ticket_system
cd ticket_system/ticket_system_django
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate SECRET_KEY
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Edit .env file
nano .env
```

**Required environment variables:**
```env
SECRET_KEY=<generated-secret-key>
DB_PASSWORD=<strong-password>
DB_CREDENTIALS_ENCRYPTION_KEY=<generated-encryption-key>
EMAIL_HOST_USER=<your-email>
EMAIL_HOST_PASSWORD=<your-app-password>
```

### 4. SSL Certificate Setup

```bash
# Install certbot
sudo apt install certbot

# Obtain certificate
sudo certbot certonly --standalone -d trackmytickets.in -d www.trackmytickets.in

# Copy certificates to nginx directory
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/trackmytickets.in/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/trackmytickets.in/privkey.pem nginx/ssl/
```

### 5. Deploy Application

```bash
# Make deploy script executable
chmod +x scripts/deploy.sh

# Run deployment
./scripts/deploy.sh
```

### 6. Create Superuser

```bash
docker-compose exec web python manage.py createsuperuser
```

### 7. Verify Deployment

```bash
# Check services
docker-compose ps

# Check logs
docker-compose logs -f web

# Test health endpoint
curl http://localhost/health/
```

## DNS Configuration

Point your domain to your server:

```
A Record:     trackmytickets.in     →  <your-server-ip>
A Record:     www.trackmytickets.in →  <your-server-ip>
CNAME Record: *.trackmytickets.in   →  trackmytickets.in
```

## SSL Certificate Renewal

Set up auto-renewal:

```bash
# Add to crontab
sudo crontab -e

# Add this line
0 0 1 * * certbot renew --quiet && cp /etc/letsencrypt/live/trackmytickets.in/*.pem /opt/ticket_system/ticket_system_django/nginx/ssl/ && docker-compose restart nginx
```

## Backup Strategy

### Automated Backups

```bash
# Make backup script executable
chmod +x scripts/backup.sh

# Add to crontab for daily backups at 2 AM
crontab -e

# Add this line
0 2 * * * cd /opt/ticket_system/ticket_system_django && ./scripts/backup.sh
```

### Manual Backup

```bash
./scripts/backup.sh
```

### Restore from Backup

```bash
# List backups
ls -lh backups/

# Restore
gunzip backups/db_backup_YYYYMMDD_HHMMSS.sql.gz
docker-compose exec -T db psql -U postgres ticket_system < backups/db_backup_YYYYMMDD_HHMMSS.sql
```

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f nginx
docker-compose logs -f db

# Application logs
tail -f logs/django.log
tail -f logs/gunicorn_access.log
```

### Health Check

```bash
# Check application health
curl https://trackmytickets.in/health/

# Expected response
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "cache": "ok"
  },
  "python_version": "3.11.x"
}
```

## Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
./scripts/deploy.sh
```

### Scale Services

```bash
# Scale web workers
docker-compose up -d --scale web=3
```

### Database Migrations

```bash
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

### Collect Static Files

```bash
docker-compose exec web python manage.py collectstatic --noinput
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs web

# Check environment variables
docker-compose exec web env

# Rebuild without cache
docker-compose build --no-cache web
```

### Database Connection Issues

```bash
# Check database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection
docker-compose exec web python manage.py dbshell
```

### Static Files Not Loading

```bash
# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Check nginx logs
docker-compose logs nginx

# Verify volume mounts
docker-compose exec nginx ls -la /app/staticfiles
```

### SSL Certificate Issues

```bash
# Check certificate files
ls -la nginx/ssl/

# Test SSL configuration
docker-compose exec nginx nginx -t

# Restart nginx
docker-compose restart nginx
```

## Security Checklist

- [ ] SECRET_KEY is random and secure
- [ ] DEBUG = False in production
- [ ] Strong database password set
- [ ] SSL certificate installed and auto-renewing
- [ ] Firewall configured (allow 80, 443, 22 only)
- [ ] Regular backups automated
- [ ] Monitoring and alerting set up
- [ ] Rate limiting configured in nginx
- [ ] Security headers enabled
- [ ] Database credentials encrypted

## Performance Optimization

### Enable Caching

Redis is already configured. To use it:

```python
# In your views
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def my_view(request):
    ...
```

### Database Optimization

```bash
# Run VACUUM and ANALYZE
docker-compose exec db psql -U postgres ticket_system -c "VACUUM ANALYZE;"
```

### Monitor Resource Usage

```bash
# Check container stats
docker stats

# Check disk usage
docker system df
```

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review health check: `curl https://trackmytickets.in/health/`
- Check documentation in `/docs`

## Production URLs

- **Main Site**: https://trackmytickets.in
- **Admin Panel**: https://trackmytickets.in/admin/
- **API**: https://trackmytickets.in/api/{company}/
- **Health Check**: https://trackmytickets.in/health/

---

**Deployment Complete! 🎉**

Your ticket system is now running in production at **https://trackmytickets.in**
