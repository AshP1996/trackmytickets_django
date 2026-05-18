#!/bin/bash

# Application Setup Script
# Run this after uploading project files

set -e

APP_DIR="/var/www/trackmytickets"
PROJECT_DIR="$APP_DIR/ticket_system_django"
VENV_DIR="$APP_DIR/venv"

GREEN='\033[0;32m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

cd $APP_DIR

# Create virtual environment
print_status "Creating virtual environment..."
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
print_status "Installing Python dependencies..."
cd $PROJECT_DIR
pip install -r requirements.txt
pip install gunicorn psycopg2-binary python-decouple

# Create necessary directories
print_status "Creating directories..."
mkdir -p staticfiles media logs

# Run migrations
print_status "Running database migrations..."
python manage.py migrate

# Collect static files
print_status "Collecting static files..."
python manage.py collectstatic --noinput

# Create platform admin
print_status "Creating platform admin..."
python manage.py shell <<EOF
from apps.accounts.models import PlatformAdmin
from django.contrib.auth.hashers import make_password

if not PlatformAdmin.objects.filter(email='admin@luminoai.online').exists():
    PlatformAdmin.objects.create(
        email='admin@luminoai.online',
        password=make_password('Admin@2026')
    )
    print("Platform admin created successfully")
else:
    print("Platform admin already exists")
EOF

# Set permissions
print_status "Setting file permissions..."
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR

print_status "Application setup complete!"
