#!/bin/bash

# Service Configuration Script
# Configures Gunicorn and Nginx services

set -e

GREEN='\033[0;32m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

# Copy systemd files
print_status "Installing Gunicorn service files..."
cp /var/www/trackmytickets/ticket_system_django/deploy/gunicorn.socket /etc/systemd/system/
cp /var/www/trackmytickets/ticket_system_django/deploy/gunicorn.service /etc/systemd/system/

# Reload systemd
print_status "Reloading systemd daemon..."
systemctl daemon-reload

# Start and enable Gunicorn
print_status "Starting Gunicorn service..."
systemctl start gunicorn.socket
systemctl enable gunicorn.socket
systemctl start gunicorn
systemctl enable gunicorn

# Configure Nginx
print_status "Configuring Nginx..."
cp /var/www/trackmytickets/ticket_system_django/deploy/nginx.conf /etc/nginx/sites-available/trackmytickets

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Enable site
ln -sf /etc/nginx/sites-available/trackmytickets /etc/nginx/sites-enabled/

# Test Nginx configuration
print_status "Testing Nginx configuration..."
nginx -t

# Restart Nginx
print_status "Restarting Nginx..."
systemctl restart nginx
systemctl enable nginx

print_status "Services configured successfully!"

# Show status
echo ""
echo "Service Status:"
systemctl status gunicorn --no-pager
echo ""
systemctl status nginx --no-pager
