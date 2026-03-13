# VPS Deployment Guide — trackmytickets.in

## Fix: "Site Just Loading" / Hang

**Root cause:** Production was configured for Docker (Redis at `redis:6379`, Postgres at `db`). On a bare VPS these hosts don't exist → requests hang.

**Fixes applied in code:**
- `DB_HOST` defaults to `127.0.0.1` (not `db`)
- Redis optional: `USE_REDIS=false` by default → uses DB sessions + LocMem cache (no Redis)
- Optional `USE_SQLITE=true` for minimal setup without PostgreSQL

---

## Required .env on Server

Create `/var/www/trackmytickets/shared/.env`:

```bash
# Required
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=your-50-char-secret-key-here
DB_CREDENTIALS_ENCRYPTION_KEY=your-fernet-key-from-python-cryptography

# Database (PostgreSQL on VPS)
DB_HOST=127.0.0.1
DB_NAME=ticket_system
DB_USER=postgres
DB_PASSWORD=your_db_password

# Optional: Use SQLite for minimal deploy (no PostgreSQL)
# USE_SQLITE=true

# Optional: Redis (only if Redis is installed and running)
# USE_REDIS=true
# REDIS_URL=redis://127.0.0.1:6379/1

# Server IP (for ALLOWED_HOSTS)
SERVER_IP=72.60.101.189

# Optional: SITE_URL for email login links (defaults to https://trackmytickets.in)
```

Generate keys:
```bash
# SECRET_KEY
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# DB_CREDENTIALS_ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Gunicorn Service

Ensure `EnvironmentFile` and `WorkingDirectory` point correctly:

**/etc/systemd/system/trackmytickets.service**

```ini
[Unit]
Description=TrackMyTickets Gunicorn
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/trackmytickets/current
EnvironmentFile=/var/www/trackmytickets/shared/.env
ExecStart=/var/www/trackmytickets/current/venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --timeout 60
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Note:** Use `config.wsgi` (not `project.wsgi`).

---

## Post-Deploy Commands on VPS

```bash
# Load env
set -a
. /var/www/trackmytickets/shared/.env
set +a

cd /var/www/trackmytickets/current

# Migrate (creates session table if using DB sessions)
./venv/bin/python manage.py migrate --noinput

# Static files
./venv/bin/python manage.py collectstatic --noinput

# Restart
systemctl daemon-reload
systemctl restart trackmytickets
systemctl restart nginx
```

---

## Install PostgreSQL (if not using SQLite)

```bash
apt update
apt install -y postgresql postgresql-contrib

sudo -u postgres psql -c "CREATE USER ticket_system WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "CREATE DATABASE ticket_system OWNER ticket_system;"
```

---

## Run Deployment Check

```bash
chmod +x scripts/vps_deploy_check.sh
./scripts/vps_deploy_check.sh
```
