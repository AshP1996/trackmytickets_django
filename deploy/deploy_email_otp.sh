#!/bin/bash
# Deploy Email OTP Fixes to Production Server
# Server: 72.60.101.189 (trackmytickets.in)

set -e

SERVER="root@72.60.101.189"
APP_DIR="/var/www/trackmytickets/ticket_system_django"

echo "========================================="
echo "Deploying Email OTP Fixes to Production"
echo "Server: trackmytickets.in"
echo "========================================="
echo ""

# 1. Upload new files
echo "📤 Uploading new files to server..."

# Upload email utilities
scp apps/accounts/email_utils.py $SERVER:$APP_DIR/apps/accounts/

# Upload updated views
scp apps/accounts/views.py $SERVER:$APP_DIR/apps/accounts/
scp apps/accounts/platform_views.py $SERVER:$APP_DIR/apps/accounts/

# Upload updated URLs
scp apps/accounts/platform_urls.py $SERVER:$APP_DIR/apps/accounts/

# Upload updated settings
scp config/settings/base.py $SERVER:$APP_DIR/config/settings/

echo "✅ Files uploaded successfully"
echo ""

# 2. Update .env file on server
echo "📝 Updating .env file on server..."
ssh $SERVER << 'ENDSSH'
cd /var/www/trackmytickets/ticket_system_django

# Backup existing .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Add email configuration if not present
if ! grep -q "JWT_SECRET_KEY" .env; then
    echo "" >> .env
    echo "# JWT Secret Key" >> .env
    echo "JWT_SECRET_KEY=511bd0176dcf54f2b526242f0be78a4eeee1b349af1b24f6bf02cc56492c480b" >> .env
fi

if ! grep -q "EMAIL_HOST" .env; then
    echo "" >> .env
    echo "# Email Configuration for OTP (Forgot Password)" >> .env
    echo "EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend" >> .env
    echo "EMAIL_HOST=smtp.gmail.com" >> .env
    echo "EMAIL_PORT=587" >> .env
    echo "EMAIL_USE_TLS=True" >> .env
    echo "EMAIL_HOST_USER=ash894173@gmail.com" >> .env
    echo "EMAIL_HOST_PASSWORD=ttrpmhdeyxzeulmt" >> .env
    echo "DEFAULT_FROM_EMAIL=ash894173@gmail.com" >> .env
    echo "" >> .env
    echo "# SMTP Configuration (alternative names)" >> .env
    echo "SMTP_SERVER=smtp.gmail.com" >> .env
    echo "SMTP_PORT=587" >> .env
    echo "SMTP_USERNAME=ash894173@gmail.com" >> .env
    echo "SMTP_PASSWORD=ttrpmhdeyxzeulmt" >> .env
fi

echo "✅ .env file updated"
ENDSSH

echo ""

# 3. Restart services
echo "🔄 Restarting Gunicorn service..."
ssh $SERVER << 'ENDSSH'
systemctl restart gunicorn
systemctl status gunicorn --no-pager -l
ENDSSH

echo ""
echo "✅ Gunicorn restarted successfully"
echo ""

# 4. Test email configuration
echo "🧪 Testing email configuration on server..."
ssh $SERVER << 'ENDSSH'
cd /var/www/trackmytickets/ticket_system_django
source venv/bin/activate

python << 'PYEOF'
import os
import django
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod_override')
django.setup()

from django.conf import settings

print("\n✅ Email Configuration Loaded:")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print()
PYEOF

ENDSSH

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "Email OTP functionality is now live at:"
echo "  🌐 https://trackmytickets.in"
echo ""
echo "API Endpoints:"
echo "  📧 Platform Admin Forgot Password:"
echo "     POST https://trackmytickets.in/platform/api/forgot-password"
echo ""
echo "  🔑 Platform Admin Reset Password:"
echo "     POST https://trackmytickets.in/platform/api/reset-password"
echo ""
echo "  📧 User Forgot Password:"
echo "     POST https://trackmytickets.in/{company}/api/forgot-password/"
echo ""
echo "  🔑 User Reset Password:"
echo "     POST https://trackmytickets.in/{company}/api/reset-password/"
echo ""
echo "Test the functionality:"
echo "  curl -X POST https://trackmytickets.in/platform/api/forgot-password \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"email\": \"admin@trackmytickets.in\"}'"
echo ""
