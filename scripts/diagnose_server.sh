#!/bin/bash
# Production Server Diagnostic and Fix Script
# Run this on the production server via SSH

set -e

echo "========================================="
echo "TrackMyTickets Server Diagnostic"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="/var/www/trackmytickets/ticket_system_django"
NGINX_CONFIG="/etc/nginx/sites-available/trackmytickets"

echo -e "${YELLOW}1. Checking Nginx Configuration${NC}"
echo "-----------------------------------"
if [ -f "$NGINX_CONFIG" ]; then
    echo -e "${GREEN}✓ Nginx config exists${NC}"
    echo ""
    echo "Current configuration:"
    cat "$NGINX_CONFIG"
    echo ""
else
    echo -e "${RED}✗ Nginx config not found${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}2. Checking Nginx Status${NC}"
echo "------------------------"
systemctl status nginx --no-pager | head -20

echo ""
echo -e "${YELLOW}3. Checking Gunicorn Status${NC}"
echo "---------------------------"
systemctl status gunicorn --no-pager | head -20

echo ""
echo -e "${YELLOW}4. Checking Gunicorn Service File${NC}"
echo "---------------------------------"
if [ -f "/etc/systemd/system/gunicorn.service" ]; then
    echo -e "${GREEN}✓ Gunicorn service file exists${NC}"
    cat /etc/systemd/system/gunicorn.service
else
    echo -e "${RED}✗ Gunicorn service file not found${NC}"
fi

echo ""
echo -e "${YELLOW}5. Checking Recent Nginx Error Logs${NC}"
echo "-----------------------------------"
if [ -f "/var/log/nginx/error.log" ]; then
    echo "Last 30 lines:"
    tail -30 /var/log/nginx/error.log
else
    echo "No error log found"
fi

echo ""
echo -e "${YELLOW}6. Checking Recent Gunicorn Logs${NC}"
echo "--------------------------------"
if [ -d "/var/www/trackmytickets/logs" ]; then
    echo "Gunicorn error log (last 30 lines):"
    tail -30 /var/www/trackmytickets/logs/gunicorn-error.log 2>/dev/null || echo "No error log"
    echo ""
    echo "Gunicorn access log (last 10 lines):"
    tail -10 /var/www/trackmytickets/logs/gunicorn-access.log 2>/dev/null || echo "No access log"
else
    echo "Log directory not found"
fi

echo ""
echo -e "${YELLOW}7. Testing Django URL Resolution${NC}"
echo "---------------------------------"
cd "$PROJECT_DIR"
source /var/www/trackmytickets/venv/bin/activate

python3 << 'PYTHON_EOF'
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import resolve, Resolver404

test_paths = [
    '/platform/login',
    '/demo/login',
    '/demo/dashboard',
    '/api/platform/login',
    '/api/demo/auth/login/',
]

print("\nTesting URL resolution in Django:")
for path in test_paths:
    try:
        match = resolve(path)
        print(f"✓ {path} → {match.view_name}")
    except Resolver404:
        print(f"✗ {path} → NOT FOUND")
    except Exception as e:
        print(f"✗ {path} → ERROR: {e}")
PYTHON_EOF

echo ""
echo -e "${YELLOW}8. Checking Django Settings${NC}"
echo "---------------------------"
cd "$PROJECT_DIR"
python3 << 'PYTHON_EOF'
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

print(f"DEBUG: {settings.DEBUG}")
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"STATIC_URL: {settings.STATIC_URL}")
print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
PYTHON_EOF

echo ""
echo -e "${YELLOW}9. Checking Static Files${NC}"
echo "------------------------"
if [ -d "$PROJECT_DIR/staticfiles" ]; then
    echo -e "${GREEN}✓ Static files directory exists${NC}"
    echo "Contents:"
    ls -la "$PROJECT_DIR/staticfiles" | head -20
else
    echo -e "${RED}✗ Static files directory not found${NC}"
    echo "Running collectstatic..."
    cd "$PROJECT_DIR"
    source /var/www/trackmytickets/venv/bin/activate
    python manage.py collectstatic --noinput
fi

echo ""
echo "========================================="
echo "Diagnostic Complete"
echo "========================================="
