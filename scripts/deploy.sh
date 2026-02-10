#!/bin/bash
# Deployment script for Ticket System
# Usage: ./scripts/deploy.sh

set -e  # Exit on error

echo "=========================================="
echo "Deploying Ticket System to Production"
echo "=========================================="

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found!"
    exit 1
fi

# Check if SECRET_KEY is set
if [ -z "$SECRET_KEY" ]; then
    echo "Error: SECRET_KEY not set in .env file!"
    exit 1
fi

# Pull latest code (if using git)
echo "[1/8] Pulling latest code..."
# git pull origin main

# Build Docker images
echo "[2/8] Building Docker images..."
docker-compose build --no-cache

# Stop existing containers
echo "[3/8] Stopping existing containers..."
docker-compose down

# Start database and redis first
echo "[4/8] Starting database and redis..."
docker-compose up -d db redis

# Wait for database to be ready
echo "[5/8] Waiting for database..."
sleep 10

# Run migrations
echo "[6/8] Running database migrations..."
docker-compose run --rm web python manage.py migrate --noinput

# Collect static files
echo "[7/8] Collecting static files..."
docker-compose run --rm web python manage.py collectstatic --noinput --clear

# Start all services
echo "[8/8] Starting all services..."
docker-compose up -d

# Show running containers
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
docker-compose ps

echo ""
echo "Application is running at:"
echo "  - http://localhost (HTTP)"
echo "  - https://trackmytickets.in (HTTPS)"
echo ""
echo "View logs with: docker-compose logs -f"
echo "Stop services with: docker-compose down"
