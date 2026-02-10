#!/bin/bash

# Master Deployment Script
# Run this script from your LOCAL machine to deploy to the server

set -e

SERVER="root@72.60.101.189"
LOCAL_PROJECT="/home/ashish/Documents/ticket_system_v1/ticket_system_django"
REMOTE_DIR="/var/www/trackmytickets"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

echo "========================================="
echo "TrackMyTickets Deployment"
echo "========================================="
echo ""

# Step 1: Test SSH connection
print_status "Testing SSH connection..."
ssh -o ConnectTimeout=10 $SERVER "echo 'SSH connection successful'"

# Step 2: Upload server setup script
print_status "Uploading server setup script..."
scp $LOCAL_PROJECT/deploy/01_server_setup.sh $SERVER:/tmp/

# Step 3: Run server setup
print_status "Running server setup on remote server..."
ssh $SERVER "bash /tmp/01_server_setup.sh"

# Step 4: Upload project files
print_status "Uploading project files..."
rsync -avz --exclude='*.pyc' --exclude='__pycache__' --exclude='db.sqlite3' \
    --exclude='venv' --exclude='.git' --exclude='staticfiles' --exclude='media' \
    --exclude='.env' \
    $LOCAL_PROJECT/ $SERVER:$REMOTE_DIR/ticket_system_django/

# Step 5: Create .env file
print_status "Creating environment file..."
ssh $SERVER "cat > $REMOTE_DIR/.env" <<'EOF'
DEBUG=False
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
ALLOWED_HOSTS=trackmytickets.in,*.trackmytickets.in,72.60.101.189
DATABASE_URL=postgresql://ticketuser:TrackMyTickets2026!@localhost/trackmytickets
CSRF_TRUSTED_ORIGINS=https://trackmytickets.in,https://*.trackmytickets.in
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
EOF

# Step 6: Run application setup
print_status "Running application setup..."
ssh $SERVER "bash $REMOTE_DIR/ticket_system_django/deploy/02_app_setup.sh"

# Step 7: Configure services
print_status "Configuring services..."
ssh $SERVER "bash $REMOTE_DIR/ticket_system_django/deploy/03_configure_services.sh"

# Step 8: Setup SSL (optional, run separately)
print_warning "SSL setup can be run separately with: ssh $SERVER 'bash $REMOTE_DIR/ticket_system_django/deploy/04_setup_ssl.sh'"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Your application is now running at:"
echo "  http://trackmytickets.in"
echo ""
echo "Platform Admin Login:"
echo "  URL: http://trackmytickets.in/platform/login"
echo "  Email: admin@trackmytickets.in"
echo "  Password: Admin@2026"
echo ""
echo "To enable HTTPS, run:"
echo "  ssh $SERVER 'bash $REMOTE_DIR/ticket_system_django/deploy/04_setup_ssl.sh'"
echo ""
