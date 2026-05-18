#!/bin/bash
# Quick Docker Deployment Script for TrackMyTickets

set -e

echo "========================================="
echo "TrackMyTickets - Docker Deployment"
echo "========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from template..."
    cp .env.docker .env
    echo "✅ .env file created. Please edit it with your actual values."
    echo ""
    read -p "Press Enter after editing .env file..."
fi

# Build images
echo "📦 Building Docker images..."
docker-compose build --no-cache

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for database
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run migrations
echo "🔄 Running database migrations..."
docker-compose exec -T web python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
docker-compose exec -T web python manage.py collectstatic --noinput

# Create platform admin
echo "👤 Creating platform admin..."
docker-compose exec -T web python manage.py shell <<EOF
from apps.accounts.models import PlatformAdmin
from django.contrib.auth.hashers import make_password

if not PlatformAdmin.objects.filter(email='admin@luminoai.online').exists():
    PlatformAdmin.objects.create(
        email='admin@luminoai.online',
        password=make_password('Admin@2026')
    )
    print("✅ Platform admin created successfully")
else:
    print("ℹ️  Platform admin already exists")
EOF

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "Access your application at:"
echo "  🌐 Main Site: https://trackmyticket.luminoai.online (or http://localhost:8080 locally)"
echo "  🔐 Platform Admin: /platform/login"
echo "     Email: admin@luminoai.online"
echo "     Password: Admin@2026"
echo ""
echo "Useful commands:"
echo "  📋 View logs: docker-compose logs -f"
echo "  🔄 Restart: docker-compose restart"
echo "  🛑 Stop: docker-compose down"
echo ""
