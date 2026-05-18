#!/bin/bash
# Fix Production Server Configuration
# This script fixes the WSGI settings module and restarts services

set -e

echo "========================================="
echo "Fixing Production Server Configuration"
echo "========================================="
echo ""

PROJECT_DIR="/var/www/trackmytickets/ticket_system_django"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}1. Backing up current wsgi.py${NC}"
cp "$PROJECT_DIR/config/wsgi.py" "$PROJECT_DIR/config/wsgi.py.backup.$(date +%Y%m%d_%H%M%S)"
echo -e "${GREEN}✓ Backup created${NC}"

echo ""
echo -e "${YELLOW}2. Updating wsgi.py to use prod_override settings${NC}"
cat > "$PROJECT_DIR/config/wsgi.py" << 'EOF'
import os

from django.core.wsgi import get_wsgi_application

# Use prod_override settings for production
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod_override')

application = get_wsgi_application()
EOF
echo -e "${GREEN}✓ wsgi.py updated${NC}"

echo ""
echo -e "${YELLOW}3. Updating manage.py to use prod_override settings${NC}"
cp "$PROJECT_DIR/manage.py" "$PROJECT_DIR/manage.py.backup.$(date +%Y%m%d_%H%M%S)"
cat > "$PROJECT_DIR/manage.py" << 'EOF'
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod_override')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
EOF
chmod +x "$PROJECT_DIR/manage.py"
echo -e "${GREEN}✓ manage.py updated${NC}"

echo ""
echo -e "${YELLOW}4. Updating prod_override.py for HTTPS${NC}"
cat > "$PROJECT_DIR/config/settings/prod_override.py" << 'EOF'
"""
Production Settings Override
Simplified production settings without Redis dependency
"""
import os
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Domain configuration
ALLOWED_HOSTS = [
    'trackmyticket.luminoai.online',
    'www.trackmyticket.luminoai.online',
    '72.60.101.189',  # Server IP
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'trackmytickets'),
        'USER': os.environ.get('DB_USER', 'ticketuser'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
    }
}

# Security Settings
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set in production")

# HTTPS/SSL Settings (enabled for HTTPS)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Proxy Settings (for Nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    'https://trackmyticket.luminoai.online',
]
CORS_ALLOW_CREDENTIALS = True

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    'https://trackmyticket.luminoai.online',
]

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# WhiteNoise for static file serving
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Use database-backed sessions instead of cache
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
EOF
echo -e "${GREEN}✓ prod_override.py updated for HTTPS${NC}"

echo ""
echo -e "${YELLOW}5. Collecting static files${NC}"
cd "$PROJECT_DIR"
source /var/www/trackmytickets/venv/bin/activate

# Export environment variables from systemd service
export DJANGO_SETTINGS_MODULE=config.settings.prod_override
export DEBUG=False
export SECRET_KEY="EAl1GuKGVqU4WALJrd8tqcROFPBARgPlQwEs6Xe16lBeBtRoysZ0HeAYhyKy3zEOYl0"
export DB_NAME="trackmytickets"
export DB_USER="ticketuser"
export DB_PASSWORD="TrackMyTickets2026!"
export DB_HOST="127.0.0.1"
export DB_PORT="5433"
export SERVER_IP="72.60.101.189"

python manage.py collectstatic --noinput
echo -e "${GREEN}✓ Static files collected${NC}"

echo ""
echo -e "${YELLOW}6. Restarting Gunicorn${NC}"
systemctl restart gunicorn
sleep 2
systemctl status gunicorn --no-pager | head -15
echo -e "${GREEN}✓ Gunicorn restarted${NC}"

echo ""
echo -e "${YELLOW}7. Restarting Nginx${NC}"
systemctl restart nginx
sleep 1
systemctl status nginx --no-pager | head -15
echo -e "${GREEN}✓ Nginx restarted${NC}"

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Fix Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Testing URLs..."
echo ""

# Test a few URLs
curl -s -o /dev/null -w "Platform Login: %{http_code}\n" https://trackmyticket.luminoai.online/platform/login
curl -s -o /dev/null -w "Demo Login: %{http_code}\n" https://trackmyticket.luminoai.online/demo/login
curl -s -o /dev/null -w "Demo Dashboard: %{http_code}\n" https://trackmyticket.luminoai.online/demo/dashboard

echo ""
echo -e "${YELLOW}Please run the full URL test script to verify all URLs are working.${NC}"
