#!/bin/bash

# Deployment Script for TrackMyTickets
# This script automates the deployment of the Django ticket system

set -e  # Exit on error

echo "========================================="
echo "TrackMyTickets Deployment Script"
echo "========================================="

# Configuration
APP_DIR="/var/www/trackmytickets"
PROJECT_DIR="$APP_DIR/ticket_system_django"
VENV_DIR="$APP_DIR/venv"
DB_NAME="trackmytickets"
DB_USER="ticketuser"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Step 1: Update system
print_status "Updating system packages..."
apt update && apt upgrade -y

# Step 2: Install system dependencies
print_status "Installing system dependencies..."
apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib \
    nginx git curl build-essential libpq-dev python3-dev

# Step 3: Remove old Flask project
print_status "Cleaning up old projects..."
if [ -d "/var/www/html" ]; then
    rm -rf /var/www/html/*
fi

# Stop any existing services
systemctl stop nginx 2>/dev/null || true
systemctl stop gunicorn 2>/dev/null || true

# Step 4: Create application directory
print_status "Creating application directory..."
mkdir -p $APP_DIR
cd $APP_DIR

# Step 5: Set up PostgreSQL
print_status "Setting up PostgreSQL database..."
sudo -u postgres psql <<EOF
-- Drop database if exists
DROP DATABASE IF EXISTS $DB_NAME;
DROP USER IF EXISTS $DB_USER;

-- Create database and user
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD 'TrackMyTickets2026!';
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'Asia/Kolkata';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

print_status "PostgreSQL database created successfully"

# Step 6: Create virtual environment (will be done after file upload)
print_status "Virtual environment will be created after file upload"

# Step 7: Configure firewall
print_status "Configuring firewall..."
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw reload

print_status "Firewall configured successfully"

echo ""
echo "========================================="
echo "Server preparation complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Upload project files to $APP_DIR"
echo "2. Run the application setup script"
echo ""
