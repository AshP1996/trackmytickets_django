#!/bin/bash
# Script to check server configuration and diagnose URL issues

echo "========================================="
echo "Server Configuration Diagnostic"
echo "========================================="
echo ""

# Check if we're on the production server
if [ -f "/var/www/trackmytickets/ticket_system_django/manage.py" ]; then
    echo "✓ Running on production server"
    PROJECT_DIR="/var/www/trackmytickets/ticket_system_django"
else
    echo "✗ Not on production server, checking local config"
    PROJECT_DIR="/home/ashish/Documents/ticket_system_v1/ticket_system_django"
fi

echo ""
echo "1. Checking Nginx Configuration"
echo "--------------------------------"
if [ -f "/etc/nginx/sites-available/trackmytickets" ]; then
    echo "Nginx config file exists"
    echo "Location: /etc/nginx/sites-available/trackmytickets"
    echo ""
    echo "Proxy pass configuration:"
    grep -A 2 "location /" /etc/nginx/sites-available/trackmytickets | head -10
else
    echo "✗ Nginx config not found at /etc/nginx/sites-available/trackmytickets"
fi

echo ""
echo "2. Checking Gunicorn Status"
echo "---------------------------"
if command -v systemctl &> /dev/null; then
    systemctl status gunicorn --no-pager | head -15
else
    echo "systemctl not available"
fi

echo ""
echo "3. Checking Django URLs Configuration"
echo "-------------------------------------"
if [ -f "$PROJECT_DIR/config/urls.py" ]; then
    echo "Main URLs file: $PROJECT_DIR/config/urls.py"
    echo "First 30 lines:"
    head -30 "$PROJECT_DIR/config/urls.py"
else
    echo "✗ URLs file not found"
fi

echo ""
echo "4. Checking Static Files"
echo "------------------------"
if [ -d "$PROJECT_DIR/static" ]; then
    echo "Static directory exists: $PROJECT_DIR/static"
    echo "Contents:"
    ls -la "$PROJECT_DIR/static" | head -20
else
    echo "✗ Static directory not found"
fi

echo ""
echo "5. Checking Django Settings"
echo "---------------------------"
if [ -f "$PROJECT_DIR/config/settings.py" ]; then
    echo "ALLOWED_HOSTS:"
    grep "ALLOWED_HOSTS" "$PROJECT_DIR/config/settings.py"
    echo ""
    echo "STATIC_URL and STATIC_ROOT:"
    grep -E "STATIC_URL|STATIC_ROOT" "$PROJECT_DIR/config/settings.py"
else
    echo "✗ Settings file not found"
fi

echo ""
echo "6. Checking Application Logs"
echo "----------------------------"
if [ -d "/var/www/trackmytickets/logs" ]; then
    echo "Recent errors from gunicorn:"
    tail -50 /var/www/trackmytickets/logs/gunicorn-error.log 2>/dev/null || echo "No error log found"
else
    echo "Log directory not found"
fi

echo ""
echo "========================================="
echo "Diagnostic Complete"
echo "========================================="
