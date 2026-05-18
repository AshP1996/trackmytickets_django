#!/bin/bash
# Quick test to check what's happening with demo URLs

echo "Testing URL resolution and actual HTTP responses..."
echo ""

# Test 1: Check if URL resolves in Django
echo "1. Django URL Resolution Test:"
ssh root@72.60.101.189 "cd /var/www/trackmytickets/ticket_system_django && /var/www/trackmytickets/venv/bin/python3 manage.py shell << 'EOF'
from django.urls import resolve
try:
    match = resolve('/demo/login')
    print(f'✓ /demo/login resolves to: {match.view_name}')
except Exception as e:
    print(f'✗ /demo/login error: {e}')
EOF
"

echo ""
echo "2. HTTP Request Test (via Nginx):"
curl -s -I https://trackmyticket.luminoai.online/demo/login | head -3

echo ""
echo "3. HTTP Request Test (direct to Gunicorn socket):"
ssh root@72.60.101.189 "curl -s --unix-socket /run/gunicorn.sock -H 'Host: trackmyticket.luminoai.online' -H 'X-Forwarded-Proto: https' http://localhost/demo/login -I | head -3"

echo ""
echo "4. Check current Django settings in running Gunicorn:"
ssh root@72.60.101.189 "cat /proc/2001918/environ | tr '\\0' '\\n' | grep DJANGO_SETTINGS_MODULE"

echo ""
echo "5. Test with platform URL for comparison:"
curl -s -I https://trackmyticket.luminoai.online/platform/login | head -3
