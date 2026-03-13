#!/bin/bash
# VPS Deployment Checklist for trackmytickets.in
# Run this ON THE SERVER (ssh root@72.60.101.189) after deploying

set -e
cd /var/www/trackmytickets/current 2>/dev/null || cd /var/www/trackmytickets

echo "=== 1. Gunicorn ==="
systemctl status trackmytickets --no-pager || true

echo ""
echo "=== 2. Nginx ==="
systemctl status nginx --no-pager || true
nginx -t 2>&1

echo ""
echo "=== 3. Local Gunicorn (port 8000) ==="
curl -sI -m 5 http://127.0.0.1:8000/ || echo "FAIL: Gunicorn not responding"

echo ""
echo "=== 4. Health endpoint ==="
curl -s -m 5 http://127.0.0.1:8000/health/ | head -20 || echo "FAIL: Health check failed"

echo ""
echo "=== 5. Landing page (root) ==="
curl -sI -m 10 http://127.0.0.1:8000/ || echo "FAIL: Root page failed"

echo ""
echo "=== 6. Check env vars ==="
echo "DJANGO_SETTINGS_MODULE should be config.settings.production"
grep -E "DJANGO_SETTINGS|DB_HOST|USE_REDIS" /var/www/trackmytickets/shared/.env 2>/dev/null || true

echo ""
echo "=== 7. Recent Gunicorn logs ==="
journalctl -u trackmytickets -n 15 --no-pager 2>/dev/null || true
