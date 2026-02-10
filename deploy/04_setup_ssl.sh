#!/bin/bash

# SSL Setup Script using Let's Encrypt

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Install Certbot
print_status "Installing Certbot..."
apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
print_warning "Obtaining SSL certificate for trackmytickets.in..."
print_warning "Note: Wildcard certificates require DNS validation"

# For main domain and www
certbot --nginx -d trackmytickets.in -d www.trackmytickets.in --non-interactive --agree-tos --email admin@trackmytickets.in

print_status "SSL certificate obtained successfully!"

# Set up auto-renewal
print_status "Configuring auto-renewal..."
systemctl enable certbot.timer
systemctl start certbot.timer

print_status "SSL setup complete!"
print_status "Certificate will auto-renew via systemd timer"

# Test renewal
print_status "Testing certificate renewal..."
certbot renew --dry-run
